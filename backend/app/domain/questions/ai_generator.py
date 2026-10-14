"""AI-backed question generator (MASTER_SPEC.md §12.7).

The algorithmic engine stays the default. When a room opts into
``question_source="ai"`` and the deployment has an Anthropic key configured,
the application layer calls this generator instead. Every question passes
through four independent gates before a player can see it:

1. **Privacy by construction** — the model only receives consented fields,
   and exact ages are replaced by the SPEC's age bands (§12.6), so the model
   cannot leak an exact age it never saw.
2. **Deterministic filters** — a question that still states an exact age, or
   that argues from absence ("which style does not appear"), is dropped. These
   do not depend on the model behaving.
3. **Structural validation** — the shared ``QuestionValidator`` (option
   count, duplicates, answer named in the question, ...), identical to the
   algorithmic path.
4. **Verification pass** — a second, separate call asks the model to
   fact-check each surviving question against the same data. Only questions
   judged ``correct`` are kept. This reduces — it cannot eliminate — wrong
   answers: unlike the algorithmic rules, nothing here is mathematically
   proven. Verification fails closed.

Any failure raises ``AIGenerationError`` with a stable public message; the
application layer then falls back to the algorithmic generator.

Threading: ``generate`` is blocking (it makes network calls). It only reads
the immutable ``ProfileDataset`` it is given, so it is safe to run in a worker
thread — the realtime layer must not call it on the event loop.
"""

from __future__ import annotations

import json
import logging
import random
import re
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import TYPE_CHECKING

from app.domain.questions.candidate import QuestionCandidate
from app.domain.questions.dataset import ProfileDataset
from app.domain.questions.question import Difficulty, Question, QuestionOption, QuestionType
from app.domain.questions.validator import QuestionValidator
from app.infrastructure.ai_client import AIGenerationError, parse_json_payload

if TYPE_CHECKING:  # pragma: no cover
    from app.infrastructure.ai_client import AnthropicClient

logger = logging.getLogger("mizemi.ai.generator")

_SOURCE_RULE_ID = "ai_group_insight"
_OPTION_ALPHABET = ("a", "b", "c", "d")
_MAX_ATTEMPTS = 2  # generation is retried once if the first pass yields nothing
_QUESTION_ID_BITS = 128
_GENERATION_MAX_TOKENS = 6000  # Hebrew is token-heavy: 8 questions ≈ 4-5k tokens
# One request for a whole 20-question game (26 with surplus) in Hebrew does not
# fit in a single response and takes minutes. Several smaller requests run in
# parallel, each finishing well inside the timeout.
_BATCH_SIZE = 8  # small games fit in one batch; large games split in parallel
_VERIFICATION_MAX_TOKENS = 1024

# The SPEC §12.6 age bands. The model is only ever shown these labels.
_AGE_BANDS = (
    (12, "12 and under"),
    (15, "13-15"),
    (18, "16-18"),
    (24, "19-24"),
    (34, "25-34"),
    (49, "35-49"),
)
_OLDEST_BAND = "50+"


