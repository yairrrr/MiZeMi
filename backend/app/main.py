"""MiZeMi backend entry point. Run from backend/ with: uvicorn app.main:app"""

from fastapi import FastAPI

from app.api.health import router as health_router
from app.api.rooms import router as rooms_router
from app.infrastructure.rooms import RoomRegistry


def create_app() -> FastAPI:
    app = FastAPI(title="MiZeMi")
    # One registry per application instance: survives across requests in a
    # running process, isolated between separately created apps (tests).
    app.state.room_registry = RoomRegistry()
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(rooms_router, prefix="/api/v1")
    return app


app = create_app()
