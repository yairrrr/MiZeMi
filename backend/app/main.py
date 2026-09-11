"""MiZeMi backend entry point.

Local:   cd backend && uvicorn app.main:app --reload
Render:  uvicorn app.main:app --host 0.0.0.0 --port $PORT --ws-max-size 65536

Run a single worker: live games are held in process memory (§15).
"""

import asyncio
import contextlib
import logging
import threading
from collections.abc import AsyncIterator
from datetime import timedelta

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.errors import error_response
from app.api.health import router as health_router
from app.api.rooms import router as rooms_router
from app.application.gameplay import GameplayConfig, GameplayService, utc_now
from app.domain.game import Game
from app.infrastructure.credentials import CredentialStore
from app.infrastructure.database import (
    Base,
    create_database_engine,
    create_session_factory,
)
from app.infrastructure.database import models  # noqa: F401 - registers ORM tables
from app.infrastructure.repositories import SqlAlchemyGameRepository
from app.infrastructure.rooms import RoomRegistry
from app.infrastructure.settings import Settings, get_settings
from app.realtime.connections import RoomConnectionRegistry
from app.realtime.errors import ErrorCode
from app.realtime.host_connection import router as host_ws_router
from app.realtime.hub import GameHub
from app.realtime.player_connection import router as player_ws_router

logger = logging.getLogger("mizemi")

MAINTENANCE_INTERVAL_SECONDS = 300


class _Database:
    """Per-app engine/session factory with lazy, idempotent schema creation."""

    def __init__(self, database_url: str) -> None:
        self.engine = create_database_engine(database_url)
        self.session_factory = create_session_factory(self.engine)
        self._schema_ready = False
        self._lock = threading.Lock()

    def ensure_schema(self) -> None:
        # Schema strategy (§15): the ORM metadata is the schema; create_all is
        # idempotent and creates only missing tables on SQLite or PostgreSQL.
        with self._lock:
            if not self._schema_ready:
                Base.metadata.create_all(self.engine)
                self._schema_ready = True

    def save_finished_game(self, game: Game) -> None:
        self.ensure_schema()
        with self.session_factory() as session:
            SqlAlchemyGameRepository(session).save(game)
            session.commit()

    def purge_expired(self, retention: timedelta) -> int:
        self.ensure_schema()
        with self.session_factory() as session:
            removed = SqlAlchemyGameRepository(session).delete_older_than(utc_now() - retention)
            session.commit()
            return removed


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else get_settings()
    logging.getLogger("mizemi").setLevel(settings.log_level)
    database = _Database(settings.database_url)

    registry = RoomRegistry()
    credentials = CredentialStore()
    connections = RoomConnectionRegistry()
    hub = GameHub(
        registry=registry,
        credentials=credentials,
        connections=connections,
        gameplay=GameplayService(
            GameplayConfig(
                questions_per_game=settings.questions_per_game,
                time_limit_seconds=settings.question_time_limit_seconds,
            )
        ),
        max_players=settings.max_players_per_room,
        persist=database.save_finished_game,
    )

    async def maintenance() -> None:
        retention = timedelta(days=settings.retention_days)
        idle_ttl = timedelta(minutes=settings.room_idle_ttl_minutes)
        while True:
            try:
                hub.sweep_idle_rooms(idle_ttl=idle_ttl)
                await asyncio.to_thread(database.purge_expired, retention)
            except Exception:
                logger.exception("maintenance run failed")
            await asyncio.sleep(MAINTENANCE_INTERVAL_SECONDS)

    @contextlib.asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await asyncio.to_thread(database.ensure_schema)
        task = asyncio.create_task(maintenance())
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
            await asyncio.to_thread(hub.flush_persistence)
            database.engine.dispose()

    app = FastAPI(title="MiZeMi", lifespan=lifespan)
    app.state.settings = settings
    app.state.room_registry = registry
    app.state.credentials = credentials
    app.state.room_connections = connections
    app.state.game_hub = hub
    app.state.database = database

    # No cookies or auth headers are used by the browser, so credentials stay
    # off; origins come from MIZEMI_CORS_ORIGINS (§16).
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=False,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.exception_handler(RequestValidationError)
    async def _invalid_request(_: Request, __: RequestValidationError) -> JSONResponse:
        # §17 shape instead of FastAPI's default; no echo of the input.
        return error_response(422, ErrorCode.VALIDATION_ERROR, "The request is not valid.")

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("unhandled error on %s %s", request.method, request.url.path)
        return error_response(
            500, ErrorCode.INTERNAL_ERROR, "Something went wrong. Please try again."
        )

    app.include_router(health_router, prefix="/api/v1")
    app.include_router(rooms_router, prefix="/api/v1")
    app.include_router(player_ws_router)  # WS paths are /ws/... — no /api/v1 prefix
    app.include_router(host_ws_router)
    return app


app = create_app()
