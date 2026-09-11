"""Contract-pinning tests for the API wire schemas (MASTER_SPEC.md §9.1–§9.3)."""

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from app.api.schemas import (
    AnswerSubmissionSchema,
    JoinRoomResponse,
    PlayerProfileSchema,
    PlayerSchema,
    ProfileFieldSchema,
    PublicQuestionSchema,
    QuestionOptionSchema,
)
from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions.question import Question, QuestionOption, QuestionType

PLAYER_WIRE_KEYS = {
    "player_id",
    "display_name",
    "is_host",
    "connected",
    "has_profile",
    "is_ready",
    "score",
}


def _profile() -> PlayerProfile:
    return PlayerProfile(
        player_id="p1",
        fields=(
            ProfileField(field_key="favorite_food", value="pizza", allow_question_usage=True),
            ProfileField(field_key="age", value=27, allow_question_usage=True),
            ProfileField(field_key="personal_fact", value="afraid of pigeons", allow_question_usage=False),
        ),
    )


class TestPlayerSchema:
    def test_player_without_profile_maps_correctly(self) -> None:
        player = Player(player_id="p1", display_name="Dana")

        schema = PlayerSchema.from_domain(player, score=0)

        assert schema.player_id == "p1"
        assert schema.display_name == "Dana"
        assert schema.is_host is False
        assert schema.connected is False
        assert schema.has_profile is False
        assert schema.is_ready is False
        assert schema.score == 0

    def test_player_with_profile_maps_has_profile_true(self) -> None:
        player = Player(player_id="p1", display_name="Dana")
        player.assign_initial_profile(_profile())

        schema = PlayerSchema.from_domain(player, score=0)

        assert schema.has_profile is True

    def test_connected_state_is_mapped_from_domain(self) -> None:
        player = Player(player_id="p1", display_name="Dana", connected=True)

        schema = PlayerSchema.from_domain(player, score=0)

        assert schema.connected is True

    def test_ready_state_is_mapped_from_domain(self) -> None:
        player = Player(player_id="p1", display_name="Dana", is_ready=True)

        schema = PlayerSchema.from_domain(player, score=0)

        assert schema.is_ready is True

    def test_explicit_score_is_preserved_exactly(self) -> None:
        player = Player(player_id="p1", display_name="Dana")

        schema = PlayerSchema.from_domain(player, score=1730)

        assert schema.score == 1730

    def test_from_domain_requires_score(self) -> None:
        player = Player(player_id="p1", display_name="Dana")

        with pytest.raises(TypeError):
            PlayerSchema.from_domain(player)  # type: ignore[call-arg]

    def test_serialized_player_has_exact_wire_keys(self) -> None:
        player = Player(player_id="p1", display_name="Dana")

        dumped = PlayerSchema.from_domain(player, score=0).model_dump(mode="json")

        assert set(dumped.keys()) == PLAYER_WIRE_KEYS

    def test_extra_player_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PlayerSchema.model_validate(
                {
                    "player_id": "p1",
                    "display_name": "Dana",
                    "is_host": False,
                    "connected": True,
                    "has_profile": False,
                    "is_ready": False,
                    "score": 0,
                    "email": "dana@example.com",
                }
            )

    def test_mapping_does_not_mutate_domain_player(self) -> None:
        player = Player(player_id="p1", display_name="Dana")

        PlayerSchema.from_domain(player, score=999)

        assert player.player_id == "p1"
        assert player.display_name == "Dana"
        assert player.connected is False
        assert player.is_ready is False
        assert player.profile is None


class TestJoinRoomResponse:
    def test_serialized_response_has_exact_contract_keys(self) -> None:
        player = PlayerSchema.from_domain(
            Player(player_id="p1", display_name="Dana"), score=0
        )

        dumped = JoinRoomResponse(
            game_id="g1", player=player, player_token="token-1"
        ).model_dump(mode="json")

        assert set(dumped.keys()) == {"game_id", "player", "player_token"}
        assert set(dumped["player"].keys()) == PLAYER_WIRE_KEYS

    def test_extra_response_fields_rejected(self) -> None:
        player = PlayerSchema.from_domain(
            Player(player_id="p1", display_name="Dana"), score=0
        )

        with pytest.raises(ValidationError):
            JoinRoomResponse.model_validate(
                {
                    "game_id": "g1",
                    "player": player,
                    "player_token": "token-1",
                    "room_code": "ABC234",
                }
            )