SYSTEM_PROMPT = """\
You design questions for MiZeMi, an in-person icebreaker game. The
group just met. Your only job: help them discover WHO THEY ARE AS A
GROUP — shared tastes, hidden overlaps, uniqueness, the room's shape.

CORE TEST. A good question's answer tells the room something it did
not know. A BAD question is trivia dressed up with player names.

TRIVIA IS BANNED. The answer MUST come from the players' profile data
alone. Do NOT bring in outside knowledge: not release years, not
decades, not country or nationality of artists, not movie franchises
(Marvel, DC), not cuisine origin, not geography (coasts, mountains,
north/south). If the question could be answered without seeing the
profiles, it is trivia and you must NOT write it.

Forbidden examples (and why):
- "Elick lives in Tiberias, Yair in Ramat Gan. Which is further north?"
  → geography trivia. Players are decoration.
- "Which chosen food comes from Italian cuisine?" → cuisine trivia.
- "How many of the chosen movies are Marvel?" → franchise trivia.
- "Which chosen song was released in the 80s?" → year trivia.
- "Which chosen artist is from France?" → nationality trivia.

QUESTION SHAPES — pick only from these five:
1. SHARED TASTE: "איזה סגנון בחרו הכי הרבה בקבוצה?"
2. UNIQUE VOICE: "מי היחיד בקבוצה שבחר אוכל אסייתי?"
3. HIDDEN CONNECTION: "אילו שני אנשים חולקים אותו אמן אהוב?"
4. GROUP SHAPE: "כמה ערים שונות מיוצגות?"
5. BRIDGE: "עם מי מהקבוצה אליק הכי דומה בטעמים?"

HARD RULES:
* 2-4 options, exactly one verifiable correct answer from the data.
* Use players' display names as given — never "player one" / "משתמש אחד".
* AGES only as ranges ("25-34"). Never state or hint an exact age.
* NEVER ask about absence ("which style does not appear").
* Follow "topic_plan" in the input: it tells you how many questions
  to build per field (based on how many players filled it in).
  Never ask about a field not in the plan.
* DIVERSITY: every question reveals a DIFFERENT fact. Do not repeat
  the same correct answer across two questions.
* No stereotypes, no personality judgements.
* Write in the requested language.
* Order easy → hard.

DIFFICULTY — all about the GROUP, never trivia:
* EASY: direct observation. "איזו עיר מופיעה הכי הרבה?"
* MEDIUM: combines two fields of the same players, or compares
  subgroups. "מי מבין אוהבי הפופ גר בחיפה?"
* HARD: cross-group insight — the most-unique player, two players
  with the most in common, etc. NOT outside knowledge.
  "אילו שני שחקנים חולקים הכי הרבה טעמים?"

Distribute ~30% EASY, ~50% MEDIUM, ~20% HARD. Include ≥1 HARD when
total ≥ 5.

Output: strict JSON only. No prose, no markdown fences.

[{"text":"...","options":["...","..."],"correct_index":0,
  "difficulty":"EASY|MEDIUM|HARD",
  "explanation":"one short sentence, cite players by name"}]
"""


VERIFY_SYSTEM_PROMPT = """\
Review each question of a MiZeMi icebreaker quiz. You see the players'
data and each question with its claimed correct option. Judge:

* "correct": the claimed answer follows from the players' data alone,
  no other option fits, AND the question reveals something about the
  group (not outside trivia).
* "incorrect": the answer is wrong, OR the question is trivia (its
  answer depends on year, decade, nationality, franchise, cuisine,
  geography, or any fact the players did not type).
* "ambiguous": more than one option fits, data does not settle it,
  the question uses "player one" / "משתמש אחד" instead of real names,
  or you are not sure.

Be strict: when a question smells like trivia, mark it "incorrect".
Ages are ranges only; questions needing exact age → "ambiguous".

Output JSON only, one entry per question in order:
[{"index": 0, "verdict": "correct"}, ...]
"""


# --- privacy payload -----------------------------------------------------------

def _age_band(age: int) -> str:
    for upper, label in _AGE_BANDS:
        if age <= upper:
            return label
    return _OLDEST_BAND


def _as_int(value: object) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def _consented_fields_payload(dataset: ProfileDataset) -> list[dict[str, object]]:
    """Serialize the dataset into exactly what the model may see.

    ``ProfileDataset`` already drops non-consented fields. Additionally: no
    ``player_id``, and ``age`` is reduced to its SPEC band so an exact age
    never leaves the server.
    """
    rows: list[dict[str, object]] = []
    for player_id in dataset.player_ids:
        answers: dict[str, object] = {}
        for field in dataset.fields_for(player_id):
            if field.field_key == "age":
                age = _as_int(field.value)
                if age is not None:
                    answers["age_range"] = _age_band(age)
                continue
            answers[field.field_key] = field.value
        rows.append({
            "name": dataset.display_name_for(player_id),
            "answers": answers,
        })
    return rows


def _known_ages(dataset: ProfileDataset) -> set[int]:
    ages: set[int] = set()
    for player_id in dataset.player_ids:
        for field in dataset.fields_for(player_id):
            if field.field_key == "age":
                age = _as_int(field.value)
                if age is not None:
                    ages.add(age)
    return ages


# --- deterministic filters -----------------------------------------------------

# Canonical SPEC band expressions are allowed even when a player is exactly one
# of the boundary ages (e.g. a 25-year-old and the phrase "25-34").
_BAND_EXPRESSION = re.compile(
    r"""
      12\s*(?:and\s+under|or\s+(?:under|younger)|ומטה|ומתחת)
    | \b50\s*\+ | \+\s*50
    | \b50\s*(?:and\s+(?:over|above|older)|or\s+(?:over|older)|ומעלה)
    | \b(?:13\s*[-–—]\s*15|16\s*[-–—]\s*18|19\s*[-–—]\s*24
        |25\s*[-–—]\s*34|35\s*[-–—]\s*49)\b
    """,
    re.VERBOSE | re.IGNORECASE,
)
_STANDALONE_INTEGER = re.compile(r"(?<![\w.])(\d{1,3})(?!\w)")

