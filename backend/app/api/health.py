"""Health check router. Must stay free of database, domain, and service access."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def get_health() -> dict[str, str]:
    return {"status": "ok"}
