"""Error payload models for the realtime ``error`` event (MASTER_SPEC.md §17).

Pure wire-contract layer: no domain, transport, or application imports.
The same §17 shape serves REST bodies; the REST error-mapping work may
later import or relocate these — a non-contractual refactor.
"""

from enum import Enum, unique
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    SerializerFunctionWrapHandler,
    model_serializer,
)


@unique
class ErrorCode(Enum):
    """The approved §17 error-code registry — additions only via a spec PR."""

    ROOM_NOT_FOUND = "ROOM_NOT_FOUND"
    ROOM_FULL = "ROOM_FULL"
    NAME_TAKEN = "NAME_TAKEN"
    INVALID_STATE_TRANSITION = "INVALID_STATE_TRANSITION"
    QUESTION_CLOSED = "QUESTION_CLOSED"
    ALREADY_ANSWERED = "ALREADY_ANSWERED"
    NOT_HOST = "NOT_HOST"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNKNOWN_EVENT = "UNKNOWN_EVENT"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class ErrorDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: ErrorCode
    message: str
    details: dict[str, Any] | None = None

    @model_serializer(mode="wrap")
    def _omit_absent_details(
        self, handler: SerializerFunctionWrapHandler
    ) -> dict[str, Any]:
        # The wire contract marks "details" as an optional key, not nullable:
        # omit it when absent so callers need not remember exclude_none.
        data = handler(self)
        if data.get("details") is None:
            data.pop("details", None)
        return data


class ErrorPayload(BaseModel):
    """The §17 wire shape: ``{"error": {"code", "message", "details"?}}``."""

    model_config = ConfigDict(extra="forbid")

    error: ErrorDetail
