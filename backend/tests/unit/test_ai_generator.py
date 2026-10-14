"""Unit tests for AIQuestionGenerator (MASTER_SPEC.md §12.7).

The Anthropic client is mocked; no real API call is ever made. The mock tells
the generation call and the verification call apart by their system prompt.
"""

from __future__ import annotations

import json
from unittest.mock import Mock

import pytest

from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions import ProfileDataset
from app.domain.questions.question import Difficulty
from app.domain.questions.ai_generator import (
    VERIFY_SYSTEM_PROMPT,
    AIQuestionGenerator,
    _age_band,
    _argues_from_absence,
    _consented_fields_payload,
    _batch_sizes,
    _content_words,
    _high_overlap,
    _mentions_exact_age,
    _split_plan,
    _topic_plan,
    _unique_and_ordered,
    _AIQuestionRecord,
)
from app.infrastructure.ai_client import AIGenerationError, AIRateLimitError


def _player(pid: str, name: str, *fields: tuple[str, str | int, bool]) -> Player:
    return Player(pid, name, profile=PlayerProfile(
        pid, tuple(ProfileField(k, v, consent) for k, v, consent in fields),
    ))


def _dataset(language: str = "he") -> ProfileDataset:
    return ProfileDataset([
        _player("p1", "אליק",
                ("city", "תל אביב", True), ("favorite_food", "פיצה", True),
                ("hobby", "כדורגל", True), ("age", 25, True)),
        _player("p2", "יאיר",
                ("city", "חיפה", True), ("favorite_food", "סושי", True),
                ("hobby", "ריצה", True), ("age", 27, True)),
        _player("p3", "נועה",
                ("city", "חיפה", True), ("favorite_food", "פיצה", True),
                ("hobby", "קריאה", True), ("age", 30, True)),
    ], language=language)


def _q(text: str, options: list[str] | None = None, correct: int = 0,
       difficulty: str = "EASY", explanation: str = "") -> dict:
    return {
        "text": text,
        "options": options or ["כן", "לא"],
        "correct_index": correct,
        "difficulty": difficulty,
        "explanation": explanation,
    }


def _client(questions: list[dict], *, verdicts: dict[str, str] | None = None,
            generation_raw: str | None = None) -> Mock:
    """Mock client: generation returns ``questions``; verification judges them.

    ``verdicts`` maps question text -> verdict (default: every question is
    "correct"). ``generation_raw`` overrides the raw generation response.
    """
    verdicts = verdicts or {}

    def send(system: str, user: str, **kwargs):
        if system == VERIFY_SYSTEM_PROMPT:
            asked = json.loads(user)["questions"]
            return json.dumps([
                {"index": item["index"], "verdict": verdicts.get(item["text"], "correct")}
                for item in asked
            ])
        if generation_raw is not None:
            return generation_raw
        return json.dumps(questions, ensure_ascii=False)

    client = Mock()
    client.send_prompt = Mock(side_effect=send)
    client.model = "claude-sonnet-5"
    return client


def _generation_requests(client: Mock) -> list[int]:
    """requested_count of every generation call (verification calls excluded)."""
    sizes = []
    for call in client.send_prompt.call_args_list:
        if call.args[0] == VERIFY_SYSTEM_PROMPT:
            continue
        sizes.append(json.loads(call.args[1].split("profiles:\n\n", 1)[1])["requested_count"])
    return sizes


def _generate(client: Mock, *, count: int = 5, dataset: ProfileDataset | None = None):
    return AIQuestionGenerator(client).generate(
        dataset or _dataset(), question_count=count, time_limit_seconds=20, seed=42,
    )


