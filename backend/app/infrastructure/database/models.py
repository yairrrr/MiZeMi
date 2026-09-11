"""SQLAlchemy models for game persistence (MASTER_SPEC.md §15).

Infrastructure layer only — nothing above imports these. They mirror the
``Game`` aggregate for the approved MVP snapshot: a game persisted on the
``FINISHED`` transition (§15).

``profile_fields`` is deliberately schema-agnostic: the final PlayerProfile
schema is deferred (§9.2), so it stores whatever fields the domain supplies.
Interim (§9.2): ``value`` is text plus a ``value_type`` discriminator
("str" | "int"). Primary keys are domain-supplied strings or natural
composites — never database-generated (§15). Child rows are cleaned up
through the ORM ``delete-orphan`` cascade.

Schema note (§15): no migration tooling yet — this is the first schema.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.database.base import Base, TimestampMixin


class GameRow(Base, TimestampMixin):
    __tablename__ = "games"

    game_id: Mapped[str] = mapped_column(String, primary_key=True)
    state: Mapped[str] = mapped_column(String, nullable=False)
    current_question_index: Mapped[int | None] = mapped_column(Integer, nullable=True)

    scores: Mapped[list["ScoreRow"]] = relationship(cascade="all, delete-orphan", order_by="ScoreRow.player_id")
    answers: Mapped[list["AnswerRow"]] = relationship(cascade="all, delete-orphan", order_by="AnswerRow.answered_at, AnswerRow.player_id")

    players: Mapped[list["PlayerRow"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="PlayerRow.position",
    )
    questions: Mapped[list["GameQuestionRow"]] = relationship(
        back_populates="game",
        cascade="all, delete-orphan",
        order_by="GameQuestionRow.index",
    )


class PlayerRow(Base, TimestampMixin):
    __tablename__ = "players"

    player_id: Mapped[str] = mapped_column(String, primary_key=True)
    game_id: Mapped[str] = mapped_column(
        ForeignKey("games.game_id", ondelete="CASCADE"), nullable=False
    )
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    connected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    is_ready: Mapped[bool] = mapped_column(Boolean, nullable=False)
    has_profile: Mapped[bool] = mapped_column(Boolean, nullable=False)

    game: Mapped[GameRow] = relationship(back_populates="players")
    profile_fields: Mapped[list["ProfileFieldRow"]] = relationship(
        back_populates="player",
        cascade="all, delete-orphan",
        order_by="ProfileFieldRow.position",
    )


class ProfileFieldRow(Base, TimestampMixin):
    __tablename__ = "profile_fields"

    player_id: Mapped[str] = mapped_column(
        ForeignKey("players.player_id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_key: Mapped[str] = mapped_column(String, nullable=False)
    value: Mapped[str] = mapped_column(String, nullable=False)
    value_type: Mapped[str] = mapped_column(String, nullable=False)
    allow_question_usage: Mapped[bool] = mapped_column(Boolean, nullable=False)

    player: Mapped[PlayerRow] = relationship(back_populates="profile_fields")


class GameQuestionRow(Base, TimestampMixin):
    __tablename__ = "game_questions"

    question_id: Mapped[str] = mapped_column(String, primary_key=True)
    game_id: Mapped[str] = mapped_column(
        ForeignKey("games.game_id", ondelete="CASCADE"), nullable=False
    )
    index: Mapped[int] = mapped_column(Integer, nullable=False)
    total_questions: Mapped[int] = mapped_column(Integer, nullable=False)
    question_type: Mapped[str] = mapped_column(String, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)
    correct_option_id: Mapped[str] = mapped_column(String, nullable=False)
    time_limit_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    game: Mapped[GameRow] = relationship(back_populates="questions")
    options: Mapped[list["QuestionOptionRow"]] = relationship(
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionOptionRow.position",
    )


class QuestionOptionRow(Base, TimestampMixin):
    __tablename__ = "question_options"

    question_id: Mapped[str] = mapped_column(
        ForeignKey("game_questions.question_id", ondelete="CASCADE"), primary_key=True
    )
    option_id: Mapped[str] = mapped_column(String, primary_key=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    text: Mapped[str] = mapped_column(String, nullable=False)

    question: Mapped[GameQuestionRow] = relationship(back_populates="options")


class ScoreRow(Base, TimestampMixin):
    __tablename__ = "scores"

    game_id: Mapped[str] = mapped_column(ForeignKey("games.game_id", ondelete="CASCADE"), primary_key=True)
    player_id: Mapped[str] = mapped_column(String, primary_key=True)
    total_score: Mapped[int] = mapped_column(Integer, nullable=False)


class AnswerRow(Base, TimestampMixin):
    __tablename__ = "answers"

    game_id: Mapped[str] = mapped_column(ForeignKey("games.game_id", ondelete="CASCADE"), primary_key=True)
    question_id: Mapped[str] = mapped_column(String, primary_key=True)
    player_id: Mapped[str] = mapped_column(String, primary_key=True)
    option_id: Mapped[str] = mapped_column(String, nullable=False)
    answered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
