"""MiZeMi backend entry point. Run from backend/ with: uvicorn app.main:app"""

from fastapi import FastAPI

from app.api.health import router as health_router


def create_app() -> FastAPI:
    app = FastAPI(title="MiZeMi")
    app.include_router(health_router, prefix="/api/v1")
    return app


app = create_app()