class TestPrivacyPayload:
    """§10.8 — the model never sees non-consented fields, ids or exact ages."""

    def test_non_consented_fields_are_absent(self):
        dataset = ProfileDataset([
            _player("p1", "אליק", ("city", "תל אביב", True),
                    ("personal_fact", "השתתפתי באולימפיאדה", False)),
            _player("p2", "יאיר", ("city", "חיפה", True), ("favorite_food", "סושי", True)),
        ])
        serialized = json.dumps(_consented_fields_payload(dataset), ensure_ascii=False)
        assert "אולימפיאדה" not in serialized
        assert "personal_fact" not in serialized

    def test_player_ids_are_not_exposed(self):
        dataset = _dataset()
        serialized = json.dumps(_consented_fields_payload(dataset))
        for pid in dataset.player_ids:
            assert pid not in serialized

    def test_display_names_are_included(self):
        names = {row["name"] for row in _consented_fields_payload(_dataset())}
        assert names == {"אליק", "יאיר", "נועה"}

    def test_exact_ages_never_reach_the_model(self):
        payload = _consented_fields_payload(_dataset())
        serialized = json.dumps(payload, ensure_ascii=False)
        for exact in ("25", "27", "30"):
            assert f'"{exact}"' not in serialized
            assert f": {exact}" not in serialized
        assert all("age" not in row["answers"] for row in payload)
        assert [row["answers"]["age_range"] for row in payload] == ["25-34", "25-34", "25-34"]

    def test_a_non_consented_age_is_not_sent_at_all(self):
        dataset = ProfileDataset([
            _player("p1", "אליק", ("city", "תל אביב", True), ("age", 41, False)),
            _player("p2", "יאיר", ("city", "חיפה", True)),
        ])
        serialized = json.dumps(_consented_fields_payload(dataset))
        assert "age_range" not in serialized and "41" not in serialized


class TestAgeBands:
    @pytest.mark.parametrize("age,band", [
        (5, "12 and under"), (12, "12 and under"), (13, "13-15"), (15, "13-15"),
        (16, "16-18"), (18, "16-18"), (19, "19-24"), (24, "19-24"),
        (25, "25-34"), (34, "25-34"), (35, "35-49"), (49, "35-49"),
        (50, "50+"), (120, "50+"),
    ])
    def test_bands_follow_the_spec(self, age, band):
        assert _age_band(age) == band


class TestExactAgeFilter:
    def test_flags_a_real_age(self):
        assert _mentions_exact_age(["כמה אנשים בני 27 יש כאן?"], {25, 27, 30})

    def test_flags_it_in_options_and_explanations_too(self):
        assert _mentions_exact_age(["30", "31"], {30})

    def test_a_canonical_band_is_not_an_exact_age(self):
        # A 25-year-old is in the room, yet "25-34" is the allowed band label.
        assert not _mentions_exact_age(["כמה אנשים בני 25-34 יש כאן?"], {25})
        assert not _mentions_exact_age(["How many are 25–34?"], {25, 34})
        assert not _mentions_exact_age(["people aged 50+"], {50})
        assert not _mentions_exact_age(["12 and under"], {12})

    def test_unrelated_numbers_are_fine(self):
        assert not _mentions_exact_age(["כמה תחביבים שונים יש?", "1", "2", "3"], {25, 27})

    def test_no_ages_means_nothing_to_leak(self):
        assert not _mentions_exact_age(["30"], set())


class TestAbsenceFilter:
    @pytest.mark.parametrize("text", [
        "איזה סגנון מוזיקה אינו מופיע בכלל כהעדפה בקבוצה?",
        "איזו עיר לא מופיעה אצל אף אחד?",
        "Which music style does not appear in the group?",
        "Which food did no one choose?",
    ])
    def test_flags_absence_questions(self, text):
        assert _argues_from_absence(text)

    @pytest.mark.parametrize("text", [
        "מה המשותף לשלושת הסרטים האהובים על חברי הקבוצה?",
        "כמה תחביבים שונים יש בקבוצה?",
        "Which food is the most popular in the group?",
    ])
    def test_allows_positive_questions(self, text):
        assert not _argues_from_absence(text)


