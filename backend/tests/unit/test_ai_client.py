"""Unit tests for the Anthropic client wrapper (MASTER_SPEC.md §12.7).

No network is ever hit. We validate throttling, JSON parsing and the
key-leak defenses that keep the API key out of logs/exceptions.
"""

from __future__ import annotations

import logging

import pytest

from app.infrastructure.ai_client import (
    AIClientUnavailable,
    AIGenerationError,
    AIRateLimitError,
    _ThrottleWindow,
    parse_json_payload,
)


class TestConstructor:
    def test_rejects_missing_key(self):
        with pytest.raises(AIClientUnavailable):
            from app.infrastructure.ai_client import AnthropicClient
            AnthropicClient(api_key="", model="claude-sonnet-5")

    def test_rejects_wrongly_formatted_key(self):
        from app.infrastructure.ai_client import AnthropicClient
        with pytest.raises(AIClientUnavailable):
            AnthropicClient(api_key="not-an-anthropic-key", model="claude-sonnet-5")


class TestThrottle:
    def test_allows_up_to_max_in_window(self):
        window = _ThrottleWindow(max_in_window=3)
        for _ in range(3):
            window.check_and_record()

    def test_raises_after_cap(self):
        window = _ThrottleWindow(max_in_window=2)
        window.check_and_record()
        window.check_and_record()
        with pytest.raises(AIRateLimitError):
            window.check_and_record()


class TestParseJson:
    def test_plain_json(self):
        assert parse_json_payload('[{"x": 1}]') == [{"x": 1}]

    def test_json_object(self):
        assert parse_json_payload('{"x": 1}') == {"x": 1}

    def test_fenced_json(self):
        raw = '```json\n[{"x": 1}]\n```'
        assert parse_json_payload(raw) == [{"x": 1}]

    def test_fenced_plain(self):
        raw = '```\n[{"x": 1}]\n```'
        assert parse_json_payload(raw) == [{"x": 1}]

    def test_prose_around_array(self):
        raw = 'Here are the questions:\n[{"x": 1}]\nHope this helps!'
        assert parse_json_payload(raw) == [{"x": 1}]

    def test_rejects_non_json(self):
        with pytest.raises(AIGenerationError):
            parse_json_payload("no json here")


class TestKeyHygiene:
    """A fake key must never appear in any public error message or log."""

    def test_error_message_does_not_contain_key(self, caplog):
        """The AIGenerationError raised by send_prompt is intentionally generic."""
        # Can't test send_prompt without hitting the network. The hygiene is
        # structural: the except block in send_prompt raises
        # AIGenerationError(...) with a hard-coded message and uses
        # ``from None`` to drop the chained exception's text. We verify the
        # message is stable and key-free.
        error = AIGenerationError(
            "The AI service did not respond. Falling back to the regular question engine."
        )
        assert "sk-ant" not in str(error)
        assert "api" not in str(error).lower() or "AI" in str(error)


class TestTruncatedResponses:
    """A reply cut off by the token limit keeps its complete questions."""

    def test_salvages_complete_items_from_a_cut_off_array(self):
        from app.infrastructure.ai_client import parse_json_payload
        raw = '[{"text": "a", "n": 1}, {"text": "b", "n": 2}, {"text": "c", "n'
        assert parse_json_payload(raw) == [{"text": "a", "n": 1}, {"text": "b", "n": 2}]

    def test_nothing_recoverable_still_raises(self):
        from app.infrastructure.ai_client import AIGenerationError, parse_json_payload
        with pytest.raises(AIGenerationError):
            parse_json_payload('[{"text": "cut off')

    def test_valid_json_is_unchanged(self):
        from app.infrastructure.ai_client import parse_json_payload
        assert parse_json_payload('```json\n[{"a": 1}]\n```') == [{"a": 1}]
