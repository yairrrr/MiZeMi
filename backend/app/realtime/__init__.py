"""Realtime wire contracts (MASTER_SPEC.md §14, §17)."""

from app.realtime.envelope import (
    MalformedEnvelopeError,
    RealtimeEnvelope,
    UnknownEventError,
    parse_client_envelope,
)
from app.realtime.errors import ErrorCode, ErrorDetail, ErrorPayload
from app.realtime.events import ClientToServerEvent, ServerToClientEvent

__all__ = [
    "ClientToServerEvent",
    "ErrorCode",
    "ErrorDetail",
    "ErrorPayload",
    "MalformedEnvelopeError",
    "RealtimeEnvelope",
    "ServerToClientEvent",
    "UnknownEventError",
    "parse_client_envelope",
]