class TestGenerate:
    def test_produces_verified_questions(self):
        client = _client([
            _q("מהי העיר הנפוצה ביותר בקבוצה?", ["תל אביב", "חיפה", "ירושלים"], 1,
               explanation="שניים מתוך שלושה גרים בחיפה."),
            _q("מי אוהב אוכל אסייתי?", ["אליק", "יאיר", "נועה"], 1, "MEDIUM", "יאיר בחר סושי."),
        ])
        questions = _generate(client)
        assert len(questions) == 2
        first = questions[0]
        assert first.text == "מהי העיר הנפוצה ביותר בקבוצה?"
        assert first.correct_option_id == "b"
        assert first.source_rule_id == "ai_group_insight"
        assert first.knowledge_version == "ai"
        assert first.explanation == "שניים מתוך שלושה גרים בחיפה."
        assert first.language == "he"
        assert [q.index for q in questions] == [0, 1]
        assert all(q.total_questions == 2 for q in questions)

    def test_respects_the_requested_count(self):
        client = _client([_q(f"שאלה {i}", [f"תשובה_{i}", "אחר"], 0) for i in range(10)])
        assert len(_generate(client, count=3)) == 3

    def test_asks_the_model_for_a_surplus(self):
        client = _client([_q("שאלה")])
        _generate(client, count=9)
        # The surplus (9 -> 12) may be split over parallel batches: count them all.
        assert sum(_generation_requests(client)) == 12

    def test_malformed_items_are_skipped(self):
        client = _client([
            _q("good", ["x", "y"], 0),
            {"text": "missing_options"},
            _q("", ["a", "b"], 0),
            _q("out_of_range", ["a", "b"], 7),
            _q("second_good", ["q", "r"], 1, "HARD"),
        ])
        assert [q.text for q in _generate(client, count=10)] == ["good", "second_good"]

    def test_raises_when_nothing_parses(self):
        with pytest.raises(AIGenerationError):
            _generate(_client([{"nonsense": 1}, {"also": "bad"}]))

    def test_needs_at_least_two_players(self):
        single = ProfileDataset([_player("p1", "אליק", ("city", "תל אביב", True))])
        with pytest.raises(AIGenerationError):
            _generate(_client([_q("x")]), dataset=single)

    def test_fenced_json_is_parsed(self):
        fenced = '```json\n[{"text": "x", "options": ["a", "b"], "correct_index": 0,' \
                 ' "difficulty": "EASY", "explanation": "y"}]\n```'
        questions = _generate(_client([], generation_raw=fenced), count=1)
        assert [q.text for q in questions] == ["x"]

    def test_language_defaults_from_the_dataset(self):
        questions = _generate(_client([_q("hello")]), count=1, dataset=_dataset(language="en"))
        assert questions[0].language == "en"

    def test_the_validator_rejects_duplicate_options(self):
        with pytest.raises(AIGenerationError):
            _generate(_client([_q("q", ["same", "same"], 0)]), count=1)

    def test_rate_limit_propagates(self):
        client = Mock()
        client.send_prompt = Mock(side_effect=AIRateLimitError("too many"))
        with pytest.raises(AIRateLimitError):
            _generate(client, count=1)


class TestDeterministicFilters:
    """Regression cases taken from real AI output."""

    def test_a_question_stating_an_exact_age_is_dropped(self):
        client = _client([
            _q("מה הגיל המשותף לכל שלושת המשתתפים בקבוצה?", ["28", "30", "32", "25"], 1,
               explanation="כל המשתתפים בני 30."),
            _q("כמה תחביבים שונים יש בקבוצה?", ["1", "2", "3", "4"], 2),
        ])
        assert [q.text for q in _generate(client)] == ["כמה תחביבים שונים יש בקבוצה?"]

    def test_an_age_in_the_explanation_alone_drops_the_question(self):
        client = _client([_q("מי הצעיר ביותר?", ["אליק", "יאיר"], 0, explanation="אליק בן 25.")])
        with pytest.raises(AIGenerationError):
            _generate(client, count=1)

    def test_an_age_band_question_survives_even_at_a_boundary_age(self):
        client = _client([_q("כמה אנשים בני 25-34 יש בקבוצה?", ["1", "2", "3", "4"], 2)])
        assert len(_generate(client, count=1)) == 1

    def test_an_absence_question_is_dropped(self):
        client = _client([
            _q("איזה סגנון מוזיקה אינו מופיע בכלל כהעדפה בקרב חברי הקבוצה?",
               ["ג'אז", "קלאסי", "רוק", "פופ"], 3),
            _q("כמה תחביבים שונים יש בקבוצה?", ["1", "2", "3", "4"], 2),
        ])
        assert [q.text for q in _generate(client)] == ["כמה תחביבים שונים יש בקבוצה?"]