class TestProfileSchemas:
    def test_profile_maps_player_id_and_fields(self) -> None:
        schema = PlayerProfileSchema.from_domain(_profile())

        assert schema.player_id == "p1"
        assert len(schema.fields) == 3

    def test_field_order_is_preserved(self) -> None:
        schema = PlayerProfileSchema.from_domain(_profile())

        assert [field.field_key for field in schema.fields] == [
            "favorite_food",
            "age",
            "personal_fact",
        ]

    def test_str_values_preserved_exactly(self) -> None:
        schema = PlayerProfileSchema.from_domain(_profile())

        assert schema.fields[0].value == "pizza"
        assert isinstance(schema.fields[0].value, str)

    def test_int_values_preserved_exactly(self) -> None:
        schema = PlayerProfileSchema.from_domain(_profile())

        assert schema.fields[1].value == 27
        assert isinstance(schema.fields[1].value, int)

    def test_allow_question_usage_preserved(self) -> None:
        schema = PlayerProfileSchema.from_domain(_profile())

        assert [field.allow_question_usage for field in schema.fields] == [True, True, False]

    def test_serialized_profile_has_exact_wire_keys(self) -> None:
        dumped = PlayerProfileSchema.from_domain(_profile()).model_dump(mode="json")

        assert set(dumped.keys()) == {"player_id", "fields"}
        assert all(
            set(field.keys()) == {"field_key", "value", "allow_question_usage"}
            for field in dumped["fields"]
        )

    def test_extra_profile_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PlayerProfileSchema.model_validate(
                {"player_id": "p1", "fields": [], "nickname": "D"}
            )

    def test_extra_profile_field_keys_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ProfileFieldSchema.model_validate(
                {
                    "field_key": "city",
                    "value": "Haifa",
                    "allow_question_usage": True,
                    "hint": "north",
                }
            )

    def test_mapping_does_not_mutate_domain_profile(self) -> None:
        profile = _profile()
        original_fields = profile.fields

        PlayerProfileSchema.from_domain(profile)

        assert profile.fields == original_fields
        assert profile.fields[1].value == 27


PUBLIC_QUESTION_WIRE_KEYS = {
    "question_id",
    "index",
    "total_questions",
    "question_type",
    "text",
    "options",
    "time_limit_seconds",
    "started_at",
}

STARTED_AT = datetime(2026, 8, 31, 10, 15, 30, tzinfo=UTC)


def _domain_question() -> Question:
    return Question(
        question_id="q1",
        index=0,
        total_questions=5,
        question_type=QuestionType.MULTIPLE_CHOICE,
        text="Who is the only player from Haifa?",
        options=(
            QuestionOption(option_id="a", text="Dana"),
            QuestionOption(option_id="b", text="Omer"),
            QuestionOption(option_id="c", text="Noa"),
        ),
        correct_option_id="b",
        time_limit_seconds=20,
    )