_ABSENCE_CLAIM = re.compile(
    r"""
      not\s+(?:appear|represented|chosen|picked|selected|present|mentioned)
    | doesn'?t\s+appear | does\s+not\s+appear
    | isn'?t\s+(?:represented|chosen|present) | aren'?t\s+(?:represented|chosen)
    | \b(?:no\s+one|nobody|none\s+of)\b
    | אינ(?:ו|ה)\s+(?:מופיע|מופיעה|מיוצג|מיוצגת|נבחר|נבחרת)
    | לא\s+(?:מופיע|מופיעה|מיוצג|מיוצגת|נבחר|נבחרה|נבחרת)
    | אף\s+(?:אחד|אחת|משתתף)
    | אין\s+אף
    """,
    re.VERBOSE | re.IGNORECASE,
)

# Trivia-style questions sneak past the model even when the prompt bans
# them. These patterns are high-confidence markers of a question whose
# correct answer depends on outside knowledge (release year, decade,
# nationality, franchise, geography, cuisine origin) rather than on the
# players' profile data. False positives only cost one question each.
_TRIVIA_MARKERS = re.compile(
    r"""
      # release year / decade — Hebrew and English
      יצא\s+(?:ב[-'־]?\s*)?(?:19|20)\d{2}
    | יצא\s+לאור
    | שנות\s+ה[-'־]?\s*(?:50|60|70|80|90|2000|2010|2020)
    | released\s+in\s+(?:19|20)\d{2}
    | released\s+in\s+the\s+(?:50|60|70|80|90|'?70|'?80|'?90|2000|2010|2020)
    # franchise / based-on classification
    | מבוסס(?:ים)?\s+על\s+דמ(?:ו|ות)
    | מבוסס(?:ים|ות)?\s+על\s+(?:מארוול|marvel|dc)
    | שייכ(?:ים|ות)?\s+ל(?:מארוול|marvel|dc|עולם\s+גיבורי)
    | מארוול | marvel | \bdc\s+(?:comic|comics|universe) | קומיקס
    # nationality / country of origin of an artist / band / song
    | מגיע(?:ים|ות)?\s+מ(?:צרפת|בריטניה|ארה[״\"']?ב|אמריקה|גרמניה|שבדיה|אוסטרליה|קנדה|יפן)
    | (?:דואט|להקה|אמן|זמר|זמרת)\s+(?:צרפתי|בריטי|אמריקאי|גרמני|שבדי|אוסטרלי|קנדי|יפני)
    | from\s+(?:the\s+)?(?:uk|usa|us\b|united\s+kingdom|united\s+states|france|germany|sweden|australia|canada|japan)
    # geography trivia about Israel
    | חוף\s+הים\s+התיכון
    | ער(?:י|ים)\s+חוף
    | עיר\s+הרים | בהרי\s+יהודה
    | קו\s+אווירי
    # cuisine origin — only flag the explicit "from X cuisine" phrasing
    | מגיע(?:ים|ות)?\s+מהמטבח
    | ממקור\s+(?:איטלקי|אסייתי|צרפתי|מקסיקני|יפני|תאילנדי|סיני|הודי)
    """,
    re.VERBOSE | re.IGNORECASE,
)


def _is_trivia(text: str, explanation: str) -> bool:
    """A question that would score 100% on Wikipedia alone, no players needed."""
    return bool(
        _TRIVIA_MARKERS.search(text) or _TRIVIA_MARKERS.search(explanation)
    )


def _mentions_exact_age(texts: Iterable[str], ages: set[int]) -> bool:
    """True if any text states a number equal to a real player's age.

    Canonical age-band expressions are removed first, so "25-34" does not
    count as revealing a 25-year-old. Conservative by design: a false positive
    only drops one question.
    """
    if not ages:
        return False
    for text in texts:
        cleaned = _BAND_EXPRESSION.sub(" ", text)
        for match in _STANDALONE_INTEGER.finditer(cleaned):
            if int(match.group(1)) in ages:
                return True
    return False