class TestVerification:
    def test_questions_judged_not_correct_are_dropped(self):
        client = _client(
            [_q("ok"), _q("wrong"), _q("fuzzy")],
            verdicts={"wrong": "incorrect", "fuzzy": "ambiguous"},
        )
        assert [q.text for q in _generate(client)] == ["ok"]

    def test_fails_closed_when_the_verifier_errors(self):
        def send(system, user, **kwargs):
            if system == VERIFY_SYSTEM_PROMPT:
                raise AIGenerationError("down")
            return json.dumps([_q("ok")])
        client = Mock()
        client.send_prompt = Mock(side_effect=send)
        with pytest.raises(AIGenerationError):
            _generate(client, count=1)

    def test_fails_closed_on_an_unreadable_verdict(self):
        def send(system, user, **kwargs):
            return "not json at all" if system == VERIFY_SYSTEM_PROMPT else json.dumps([_q("ok")])
        client = Mock()
        client.send_prompt = Mock(side_effect=send)
        with pytest.raises(AIGenerationError):
            _generate(client, count=1)

    def test_fails_when_nothing_is_verified(self):
        client = _client([_q("a"), _q("b")], verdicts={"a": "ambiguous", "b": "incorrect"})
        with pytest.raises(AIGenerationError):
            _generate(client)

    def test_verdicts_for_unknown_indexes_are_ignored(self):
        def send(system, user, **kwargs):
            if system == VERIFY_SYSTEM_PROMPT:
                return json.dumps([{"index": 99, "verdict": "correct"},
                                   {"index": 0, "verdict": "correct"}])
            return json.dumps([_q("ok")])
        client = Mock()
        client.send_prompt = Mock(side_effect=send)
        assert len(_generate(client, count=1)) == 1


class TestThrottleSlots:
    def test_a_game_spends_one_slot_even_with_verification(self):
        client = _client([_q("ok")])
        _generate(client, count=1)
        flags = [call.kwargs["counts_toward_limit"] for call in client.send_prompt.call_args_list]
        assert flags == [True, False]  # generation counts, verification does not

    def test_a_retry_does_not_spend_a_second_slot(self):
        calls = {"generation": 0}

        def send(system, user, **kwargs):
            if system == VERIFY_SYSTEM_PROMPT:
                return json.dumps([{"index": 0, "verdict": "correct"}])
            calls["generation"] += 1
            return "garbage" if calls["generation"] == 1 else json.dumps([_q("ok")])
        client = Mock()
        client.send_prompt = Mock(side_effect=send)
        assert len(_generate(client, count=1)) == 1
        flags = [call.kwargs["counts_toward_limit"] for call in client.send_prompt.call_args_list]
        assert flags == [True, False, False]


