"""Integration test: a real on-disk SQLite database round-trips (MASTER_SPEC.md §15).

Uses a temp file rather than the shared in-memory fixture to prove the engine
persists to disk and the same schema/data is visible through a second engine
opened on that file.
"""

from sqlalchemy import String, select
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.infrastructure.database import TimestampMixin, create_database_engine, create_session_factory


class _Base(DeclarativeBase):
    pass


class _Note(_Base, TimestampMixin):
    __tablename__ = "notes"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    body: Mapped[str] = mapped_column(String, nullable=False)


def test_sqlite_file_persists_between_engines(tmp_path) -> None:
    url = f"sqlite:///{tmp_path / 'mizemi_test.db'}"

    writer_engine = create_database_engine(url)
    _Base.metadata.create_all(writer_engine)
    with create_session_factory(writer_engine)() as session:
        session.add(_Note(id="n1", body="hello"))
        session.commit()
    writer_engine.dispose()

    reader_engine = create_database_engine(url)
    with create_session_factory(reader_engine)() as session:
        note = session.execute(select(_Note).where(_Note.id == "n1")).scalar_one()
        assert note.body == "hello"
        assert note.created_at.tzinfo is not None
    reader_engine.dispose()

    assert (tmp_path / "mizemi_test.db").exists()