class TestPublicQuestionSchema:
    def test_question_maps_public_fields(self) -> None:
        schema = PublicQuestionSchema.from_domain(_domain_question(), started_at=STARTED_AT)

        assert schema.question_id == "q1"
        assert schema.index == 0
        assert schema.total_questions == 5
        assert schema.question_type == "multiple_choice"
        assert schema.text == "Who is the only player from Haifa?"
        assert schema.time_limit_seconds == 20
        assert schema.started_at == STARTED_AT

    def test_serialized_question_has_exact_wire_keys(self) -> None:
        dumped = PublicQuestionSchema.from_domain(
            _domain_question(), started_at=STARTED_AT
        ).model_dump(mode="json")

        assert set(dumped.keys()) == PUBLIC_QUESTION_WIRE_KEYS

    def test_correct_option_id_is_never_serialized(self) -> None:
        """Security pin: the §9.3 never-leak rule is structural, not procedural."""
        schema = PublicQuestionSchema.from_domain(_domain_question(), started_at=STARTED_AT)

        dumped = schema.model_dump(mode="json")

        assert "correct_option_id" not in dumped
        assert not hasattr(schema, "correct_option_id")
        assert "correct_option_id" not in PublicQuestionSchema.model_fields

    def test_correct_option_id_cannot_be_injected_as_extra_field(self) -> None:
        payload = PublicQuestionSchema.from_domain(
            _domain_question(), started_at=STARTED_AT
        ).model_dump(mode="json")
        payload["correct_option_id"] = "b"

        with pytest.raises(ValidationError):
            PublicQuestionSchema.model_validate(payload)

    def test_option_schema_has_exactly_option_id_and_text(self) -> None:
        dumped = PublicQuestionSchema.from_domain(
            _domain_question(), started_at=STARTED_AT
        ).model_dump(mode="json")

        assert all(set(option.keys()) == {"option_id", "text"} for option in dumped["options"])

    def test_option_order_is_preserved(self) -> None:
        schema = PublicQuestionSchema.from_domain(_domain_question(), started_at=STARTED_AT)

        assert [option.option_id for option in schema.options] == ["a", "b", "c"]

    def test_question_type_serializes_to_approved_wire_string(self) -> None:
        dumped = PublicQuestionSchema.from_domain(
            _domain_question(), started_at=STARTED_AT
        ).model_dump(mode="json")

        assert dumped["question_type"] == "multiple_choice"

    def test_started_at_is_required(self) -> None:
        with pytest.raises(TypeError):
            PublicQuestionSchema.from_domain(_domain_question())  # type: ignore[call-arg]

    def test_naive_started_at_rejected(self) -> None:
        with pytest.raises(ValidationError):
            PublicQuestionSchema.from_domain(
                _domain_question(),
                started_at=datetime(2026, 8, 31, 10, 15, 30),  # naive
            )

    def test_utc_started_at_serializes_with_trailing_z(self) -> None:
        dumped = PublicQuestionSchema.from_domain(
            _domain_question(), started_at=STARTED_AT
        ).model_dump(mode="json")

        assert dumped["started_at"] == "2026-08-31T10:15:30.000Z"

    def test_non_utc_aware_started_at_normalizes_to_utc_z(self) -> None:
        israel = timezone(timedelta(hours=3))

        dumped = PublicQuestionSchema.from_domain(
            _domain_question(),
            started_at=datetime(2026, 8, 31, 13, 15, 30, tzinfo=israel),
        ).model_dump(mode="json")

        assert dumped["started_at"] == "2026-08-31T10:15:30.000Z"

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            QuestionOptionSchema.model_validate(
                {"option_id": "a", "text": "Dana", "is_correct": True}
            )

    def test_mapping_does_not_mutate_domain_question(self) -> None:
        question = _domain_question()

        PublicQuestionSchema.from_domain(question, started_at=STARTED_AT)

        assert question == _domain_question()
        assert question.correct_option_id == "b"


class TestAnswerSubmissionSchema:
    """The §9.4 answer.submit payload contract (wire shape only)."""

    def test_valid_submission_parses(self) -> None:
        schema = AnswerSubmissionSchema.model_validate(
            {"question_id": "q1", "option_id": "b"}
        )

        assert schema.question_id == "q1"
        assert schema.option_id == "b"

    def test_serialized_keys_match_the_contract(self) -> None:
        dumped = AnswerSubmissionSchema(
            question_id="q1", option_id="b"
        ).model_dump(mode="json")

        assert set(dumped.keys()) == {"question_id", "option_id"}

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AnswerSubmissionSchema.model_validate(
                {"question_id": "q1", "option_id": "b", "answered_at": "2026-09-05T10:00:00Z"}
            )

    def test_missing_fields_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AnswerSubmissionSchema.model_validate({"question_id": "q1"})
        with pytest.raises(ValidationError):
            AnswerSubmissionSchema.model_validate({"option_id": "b"})

    def test_client_supplied_timestamp_is_not_part_of_the_contract(self) -> None:
        """Client timestamps carry no authority (§9.4) and are not accepted."""
        assert "answered_at" not in AnswerSubmissionSchema.model_fields
