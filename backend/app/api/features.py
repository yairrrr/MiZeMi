"""Public feature flags for the frontend (MASTER_SPEC.md §12.7).

Lists only the capabilities the UI needs to render — specifically whether
the AI question-mode toggle should appear on room creation. Never exposes
anything key- or config-shaped.
"""

from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict

router = APIRouter()


class FeaturesResponse(BaseModel):
    """Minimal capability flags; add fields only through §21."""

    model_config = ConfigDict(extra="forbid")

    ai_mode_available: bool


@router.get("/features", response_model=FeaturesResponse)
async def get_features(request: Request) -> FeaturesResponse:
    hub = request.app.state.game_hub
    return FeaturesResponse(ai_mode_available=hub.ai_available)
