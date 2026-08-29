"""Realtime message envelope (MASTER_SPEC.md §14.3).

Pure wire-contract layer: no domain, transport, or application imports.
Every realtime message in both directions is wrapped in the same four-key
envelope. ``payload`` stays untyped here — per-event payload models belong
to the features that own each event.
"""

from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
    ValidationError,
    field_serializer,
    field_validator,
)

from app.realtime.events import ClientToServerEvent


class MalformedEnvelopeError(ValueError):
    """The raw message is not a structurally valid envelope.

    Local technical error; future consumers map it to VALIDATION_ERROR.
    """


class UnknownEventError(ValueError):
    """A structurally valid envelope names an event outside the registry.

    Local technical error; future consumers map it to UNKNOWN_EVENT.
    """

    def __init__(self, event: str) -> None:
        super().__init__(f"unknown event: {event}")
        self.event = event


class RealtimeEnvelope(BaseModel):
    """The §14.3 envelope: exactly event, payload, timestamp, game_id."""

    model_config = ConfigDict(extra="forbid")

    event: str
    payload: dict[str, Any]
    timestamp: datetime
    game_id: str

    @field_validator("timestamp")
    @classmethod
    def _require_timezone_aware(cls, value: datetime) -> datetime:
        # A naive datetime cannot be labeled Z without guessing its zone.
        if value.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return value

    @field_serializer("timestamp")
    def _serialize_timestamp(self, value: datetime) -> str:
        normalized = value.astimezone(UTC).replace(tzinfo=None)
        return normalized.isoformat(timespec="milliseconds") + "Z"


def parse_client_envelope(
    raw: Mapping[str, Any],
) -> tuple[ClientToServerEvent, RealtimeEnvelope]:
    """Validate a raw client message into (known event, envelope).

    Raises ``MalformedEnvelopeError`` for a structurally invalid message and
    ``UnknownEventError`` for a valid envelope whose event name is not in the
    client registry, so callers can answer with the appropriate error basis.
    """
    try:
        envelope = RealtimeEnvelope.model_validate(raw)
    except ValidationError as exc:
        raise MalformedEnvelopeError(str(exc)) from exc
    try:
        event = ClientToServerEvent(envelope.event)
    except ValueError:
        raise UnknownEventError(envelope.event) from None
    return event, envelope
