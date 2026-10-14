"""Anthropic API client wrapper (MASTER_SPEC.md §12.7).

Infrastructure layer. The one place in the codebase that holds the
Anthropic API key and talks to the hosted model. The domain never imports
this module directly; the composition root wires an instance into the
question-generation workstream when ``MIZEMI_AI_ENABLED`` is true.

Hard rules — these keep the API key from leaking:

* The constructor never logs the key.
* Every public method wraps every ``anthropic`` exception into one of the
  module-local errors below. The original exception message is dropped so a
  malformed-request echo cannot carry the key back out through the log/UI
  surfaces that consume the error.
* No part of the key ever appears in a response. ``AIGenerationError`` has a
  stable public message that the realtime/API layers surface to clients.
* The in-process rolling-hour counter is the sole throttle; nothing in the
  database tracks AI usage.
"""

from __future__ import annotations

import json
import logging
import time
from collections import deque
from dataclasses import dataclass

logger = logging.getLogger("mizemi.ai")


class AIClientUnavailable(RuntimeError):
    """The AI client cannot be used (not configured, feature flag off)."""


class AIRateLimitError(RuntimeError):
    """Too many AI games were started within the rolling-hour window."""


class AIGenerationError(RuntimeError):
    """A single call to the Anthropic API failed. Public, key-free message."""


@dataclass(frozen=True)
class _ThrottleWindow:
    """Rolling-hour counter for AI game starts, in process memory only."""

    max_in_window: int
    window_seconds: int = 3600

    def _bucket(self) -> deque[float]:
        bucket = getattr(self, "_bucket_store", None)
        if bucket is None:
            bucket = deque()
            # Stash it on the frozen dataclass via object.__setattr__.
            object.__setattr__(self, "_bucket_store", bucket)
        return bucket

    def check_and_record(self) -> None:
        now = time.monotonic()
        bucket = self._bucket()
        while bucket and bucket[0] + self.window_seconds <= now:
            bucket.popleft()
        if len(bucket) >= self.max_in_window:
            raise AIRateLimitError(
                "AI question generation is temporarily paused. Try again in a few minutes."
            )
        bucket.append(now)


class AnthropicClient:
    """Thin wrapper around the official SDK. Nothing MiZeMi-specific lives here.

    The actual question-generation prompt and parsing live in the question
    engine (``domain/questions/ai_generator.py``). This class owns only the
    transport: send a message, get text back, with timeouts and error
    scrubbing.
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        timeout_seconds: int = 45,
        max_games_per_hour: int = 20,
    ) -> None:
        if not api_key or not api_key.startswith("sk-ant-"):
            raise AIClientUnavailable(
                "Anthropic API key is missing or malformed. Set MIZEMI_ANTHROPIC_API_KEY."
            )
        self._model = model
        self._timeout_seconds = timeout_seconds
        self._throttle = _ThrottleWindow(max_in_window=max_games_per_hour)
        # Import late so the SDK is only loaded when AI is actually enabled.
        from anthropic import Anthropic  # type: ignore[import-not-found]

        self._client = Anthropic(api_key=api_key, timeout=timeout_seconds)

    @property
    def model(self) -> str:
        return self._model

    def send_prompt(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int = 8192,
        counts_toward_limit: bool = True,
    ) -> str:
        """Send one message, return the plain text of the first text block.

        ``counts_toward_limit`` lets a single game spend several calls (a
        retry, a verification pass) against ONE slot of the hourly cap: only
        the first call of a game records a slot.

        Blocking: callers on the event loop must run this in a worker thread.

        Raises:
            AIRateLimitError: hourly cap for this process reached.
            AIGenerationError: anything else (network, auth, 5xx, overload).
                The underlying exception type is logged — never its message,
                which could echo back the key or sensitive payload fragments.
        """
        if counts_toward_limit:
            self._throttle.check_and_record()
        try:
            # Mark the system prompt as cacheable so parallel batches and
            # the verification call do not re-process its tokens each time.
            # The cache lives for 5 minutes on the Anthropic side.
            message = self._client.messages.create(
                model=self._model,
                max_tokens=max_tokens,
                system=[{"type": "text", "text": system,
                         "cache_control": {"type": "ephemeral"}}],
                messages=[{"role": "user", "content": user}],
            )
        except Exception as exc:  # noqa: BLE001 — intentional: scrub everything.
            logger.error("Anthropic request failed: %s", type(exc).__name__)
            raise AIGenerationError(
                "The AI service did not respond. Falling back to the regular question engine."
            ) from None
        if getattr(message, "stop_reason", None) == "max_tokens":
            # The answer was cut off by our own limit; the parser may salvage
            # the complete items. Logged by type only: never the content.
            logger.warning("Anthropic response hit max_tokens (%d)", max_tokens)
        # Flatten the first text block; other block types are ignored.
        text_parts: list[str] = []
        for block in getattr(message, "content", []) or []:
            if getattr(block, "type", None) == "text":
                value = getattr(block, "text", "")
                if isinstance(value, str):
                    text_parts.append(value)
        return "".join(text_parts).strip()


def parse_json_payload(raw: str) -> object:
    """Parse ``raw`` as JSON, tolerating ```json fences and surrounding prose.

    Models often wrap their output in a Markdown code fence or add a short
    explanation around it. We locate the first top-level ``[`` or ``{`` and
    the matching closing bracket, then feed only that slice to ``json.loads``.
    """
    cleaned = raw.strip()
    if cleaned.startswith("```"):
        # Strip ``` or ```json fence.
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else ""
        if cleaned.rstrip().endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
    cleaned = cleaned.strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass
    # Fallback: find balanced [...] or {...} and try again.
    for opener, closer in (("[", "]"), ("{", "}")):
        start = cleaned.find(opener)
        end = cleaned.rfind(closer)
        if 0 <= start < end:
            try:
                return json.loads(cleaned[start : end + 1])
            except json.JSONDecodeError:
                continue
    salvaged = _salvage_complete_items(cleaned)
    if salvaged:
        return salvaged
    raise AIGenerationError("The AI response was not valid JSON.")


def _salvage_complete_items(text: str) -> list[object]:
    """Recover the complete items of a JSON array that was cut off mid-way.

    A long answer that hits the token limit ends in the middle of an object.
    Every item before that point is still intact, so keep those and drop the
    broken tail instead of discarding the whole response.
    """
    start = text.find("[")
    if start < 0:
        return []
    decoder = json.JSONDecoder()
    items: list[object] = []
    position = start + 1
    while position < len(text):
        while position < len(text) and text[position] in " \t\r\n,":
            position += 1
        if position >= len(text) or text[position] == "]":
            break
        try:
            item, position = decoder.raw_decode(text, position)
        except json.JSONDecodeError:
            break
        items.append(item)
    return items