def _argues_from_absence(text: str) -> bool:
    return _ABSENCE_CLAIM.search(text) is not None


# --- parsing -------------------------------------------------------------------

@dataclass(frozen=True)
class _AIQuestionRecord:
    """One parsed question coming back from the model."""

    text: str
    options: tuple[str, ...]
    correct_index: int
    difficulty: Difficulty
    explanation: str


def _parse_question_record(raw: object) -> _AIQuestionRecord | None:
    """Turn one model dict into a validated record, or None if malformed."""
    if not isinstance(raw, dict):
        return None
    text = raw.get("text")
    options = raw.get("options")
    correct_index = raw.get("correct_index")
    difficulty_raw = raw.get("difficulty", "EASY")
    explanation = raw.get("explanation", "")
    if not isinstance(text, str) or not text.strip():
        return None
    if not isinstance(options, list) or not 2 <= len(options) <= 4:
        return None
    option_strings: list[str] = []
    for item in options:
        if not isinstance(item, str) or not item.strip():
            return None
        option_strings.append(item.strip())
    if (
        isinstance(correct_index, bool)
        or not isinstance(correct_index, int)
        or not 0 <= correct_index < len(option_strings)
    ):
        return None
    if not isinstance(difficulty_raw, str):
        return None
    try:
        difficulty = Difficulty(difficulty_raw.strip().upper())
    except ValueError:
        difficulty = Difficulty.MEDIUM
    if not isinstance(explanation, str):
        explanation = ""
    return _AIQuestionRecord(
        text=text.strip(),
        options=tuple(option_strings),
        correct_index=correct_index,
        difficulty=difficulty,
        explanation=explanation.strip()[:1200],
    )


def _candidate_from_record(record: _AIQuestionRecord, dataset: ProfileDataset) -> QuestionCandidate:
    """Build a QuestionCandidate (goes through the standard validator)."""
    options = tuple(
        QuestionOption(option_id=_OPTION_ALPHABET[i], text=record.options[i])
        for i in range(len(record.options))
    )
    return QuestionCandidate(
        text=record.text,
        options=options,
        correct_option_id=_OPTION_ALPHABET[record.correct_index],
        source_rule_id=_SOURCE_RULE_ID,
        source_field_keys=(),
        # Every consented player: the validator only checks that ids are known.
        involved_player_ids=dataset.player_ids,
        difficulty=record.difficulty,
        explanation=record.explanation,
        knowledge_version="ai",
    )


# --- prompts -------------------------------------------------------------------

_PLAN_MIN_ANSWERS = 2  # one answer says nothing about the group


def _topic_plan(rows: list[dict[str, object]], total: int) -> dict[str, int]:
    """Split ``total`` questions across fields by how many players filled each in.

    Dynamic on purpose: the more of the group answered a field, the more
    group-level questions it can support. Fields answered by fewer than two
    players, and the free-text personal fact, get no questions. Largest
    remainder keeps the sum exactly ``total``; ties break by field name so the
    plan is deterministic.
    """
    coverage: dict[str, int] = {}
    for row in rows:
        answers = row["answers"]
        if not isinstance(answers, dict):
            continue
        for key, value in answers.items():
            if key != "personal_fact" and str(value).strip():
                coverage[key] = coverage.get(key, 0) + 1
    eligible = {k: n for k, n in coverage.items() if n >= _PLAN_MIN_ANSWERS}
    weight = sum(eligible.values())
    if weight == 0 or total < 1:
        return {}
    quotas = {k: total * n / weight for k, n in eligible.items()}
    plan = {k: int(q) for k, q in quotas.items()}
    leftover = total - sum(plan.values())
    for key in sorted(quotas, key=lambda k: (-(quotas[k] - plan[k]), k))[:leftover]:
        plan[key] += 1
    return {k: n for k, n in sorted(plan.items()) if n > 0}


_DIFFICULTY_ORDER = {Difficulty.EASY: 0, Difficulty.MEDIUM: 1, Difficulty.HARD: 2}


_NUMERIC_ANSWER = re.compile(r"^\d+$")

_HE_NUM_WORDS: dict[str, str] = {
    "אפס": "0", "אחד": "1", "אחת": "1",
    "שניים": "2", "שתיים": "2",
    "שלושה": "3", "שלוש": "3",
    "ארבעה": "4", "ארבע": "4",
}