class TestTopicPlan:
    """The question budget follows how many players filled each field in."""

    @staticmethod
    def _rows(*answer_sets: dict) -> list[dict]:
        return [{"name": f"p{i}", "answers": a} for i, a in enumerate(answer_sets)]

    def test_budget_is_split_by_coverage(self):
        rows = self._rows(
            {"city": "a", "hobby": "x", "favorite_movie": "m"},
            {"city": "b", "hobby": "y", "favorite_movie": "n"},
            {"city": "c", "hobby": "z"},
        )
        plan = _topic_plan(rows, 8)
        assert sum(plan.values()) == 8
        # city and hobby were answered by 3 players, movie by 2.
        assert plan["city"] == plan["hobby"] == 3 and plan["favorite_movie"] == 2

    def test_a_field_nobody_or_only_one_player_filled_gets_nothing(self):
        rows = self._rows({"city": "a", "favorite_song": "s"}, {"city": "b"}, {"city": "c"})
        assert _topic_plan(rows, 6) == {"city": 6}

    def test_the_free_text_personal_fact_is_never_planned(self):
        rows = self._rows({"city": "a", "personal_fact": "x"}, {"city": "b", "personal_fact": "y"})
        assert "personal_fact" not in _topic_plan(rows, 4)

    def test_blank_values_do_not_count(self):
        rows = self._rows({"city": "a", "hobby": "  "}, {"city": "b", "hobby": ""})
        assert _topic_plan(rows, 4) == {"city": 4}

    def test_the_plan_always_sums_to_the_total_and_is_deterministic(self):
        rows = self._rows(*({"city": "a", "hobby": "b", "favorite_food": "c"} for _ in range(3)))
        for total in range(1, 30):
            plan = _topic_plan(rows, total)
            assert sum(plan.values()) == total
            assert plan == _topic_plan(rows, total)

    def test_nothing_to_plan_when_no_field_is_shared(self):
        assert _topic_plan(self._rows({"city": "a"}, {}), 5) == {}

    def test_the_plan_reaches_the_model(self):
        client = _client([_q("שאלה")])
        _generate(client, count=9)
        prompt = client.send_prompt.call_args_list[0].args[1]
        sent = json.loads(prompt.split("profiles:\n\n", 1)[1])
        assert sum(sent["topic_plan"].values()) == sent["requested_count"]
        assert set(sent["topic_plan"]) == {"city", "favorite_food", "hobby", "age_range"}


class TestBatching:
    """A full game is written as several parallel requests, not one giant one."""

    @pytest.mark.parametrize("total", [1, 6, 10, 11, 26, 50])
    def test_batches_are_small_and_add_up(self, total):
        sizes = _batch_sizes(total)
        assert sum(sizes) == total and max(sizes) <= 10 and min(sizes) >= 1

    def test_the_plan_is_dealt_across_batches_without_loss(self):
        plan = {"city": 4, "hobby": 4, "favorite_food": 2, "age_range": 2}
        sizes = _batch_sizes(12)
        parts = _split_plan(plan, sizes)
        assert [sum(p.values()) for p in parts] == sizes
        merged: dict[str, int] = {}
        for part in parts:
            for key, units in part.items():
                merged[key] = merged.get(key, 0) + units
        assert merged == plan

    def test_a_twenty_question_game_is_not_one_request(self):
        client = _client([_q("שאלה")])
        _generate(client, count=20)
        sizes = _generation_requests(client)
        assert len(sizes) >= 3 and max(sizes) <= 10 and sum(sizes) == 26

    def test_exactly_one_slot_of_the_hourly_cap_is_spent(self):
        client = _client([_q("שאלה")])
        _generate(client, count=20)
        counted = [c for c in client.send_prompt.call_args_list
                   if c.kwargs.get("counts_toward_limit")]
        assert len(counted) == 1

    def test_exact_duplicates_across_batches_are_dropped(self):
        client = _client([_q("אותה שאלה בדיוק")])  # every batch returns the same one
        questions = _generate(client, count=20)
        assert [q.text for q in questions] == ["אותה שאלה בדיוק"]

    def test_same_answer_semantic_duplicates_are_dropped(self):
        client = _client([
            _q("איזו עיר מופיעה פעמיים?", ["תל אביב", "חיפה"], 1),
            _q("איזו עיר משותפת?", ["תל אביב", "חיפה"], 1),
            _q("איזו עיר נבחרה על ידי שניים?", ["תל אביב", "חיפה"], 1),
            _q("כמה ערים שונות?", ["2", "3", "4"], 1),
        ])
        questions = _generate(client, count=10)
        # The three "חיפה" answers collapse to one; "3" (numeric) is kept.
        assert len(questions) == 2
        assert questions[0].text == "איזו עיר מופיעה פעמיים?"
        assert questions[1].text == "כמה ערים שונות?"

    def test_one_failed_batch_does_not_sink_the_game(self):
        calls = {"n": 0}
        good = _client([_q("שאלה טובה")])

        def send(system, user, **kwargs):
            if system != VERIFY_SYSTEM_PROMPT:
                calls["n"] += 1
                if "\"requested_count\": 9" in user and calls["n"] % 3 == 0:
                    raise AIGenerationError("boom")
            return good.send_prompt.side_effect(system, user, **kwargs)

        client = Mock()
        client.send_prompt = Mock(side_effect=send)
        assert len(_generate(client, count=20)) >= 1

    def test_all_batches_failing_still_raises_for_the_fallback(self):
        client = Mock()
        client.send_prompt = Mock(side_effect=AIGenerationError("down"))
        with pytest.raises(AIGenerationError):
            _generate(client, count=20)

    def test_questions_come_back_easy_to_hard(self):
        client = _client([
            _q("קשה", difficulty="HARD"), _q("קל", difficulty="EASY"),
            _q("בינוני", difficulty="MEDIUM"),
        ])
        order = [q.difficulty.value for q in _generate(client, count=3)]
        assert order == sorted(order, key={"EASY": 0, "MEDIUM": 1, "HARD": 2}.get)


