"""Player-profile domain objects (MASTER_SPEC.md §9.2, §10).

Pure domain layer: no FastAPI, SQLAlchemy, Pydantic, or IO imports allowed.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProfileField:
    """One submitted profile field with its per-field consent flag.

    Field keys and per-field value typing are not final: ``str | int`` is the
    approved interim value type, and the final schema/validation rules are
    deferred to the PlayerProfile design stage (MASTER_SPEC.md §9.2), so this
    class performs no validation.
    """

    field_key: str
    value: str | int
    allow_question_usage: bool


@dataclass(frozen=True)
class PlayerProfile:
    """The structured facts one player submitted about themselves.

    Consent boundary (MASTER_SPEC.md §10.1): question-generation consumers
    must only ever be given ``consented_fields()`` — a field with
    ``allow_question_usage=False`` is treated as if it does not exist,
    with no override.
    """

    player_id: str
    fields: tuple[ProfileField, ...]

    def consented_fields(self) -> tuple[ProfileField, ...]:
        return tuple(field for field in self.fields if field.allow_question_usage)