_WORD_TOKEN = re.compile(r"[\w-]+", re.UNICODE)


def _content_words(text: str) -> frozenset[str]:
    return frozenset(w for w in _WORD_TOKEN.findall(text.casefold()) if len(w) >= 3)


def _high_overlap(a: frozenset[str], b: frozenset[str]) -> bool:
    if len(a) < 4 or len(b) < 4:
        return False
    return len(a & b) / min(len(a), len(b)) > 0.75


def _unique_and_ordered(records: list[_AIQuestionRecord]) -> list[_AIQuestionRecord]:
    """Merge parallel batches: drop repeated questions, order easy -> hard.

    Three passes:
    1. Exact text dedup (casefold + collapse whitespace).
    2. Same-answer dedup for non-numeric answers (two questions whose correct
       answer is "חיפה" almost certainly test the same fact). Hebrew number
       words are normalised to digits so "שלושה" and "3" are both numeric.
    3. Content-overlap dedup: if two questions share > 75 % of their content
       words (question + explanation), the later one is dropped. This catches
       rephrased questions across batches, e.g. three variants of "how many
       Marvel movies".
    """
    # Pass 1: exact question text
    seen_text: set[str] = set()
    pass1: list[_AIQuestionRecord] = []
    for record in records:
        key = " ".join(record.text.casefold().split())
        if key not in seen_text:
            seen_text.add(key)
            pass1.append(record)
    # Pass 2: same non-numeric correct answer
    seen_answer: set[str] = set()
    pass2: list[_AIQuestionRecord] = []
    for record in pass1:
        answer = record.options[record.correct_index].strip()
        normalised = _HE_NUM_WORDS.get(answer, answer)
        if _NUMERIC_ANSWER.fullmatch(normalised):
            pass2.append(record)
            continue
        answer_key = " ".join(normalised.casefold().split())
        if answer_key not in seen_answer:
            seen_answer.add(answer_key)
            pass2.append(record)
    # Pass 3: content-word overlap
    kept: list[frozenset[str]] = []
    pass3: list[_AIQuestionRecord] = []
    for record in pass2:
        words = _content_words(f"{record.text} {record.explanation}")
        if any(_high_overlap(words, k) for k in kept):
            continue
        kept.append(words)
        pass3.append(record)
    return sorted(pass3, key=lambda r: _DIFFICULTY_ORDER[r.difficulty])  # stable


_SMALL_GAME_THRESHOLD = 5  # <= this many questions skips the verify call


