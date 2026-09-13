"""The MVP PlayerProfile schema and its validation (MASTER_SPEC.md §9.2, §10).

Application layer: no FastAPI, no Pydantic. The wire layer validates the
envelope *shape* (``field_key`` / ``value`` / ``allow_question_usage``); this
module decides whether the *content* is an acceptable profile and builds the
domain ``PlayerProfile`` in a canonical field order.

Privacy (§10): the schema only asks for light, social facts. Free-text values
that look like contact details, links, or ID/phone numbers are rejected, and
every field keeps its own ``allow_question_usage`` consent flag.
"""

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from app.domain.game import PlayerProfile, ProfileField

MUSIC_STYLES: tuple[str, ...] = (
    "Pop",
    "Rock",
    "Hip-Hop / Rap",
    "Electronic",
    "Mizrahi",
    "Classical",
    "Jazz",
    "Metal",
    "Mediterranean",
    "Israeli Pop",
    "House",
    "Techno",
    "Trance",
    "Indie",
    "R&B",
    "Reggae",
    "Folk",
    "Country",
    "Blues",
    "Other",
)


@dataclass(frozen=True)
class ProfileFieldSpec:
    """One field of the approved profile schema."""

    field_key: str
    label: str
    kind: Literal["text", "int", "choice"]
    required: bool
    max_length: int = 0
    min_value: int = 0
    max_value: int = 0
    choices: tuple[str, ...] = ()


PROFILE_FIELD_SPECS: tuple[ProfileFieldSpec, ...] = (
    ProfileFieldSpec("city", "City", "text", required=True, max_length=40),
    ProfileFieldSpec("favorite_food", "Favorite food", "text", required=True, max_length=40),
    ProfileFieldSpec("hobby", "Hobby", "text", required=True, max_length=40),
    ProfileFieldSpec(
        "favorite_music", "Favorite music style", "choice", required=True, choices=MUSIC_STYLES
    ),
    ProfileFieldSpec("age", "Age", "int", required=False, min_value=5, max_value=120),
    ProfileFieldSpec("favorite_movie", "Favorite movie", "text", required=False, max_length=60),
    ProfileFieldSpec("favorite_artist", "Favorite artist", "text", required=False, max_length=60),
    ProfileFieldSpec("favorite_song", "Favorite song", "text", required=False, max_length=60),
    ProfileFieldSpec(
        "personal_fact", "Something interesting about me", "text", required=False, max_length=120
    ),
)

_SPECS_BY_KEY = {spec.field_key: spec for spec in PROFILE_FIELD_SPECS}
_ORDER = {spec.field_key: position for position, spec in enumerate(PROFILE_FIELD_SPECS)}

_EMAIL = re.compile(r"[^\s@]+@[^\s@]+\.[^\s@]+")
_LINK = re.compile(r"(https?://|www\.)", re.IGNORECASE)
_LONG_NUMBER = re.compile(r"\d(?:[\s\-.]?\d){6,}")

PRIVACY_MESSAGE = (
    "Please don't include contact details, links, or ID/phone numbers in your profile."
)


class ProfileValidationError(Exception):
    """The submitted profile is not acceptable; ``message`` is safe to display."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


def _normalize_text(value: str) -> str:
    return " ".join(value.split())


def _looks_sensitive(value: str) -> bool:
    return bool(_EMAIL.search(value) or _LINK.search(value) or _LONG_NUMBER.search(value))


def _validated_value(spec: ProfileFieldSpec, value: object) -> str | int:
    if spec.kind == "int":
        if isinstance(value, bool) or not isinstance(value, int):
            raise ProfileValidationError(f"{spec.label} must be a whole number.")
        if not spec.min_value <= value <= spec.max_value:
            raise ProfileValidationError(
                f"{spec.label} must be between {spec.min_value} and {spec.max_value}."
            )
        return value

    if not isinstance(value, str):
        raise ProfileValidationError(f"{spec.label} must be text.")
    text = _normalize_text(value)

    if spec.kind == "choice":
        if text not in spec.choices:
            raise ProfileValidationError(f"Choose one of the listed options for {spec.label}.")
        return text

    if not text:
        raise ProfileValidationError(f"{spec.label} cannot be empty.")
    if len(text) > spec.max_length:
        raise ProfileValidationError(
            f"{spec.label} must be at most {spec.max_length} characters."
        )
    if _looks_sensitive(text):
        raise ProfileValidationError(PRIVACY_MESSAGE)
    return text


def build_validated_profile(
    player_id: str,
    submitted: Sequence[tuple[str, object, bool]],
) -> PlayerProfile:
    """Validate ``(field_key, value, allow_question_usage)`` triples.

    Returns a ``PlayerProfile`` whose fields follow the canonical schema
    order. Raises ``ProfileValidationError`` for an unknown or duplicate
    field, a missing required field, or an invalid value.
    """
    seen: set[str] = set()
    fields: list[ProfileField] = []
    for field_key, value, allow_question_usage in submitted:
        spec = _SPECS_BY_KEY.get(field_key)
        if spec is None:
            raise ProfileValidationError("The profile contains an unknown field.")
        if field_key in seen:
            raise ProfileValidationError(f"{spec.label} was submitted more than once.")
        seen.add(field_key)
        fields.append(
            ProfileField(
                field_key=field_key,
                value=_validated_value(spec, value),
                allow_question_usage=bool(allow_question_usage),
            )
        )

    for spec in PROFILE_FIELD_SPECS:
        if spec.required and spec.field_key not in seen:
            raise ProfileValidationError(f"{spec.label} is required.")

    fields.sort(key=lambda field: _ORDER[field.field_key])
    return PlayerProfile(player_id=player_id, fields=tuple(fields))
