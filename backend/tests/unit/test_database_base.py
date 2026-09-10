"""Unit tests for the declarative base and column conventions (MASTER_SPEC.md §15)."""

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import String
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.infrastructure.database import Base, TimestampMixin
from app.infrastructure.database.engine import create_database_engine, create_session_factory


class _LocalBase(DeclarativeBase):
    """A throwaway base so the test model never touches the real Base.metadata."""


class _Widget(_LocalBase, TimestampMixin):
    __tablename__ = "widgets"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String, default="")


@pytest.fixture
def widget_session():
    engine = create_database_engine("sqlite://")
    _LocalBase.metadata.create_all(engine)
    session = create_session_factory(engine)()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


class TestBase:
    def test_base_is_a_declarative_base(self) -> None:
        assert issubclass(Base, DeclarativeBase)

    def test_base_metadata_has_no_tables_yet(self) -> None:
        # No ORM models exist yet; the DB task adds only the plumbing (§15).
        assert Base.metadata.tables == {}


class TestTimestampMixin:
    def test_created_and_updated_are_set_on_insert(self, widget_session) -> None:
        widget_session.add(_Widget(id="w1"))
        widget_session.commit()

        widget = widget_session.get(_Widget, "w1")
        assert isinstance(widget.created_at, datetime)
        assert isinstance(widget.updated_at, datetime)
        assert widget.created_at.tzinfo is not None
        assert widget.updated_at.tzinfo is not None

    def test_updated_at_is_bumped_on_update_but_created_at_is_not(
        self, widget_session
    ) -> None:
        widget_session.add(_Widget(id="w2", label="before"))
        widget_session.commit()
        row = widget_session.get(_Widget, "w2")
        created_before, updated_before = row.created_at, row.updated_at

        row.label = "after"
        widget_session.commit()

        widget_session.expire_all()
        refreshed = widget_session.get(_Widget, "w2")
        assert refreshed.created_at == created_before
        assert refreshed.updated_at >= updated_before


class TestUtcDateTime:
    def test_returns_utc_aware_datetimes(self, widget_session) -> None:
        widget_session.add(_Widget(id="w3"))
        widget_session.commit()
        widget_session.expire_all()

        widget = widget_session.get(_Widget, "w3")
        assert widget.created_at.utcoffset() == timedelta(0)

    def test_normalizes_a_non_utc_aware_value_to_utc(self, widget_session) -> None:
        plus_two = timezone(timedelta(hours=2))
        moment = datetime(2026, 1, 1, 12, 0, tzinfo=plus_two)

        widget = _Widget(id="w4")
        widget.created_at = moment
        widget_session.add(widget)
        widget_session.commit()
        widget_session.expire_all()  # force a real read back through UtcDateTime

        stored = widget_session.get(_Widget, "w4")
        assert stored.created_at == moment  # same instant
        assert stored.created_at.utcoffset() == timedelta(0)  # returned as UTC
        assert stored.created_at.hour == 10  # 12:00+02:00 == 10:00Z

    def test_rejects_a_naive_datetime(self, widget_session) -> None:
        widget = _Widget(id="w5")
        widget.created_at = datetime(2026, 1, 1, 12, 0)  # naive
        widget_session.add(widget)
        with pytest.raises(StatementError, match="naive datetime"):
            widget_session.commit()
