"""Opaque host and player credentials (MASTER_SPEC.md §8, §14.1).

Infrastructure layer. A credential is a random bearer token handed once to
the client that created it (the host at room creation, a player at join).
Only a SHA-256 digest is kept in memory — the plaintext token is never
stored, persisted, or logged — and verification uses a constant-time
comparison.

``player_id`` stays a public identifier (it appears in room snapshots); the
player token is what proves a connection really belongs to that player, so
one participant cannot impersonate another.
"""

import hashlib
import hmac
import secrets

_TOKEN_BYTES = 32
_MAX_TOKEN_LENGTH = 256


def issue_token() -> str:
    """A fresh URL-safe token (~43 characters, 256 bits of entropy)."""
    return secrets.token_urlsafe(_TOKEN_BYTES)


def _digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _canonical(room_code: str) -> str:
    return room_code.strip().upper()


class CredentialStore:
    """In-memory digests of host and player tokens, keyed by room.

    Instantiable and injected through application state — no global state.
    Lifetime matches the room registry (rooms are not persisted, §15).
    """

    def __init__(self) -> None:
        self._hosts: dict[str, str] = {}
        self._players: dict[tuple[str, str], str] = {}

    def register_host(self, room_code: str, token: str) -> None:
        self._hosts[_canonical(room_code)] = _digest(token)

    def verify_host(self, room_code: str, token: str | None) -> bool:
        expected = self._hosts.get(_canonical(room_code))
        return _matches(expected, token)

    def register_player(self, room_code: str, player_id: str, token: str) -> None:
        self._players[(_canonical(room_code), player_id)] = _digest(token)

    def verify_player(self, room_code: str, player_id: str, token: str | None) -> bool:
        expected = self._players.get((_canonical(room_code), player_id))
        return _matches(expected, token)

    def forget_player(self, room_code: str, player_id: str) -> None:
        self._players.pop((_canonical(room_code), player_id), None)

    def forget_room(self, room_code: str) -> None:
        code = _canonical(room_code)
        self._hosts.pop(code, None)
        for key in [key for key in self._players if key[0] == code]:
            del self._players[key]


def _matches(expected_digest: str | None, token: str | None) -> bool:
    if expected_digest is None or not token or len(token) > _MAX_TOKEN_LENGTH:
        return False
    return hmac.compare_digest(expected_digest, _digest(token))