class TestContentOverlapDedup:
    """Rephrased questions (same fact, different wording) are collapsed."""

    @staticmethod
    def _rec(text, options=("a", "b"), correct=0, difficulty="EASY", explanation=""):
        return _AIQuestionRecord(text, options, correct, Difficulty(difficulty), explanation)

    def test_rephrased_marvel_questions_are_collapsed(self):
        records = [
            self._rec("כמה סרטי מארוול?", ("1", "2", "3"), 2, explanation="Hulk Spider-Man Endgame מארוול"),
            self._rec("כמה מהסרטים שייכים למארוול?", ("1", "2", "3"), 2, explanation="Hulk Spider-Man Endgame מבוססים על מארוול"),
            self._rec("כמה סרטי גיבורי-על של מארוול?", ("אחד", "שניים", "שלושה"), 2, explanation="Hulk Spider-Man Endgame מארוול גיבורי-על"),
        ]
        assert len(_unique_and_ordered(records)) == 1

    def test_different_topics_with_same_numeric_answer_are_kept(self):
        records = [
            self._rec("כמה ערים שונות?", ("2", "3", "4"), 1, explanation="תל אביב חיפה ירושלים שלוש ערים"),
            self._rec("כמה תחביבים שונים?", ("2", "3", "4"), 1, explanation="כדורגל ריצה קריאה שלושה תחביבים"),
        ]
        assert len(_unique_and_ordered(records)) == 2

    def test_hebrew_number_words_are_normalised_in_answer_dedup(self):
        records = [
            self._rec("שאלה א", ("תל אביב", "חיפה"), 1, explanation="first"),
            self._rec("שאלה ב", ("ירושלים", "חיפה"), 1, explanation="second different enough words here"),
        ]
        # Both have non-numeric answer "חיפה" → second is dropped
        assert len(_unique_and_ordered(records)) == 1

    def test_content_overlap_needs_enough_words(self):
        records = [
            self._rec("שאלה קצרה", ("כן", "לא"), 0, explanation="קצר"),
            self._rec("שאלה אחרת קצרה", ("כן", "לא"), 1, explanation="קצר"),
        ]
        # Short content (< 4 words) → overlap check skipped, both kept
        assert len(_unique_and_ordered(records)) == 2
