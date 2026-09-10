"""SQLAlchemy declarative base and shared column conventions (MASTER_SPEC.md §15).

Infrastructure layer: nothing above it imports this module. Every MiZeMi ORM
model inherits from ``Base`` and lives in this package (§15). Models are
written against the portable SQLAlchemy API — no SQLite-only features — so a
later move to another SQL backend stays feasible.
"""

from datetime import UTC, datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import TypeDecorator


def _utcnow() -> datetime:
    return datetime.now(UTC)


class UtcDateTime(TypeDecorator):
    """A ``DateTime`` that always stores and returns timezone-aware UTC.

    SQLite has no native timezone storage, so a plain ``DateTime(timezone=True)``
    silently drops the offset on SQLite. This decorator normalizes every value
    to UTC on the way in and re-attaches UTC on the way out, keeping the §15
    "UTC" guarantee identical on SQLite and any future SQL backend. Naive
    datetimes are rejected rather than guessed.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(
        self, value: datetime | None, dialect: object
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            raise ValueError("naive datetime rejected; pass a timezone-aware UTC value")
        return value.astimezone(UTC)

    def process_result_value(
        self, value: datetime | None, dialect: object
    ) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


class Base(DeclarativeBase):
    """The declarative base every MiZeMi ORM model inherits from."""


class TimestampMixin:
    """Adds the §15-mandated ``created_at`` / ``updated_at`` columns (UTC).

    ``created_at`` is set once at insert; ``updated_at`` is set at insert and
    bumped on every UPDATE. Both are timezone-aware UTC (see ``UtcDateTime``).
    """

    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime, default=_utcnow, onupdate=_utcnow, nullable=False
    )
