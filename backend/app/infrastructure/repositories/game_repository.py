"""SQLAlchemy implementation of ``GameRepository`` (MASTER_SPEC.md §15).

Infrastructure layer: maps the ``Game`` aggregate to and from the ORM rows in
``app/infrastructure/database/models.py``. SQLAlchemy stays sealed in this
layer — the application receives only the plain ``FinishedGameRecord``.

The session is injected; the caller owns the transaction and commits (§15).
"""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.application.repositories import (
    FinishedGameRecord,
    RecordedAnswer,
    RecordedScore,
    GameRepository,
    RecordedPlayer,
    RecordedProfileField,
    RecordedQuestion,
    RecordedQuestionOption,
)
from app.domain.game import Game
from app.domain.game.config import GameConfig
from app.domain.questions import Question
from app.infrastructure.database.models import (
    GameQuestionRow,
    GameConfigurationRow,
    QuestionDetailRow,
    QuestionExplanationRow,
    AnswerRow,
    ScoreRow,
    GameRow,
    PlayerRow,
    ProfileFieldRow,
    QuestionOptionRow,
)


def _value_type(value: str | int) -> str:
    # bool is a subclass of int; profile values are only ever str | int (§9.2).
    return "int" if isinstance(value, int) and not isinstance(value, bool) else "str"


def _decode_value(value: str, value_type: str) -> str | int:
    return int(value) if value_type == "int" else value


def _current_question_index(game: Game) -> int | None:
    current = game.current_question
    if current is None:
        return None
    return game.questions.index(current)


def _question_to_row(question: Question, game_id: str) -> GameQuestionRow:
    return GameQuestionRow(
        question_id=question.question_id,
        game_id=game_id,
        index=question.index,
        total_questions=question.total_questions,
        question_type=question.question_type.value,
        text=question.text,
        correct_option_id=question.correct_option_id,
        time_limit_seconds=question.time_limit_seconds,
        detail=QuestionDetailRow(question_id=question.question_id, difficulty=question.difficulty.value, language=question.language, source_rule_id=question.source_rule_id),
        explanation=QuestionExplanationRow(question_id=question.question_id, explanation=question.explanation, knowledge_version=question.knowledge_version),
        options=[
            QuestionOptionRow(
                question_id=question.question_id,
                option_id=option.option_id,
                position=position,
                text=option.text,
            )
            for position, option in enumerate(question.options)
        ],
    )


def _game_to_row(game: Game) -> GameRow:
    row = GameRow(
        game_id=game.game_id,
        state=game.state.value,
        configuration=GameConfigurationRow(game_id=game.game_id, question_count=game.config.question_count, language=game.config.language),
        current_question_index=_current_question_index(game),
    )
    for position, player in enumerate(game.players):
        player_row = PlayerRow(
            player_id=player.player_id,
            game_id=game.game_id,
            position=position,
            display_name=player.display_name,
            connected=player.connected,
            is_ready=player.is_ready,
            has_profile=player.has_profile,
        )
        if player.profile is not None:
            player_row.profile_fields = [
                ProfileFieldRow(
                    player_id=player.player_id,
                    position=field_position,
                    field_key=field.field_key,
                    value=str(field.value),
                    value_type=_value_type(field.value),
                    allow_question_usage=field.allow_question_usage,
                )
                for field_position, field in enumerate(player.profile.fields)
            ]
        row.players.append(player_row)
    for question in game.questions:
        row.questions.append(_question_to_row(question, game.game_id))
    row.scores = [ScoreRow(game_id=game.game_id, player_id=pid, total_score=score)
                  for pid, score in game.scores.items()]
    row.answers = [AnswerRow(game_id=game.game_id, question_id=answer.question_id,
                            player_id=answer.player_id, option_id=answer.option_id,
                            answered_at=answer.answered_at)
                   for question in game.questions for answer in game.answers_for(question.question_id)]
    return row


def _row_to_record(row: GameRow) -> FinishedGameRecord:
    return FinishedGameRecord(
        scores=tuple(RecordedScore(player_id=score.player_id, total_score=score.total_score) for score in row.scores),
        answers=tuple(RecordedAnswer(player_id=answer.player_id, question_id=answer.question_id,
                                    option_id=answer.option_id,
                                    answered_at=answer.answered_at.replace(tzinfo=UTC) if answer.answered_at.tzinfo is None else answer.answered_at.astimezone(UTC))
                      for answer in row.answers),
        config=GameConfig(question_count=row.configuration.question_count, language=row.configuration.language) if row.configuration else GameConfig(question_count=max(1, len(row.questions))),
        game_id=row.game_id,
        state=row.state,
        current_question_index=row.current_question_index,
        players=tuple(
            RecordedPlayer(
                player_id=player.player_id,
                display_name=player.display_name,
                connected=player.connected,
                is_ready=player.is_ready,
                has_profile=player.has_profile,
                profile_fields=tuple(
                    RecordedProfileField(
                        field_key=field.field_key,
                        value=_decode_value(field.value, field.value_type),
                        allow_question_usage=field.allow_question_usage,
                    )
                    for field in player.profile_fields
                ),
            )
            for player in row.players
        ),
        questions=tuple(
            RecordedQuestion(
                question_id=question.question_id,
                index=question.index,
                total_questions=question.total_questions,
                question_type=question.question_type,
                text=question.text,
                options=tuple(
                    RecordedQuestionOption(option_id=option.option_id, text=option.text)
                    for option in question.options
                ),
                correct_option_id=question.correct_option_id,
                time_limit_seconds=question.time_limit_seconds,
                difficulty=question.detail.difficulty if question.detail else "EASY",
                language=question.detail.language if question.detail else "en",
                source_rule_id=question.detail.source_rule_id if question.detail else "",
                explanation=question.explanation.explanation if question.explanation else "",
                knowledge_version=question.explanation.knowledge_version if question.explanation else "",
            )
            for question in row.questions
        ),
    )


class SqlAlchemyGameRepository(GameRepository):
    """Persists the ``Game`` aggregate to SQLite/SQLAlchemy (§15)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def save(self, game: Game) -> None:
        existing = self._session.get(GameRow, game.game_id)
        if existing is not None:
            # Whole-aggregate upsert: drop the old tree (delete-orphan cascades
            # to children) and re-insert. The MVP writes each game once, so the
            # simplicity is worth more than a diffing update.
            self._session.delete(existing)
            self._session.flush()
        self._session.add(_game_to_row(game))
        self._session.flush()

    def get(self, game_id: str) -> FinishedGameRecord | None:
        row = self._session.get(GameRow, game_id)
        return _row_to_record(row) if row is not None else None

    def delete_older_than(self, cutoff: datetime) -> int:
        # ORM deletes (not a bulk DELETE) so the delete-orphan cascade removes
        # child rows on every backend, including SQLite without FK pragmas.
        rows = self._session.scalars(select(GameRow).where(GameRow.updated_at < cutoff)).all()
        for row in rows:
            self._session.delete(row)
        self._session.flush()
        return len(rows)

    def delete(self, game_id: str) -> None:
        row = self._session.get(GameRow, game_id)
        if row is not None:
            self._session.delete(row)
            self._session.flush()
