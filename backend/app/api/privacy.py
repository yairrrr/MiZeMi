"""Public factual disclosures, explicitly allowlisted; never expose settings wholesale."""

from fastapi import APIRouter, Request
from pydantic import BaseModel

router = APIRouter()


class PrivacyInfo(BaseModel):
    policy_version: str
    retention_days: int
    room_idle_ttl_minutes: int
    maintenance_interval_seconds: int
    raw_profiles_persisted: bool


@router.get("/privacy-info", response_model=PrivacyInfo)
async def privacy_info(request: Request) -> PrivacyInfo:
    settings = request.app.state.settings
    return PrivacyInfo(
        policy_version="2026-09-18",
        retention_days=settings.retention_days,
        room_idle_ttl_minutes=settings.room_idle_ttl_minutes,
        maintenance_interval_seconds=request.app.state.maintenance_interval_seconds,
        raw_profiles_persisted=False,
    )