def _requested_count(question_count: int) -> int:
    """Ask for a surplus so filters, dedup and verify can drop candidates.

    Small games keep the surplus tiny: the strict prompt + trivia filter +
    structural validator carry quality, and the verify call is skipped to
    stay under the 60-second budget hosts expect.
    """
    if question_count <= _SMALL_GAME_THRESHOLD:
        return question_count + 2
    return min(50, question_count + max(3, question_count // 2))


def _batch_sizes(total: int) -> list[int]:
    """Split ``total`` requested questions into near-equal batches of <= _BATCH_SIZE."""
    batches = max(1, -(-total // _BATCH_SIZE))
    base, extra = divmod(total, batches)
    return [base + (1 if i < extra else 0) for i in range(batches)]


def _split_plan(plan: dict[str, int], sizes: list[int]) -> list[dict[str, int]]:
    """Deal the topic plan out across batches so no two batches share a topic slot.

    Units of one topic go to different batches in turn, which keeps the parallel
    requests from writing the same question twice.
    """
    parts: list[dict[str, int]] = [{} for _ in sizes]
    room = list(sizes)
    turn = 0
    for key, units in plan.items():
        for _ in range(units):
            for _ in range(len(sizes)):
                if room[turn] > 0:
                    break
                turn = (turn + 1) % len(sizes)
            else:
                return parts
            parts[turn][key] = parts[turn].get(key, 0) + 1
            room[turn] -= 1
            turn = (turn + 1) % len(sizes)
    return parts


def _build_user_prompt(
    dataset: ProfileDataset,
    count: int,
    language: str,
    plan: dict[str, int] | None = None,
    *,
    batch: tuple[int, int] = (1, 1),
) -> str:
    lang_label = {"he": "Hebrew (עברית)", "en": "English"}.get(language, language)
    players = _consented_fields_payload(dataset)
    payload = {
        "language": language,
        "requested_count": count,
        "player_count": dataset.player_count,
        "topic_plan": _topic_plan(players, count) if plan is None else plan,
        "players": players,
    }
    split_note = ""
    if batch[1] > 1:
        if batch[0] == 1:
            diff_focus = "Focus on EASY questions for this part."
        elif batch[0] == batch[1]:
            diff_focus = "Focus on HARD and upper-MEDIUM questions for this part."
        else:
            diff_focus = "Focus on MEDIUM questions for this part."
        split_note = (
            f"The full quiz is written in {batch[1]} parts at the same time; "
            f"this is part {batch[0]}. Write exactly the topics in your "
            f"topic_plan and make every question clearly distinct from anything "
            f"the other parts might write about the same topic. {diff_focus} "
        )
    return (
        f"Please design up to {count} questions in {lang_label}. "
        + split_note
        + "Scale progressively from easy observations to deeper group insights. "
        "The group's shared profiles:\n\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
    )


def _build_verify_prompt(dataset: ProfileDataset, candidates: list[QuestionCandidate]) -> str:
    questions = []
    for index, candidate in enumerate(candidates):
        correct_text = next(
            o.text for o in candidate.options if o.option_id == candidate.correct_option_id
        )
        questions.append({
            "index": index,
            "text": candidate.text,
            "options": [o.text for o in candidate.options],
            "claimed_correct": correct_text,
        })
    return json.dumps(
        {"players": _consented_fields_payload(dataset), "questions": questions},
        ensure_ascii=False,
    )


# --- generator -----------------------------------------------------------------

class AIQuestionGenerator:
    """Alternate question source: ask Claude, filter, verify, hand back ``Question``s.

    Shares the contract ``StartGameService`` expects from
    ``QuestionGenerator.generate``.
    """

    def __init__(
        self,
        client: "AnthropicClient",
        *,
        validator: QuestionValidator | None = None,
    ) -> None:
        self._client = client
        self._validator = validator if validator is not None else QuestionValidator()

    def generate(
        self,
        dataset: ProfileDataset,
        *,
        question_count: int,
        time_limit_seconds: int,
        seed: int,
        language: str | None = None,
    ) -> tuple[Question, ...]:
        if question_count < 1:
            raise ValueError("question_count must be at least 1")
        if dataset.player_count < 2:
            raise AIGenerationError("Not enough players for AI question generation yet.")

        effective_language = (language or dataset.language or "en").lower()
        rng = random.Random(seed)
        parsed = self._request_questions(dataset, question_count, effective_language)
        accepted = self._filter_candidates(dataset, parsed)
        if not accepted:
            raise AIGenerationError("All AI questions were rejected by the filters.")
        # Small games skip the verify call to stay under the host's ~60 s
        # budget. The strict prompt + trivia filter + dedup + structural
        # validator still gate the output; verification is a safety-net that
        # costs an extra API round-trip we can afford only on larger games.
        if question_count <= _SMALL_GAME_THRESHOLD:
            verified = accepted[:question_count]
        else:
            verified = self._verify(dataset, accepted)[:question_count]

        total = len(verified)
        return tuple(
            Question(
                question_id=f"{rng.getrandbits(_QUESTION_ID_BITS):032x}",
                index=index,
                total_questions=total,
                question_type=QuestionType.MULTIPLE_CHOICE,
                text=candidate.text,
                options=candidate.options,
                correct_option_id=candidate.correct_option_id,
                time_limit_seconds=time_limit_seconds,
                difficulty=candidate.difficulty,
                language=effective_language,
                source_rule_id=_SOURCE_RULE_ID,
                explanation=candidate.explanation,
                knowledge_version="ai",
            )
            for index, candidate in enumerate(verified)
        )

    # -- stage 1: generation -------------------------------------------------------

    def _request_questions(
        self, dataset: ProfileDataset, question_count: int, language: str
    ) -> list[_AIQuestionRecord]:
        total = _requested_count(question_count)
        sizes = _batch_sizes(total)
        rows = _consented_fields_payload(dataset)
        plans = _split_plan(_topic_plan(rows, total), sizes)

        def run(index: int) -> list[_AIQuestionRecord]:
            prompt = _build_user_prompt(
                dataset, sizes[index], language, plans[index], batch=(index + 1, len(sizes))
            )
            # Only the very first call of a game spends a slot of the hourly cap.
            return self._request_batch(prompt, counts_slot=(index == 0))

        if len(sizes) == 1:
            outcomes: list[list[_AIQuestionRecord] | Exception] = [run(0)]
        else:
            with ThreadPoolExecutor(max_workers=len(sizes), thread_name_prefix="mizemi-ai-batch") as pool:
                futures = [pool.submit(run, i) for i in range(len(sizes))]
                outcomes = []
                for future in futures:
                    try:
                        outcomes.append(future.result())
                    except AIGenerationError as exc:
                        outcomes.append(exc)
        records: list[_AIQuestionRecord] = []
        failure: Exception | None = None
        for outcome in outcomes:
            if isinstance(outcome, Exception):
                failure = outcome
            else:
                records.extend(outcome)
        if not records:
            raise failure or AIGenerationError("The AI returned no usable questions.")
        if failure is not None:
            logger.warning("AI: some batches failed; continuing with the rest")
        return _unique_and_ordered(records)

    def _request_batch(self, user_prompt: str, *, counts_slot: bool) -> list[_AIQuestionRecord]:
        last_error: Exception | None = None
        for attempt in range(_MAX_ATTEMPTS):
            try:
                raw_text = self._client.send_prompt(
                    SYSTEM_PROMPT,
                    user_prompt,
                    max_tokens=_GENERATION_MAX_TOKENS,
                    counts_toward_limit=(counts_slot and attempt == 0),
                )
                payload = parse_json_payload(raw_text)
            except AIGenerationError as exc:
                last_error = exc
                # Our own fixed, key-free messages: safe to log.
                logger.warning("AI attempt %d failed: %s", attempt + 1, exc)
                continue
            if not isinstance(payload, list):
                last_error = AIGenerationError("The AI response was not a list.")
                continue
            parsed = [
                r for r in (_parse_question_record(item) for item in payload) if r is not None
            ]
            if parsed:
                return parsed
            last_error = AIGenerationError("The AI returned no usable questions.")
        raise last_error or AIGenerationError("The AI returned no usable questions.")

    # -- stage 2+3: deterministic filters and structural validation ---------------------

    def _filter_candidates(
        self, dataset: ProfileDataset, records: list[_AIQuestionRecord]
    ) -> list[QuestionCandidate]:
        ages = _known_ages(dataset)
        accepted: list[QuestionCandidate] = []
        for record in records:
            candidate = _candidate_from_record(record, dataset)
            surfaces = (candidate.text, record.explanation, *record.options)
            if _mentions_exact_age(surfaces, ages):
                logger.info("AI candidate rejected: exact_age")
                continue
            if _argues_from_absence(candidate.text):
                logger.info("AI candidate rejected: absence_claim")
                continue
            if _is_trivia(candidate.text, record.explanation):
                logger.info("AI candidate rejected: trivia_pattern")
                continue
            reason = self._validator.rejection_reason(candidate, dataset)
            if reason is not None:
                logger.info("AI candidate rejected: %s", reason)
                continue
            accepted.append(candidate)
        return accepted

    # -- stage 4: independent verification (fails closed) ------------------------------

    def _verify(
        self, dataset: ProfileDataset, candidates: list[QuestionCandidate]
    ) -> list[QuestionCandidate]:
        try:
            raw_text = self._client.send_prompt(
                VERIFY_SYSTEM_PROMPT,
                _build_verify_prompt(dataset, candidates),
                max_tokens=_VERIFICATION_MAX_TOKENS,
                counts_toward_limit=False,
            )
            payload = parse_json_payload(raw_text)
        except AIGenerationError:
            # Never ship unverified questions: the caller falls back to the
            # algorithmic engine.
            raise AIGenerationError("The AI questions could not be verified.") from None
        if not isinstance(payload, list):
            raise AIGenerationError("The AI questions could not be verified.")

        correct: set[int] = set()
        for item in payload:
            if not isinstance(item, dict):
                continue
            index, verdict = item.get("index"), item.get("verdict")
            if (
                isinstance(index, int)
                and not isinstance(index, bool)
                and 0 <= index < len(candidates)
                and isinstance(verdict, str)
                and verdict.strip().lower() == "correct"
            ):
                correct.add(index)
        verified = [c for i, c in enumerate(candidates) if i in correct]
        logger.info("AI verification kept %d of %d questions", len(verified), len(candidates))
        if not verified:
            raise AIGenerationError("None of the AI questions passed verification.")
        return verified
