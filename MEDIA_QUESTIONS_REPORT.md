# Media questions: diagnosis and verification

Focused revision from `4de891d` on `codex/group-intelligence`. Only backend question generation, selection, wording, fixtures, diagnostics and documentation changed. No knowledge-asset expansion, frontend change, dependency change, deployment or push. The pre-existing `frontend/package-lock.json` metadata diff remains untouched.

## Root cause

This diagnosis used the current category-first production engine, not the older `group_rules.py` implementations. `QuestionGenerator.trace()` exposes generated, validated, scored, selected and final public questions.

1. **Selection conflated three independent inputs.** Artist genre, song genre and the music-style dropdown all used the `music` domain. They shared domain/family caps and usage penalties, so an artist majority could exclude a song majority. Movies had their own domain, but family-first selection could still spend its opportunities elsewhere without selecting the supported movie leader.
2. **Optional answers faced a whole-room threshold.** A majority required five recognized answers and half the room participating. Four fully recognized artist/song choices could not generate a leader even when their winner was unique. Those choices can support a claim about the choices shared, without establishing the taste of the whole room.
3. **Missing media opportunities.** Diversity excluded all three media dimensions; artist/song inputs were absent from subgroup rules. Named-genre uniqueness existed, but the generic “who chose a genre nobody else chose?” required a new proof of uniqueness across all genres.
4. **A latent generation-order bias.** Each discovery family retained only its first 60 candidates. Earlier dimensions could consume the budget before artist/song candidates were visited. A constrained-budget regression reproduces this starvation independently of selection.

In the realistic 10-player fixture, the original engine generated and validated all three genre-majority candidates. Only the artist majority survived into the final quiz:

| Source | Before: raw majority | Before: valid majority | Before: selected majority | After: selected majority |
|---|---:|---:|---:|---:|
| Movies | 1 | 1 | 0 | 1 |
| Artists | 1 | 1 | 1 | 1 |
| Songs | 1 | 1 | 0 | 1 |

Before: movies supplied one semantic comparison, artists two semantic questions, and songs **zero semantic questions** (a literal song count was selected instead). After: all three leaders appear, plus an artist-genre count, a song-genre outlier and two media subgroup questions. Both versions return 20 questions. Four-player rooms and a 10-player room where only four people shared artist/song choices also now select all three media leaders.

## What changed

- Separate movie, artist, song and music-style selection budgets, while retaining shared factual music classifications and the existing overall question mix.
- Give each supported media source its first semantic discovery before repeating other sources. Prefer a valid leader, then comparison or outlier; no candidate means no reserved question. Normal deduplication, capacity, person caps and settled-answer rejection remain active.
- Interleave bounded candidate scopes instead of truncating a family by generation order.
- Permit media-choice leaders from three recognized choices at 80% coverage, with a decisive lead larger than the unknown count. Wording refers to chosen works/artists rather than claiming a majority of the entire room. Existing non-media whole-room thresholds are unchanged.
- Enable 2–6-genre diversity for all three media dimensions. Each represented genre counts once; a work may belong to several genres. Generic outlier/diversity require unique work identities too: shared genres of ambiguous title matches cannot establish a complete inventory or prove other genres absent.
- Add `group_genre_outlier`: every shared choice must be recognized and exactly one person may have any exclusive genre. Multiple exclusive genres belonging to that same person are fine; different outlier people reject the candidate. Named-genre uniqueness and membership deduplication remain.
- Add artist/hobby and artist/movie subgroup patterns, plus movie/song patterns in both directions. These compare actual, independently consented inputs; they never infer a song from an artist or a playlist from a preferred genre. An unknown media subgroup condition cannot silently exclude a possible member.
- Make counts explicitly count people’s choices, so two people selecting the same film count twice. Incomplete recognition uses “among the choices we recognized,” rather than presenting a partial count as exact for all choices.
- Keep questions tied to movies/artists/songs and add concrete chosen titles/artists to majority explanations. Improve Hebrew song-style agreement, such as “בסגנון אלקטרוני”.

The production families now cover media majority, comparison, named uniqueness, generic genre outlier, count, diversity and relevant subgroup reasoning. No release-year, franchise, artist-biography or other entity-trivia rule was added.

## Actual final Hebrew questions

These are selected public questions from [the audit artifact](scripts/knowledge/media-question-audit.json), not hand-authored candidate-only examples.

**Artists:**

איזה ז׳אנר מוזיקה הכי נפוץ בין האמנים האהובים שבחרתם?

Answer: **מזרחית**. Six participants chose Mizrahi-classified artists; four choices have pop membership. Evidence includes Omer Adam, Eyal Golan and Sarit Hadad. Participants entered artist names, not these classifications.

**Songs:**

אם מסתכלים על השירים האהובים עליכם, איזה סגנון מוביל?

Answer: **פופ**. Six choices have pop membership, versus five with rock membership. Repeated song selections count as separate participant choices; genres come from the songs’ own facts.

**Movies:**

איזה ז׳אנר חוזר הכי הרבה בסרטים שבחרתם?

Answer: **אימה**. Five participant choices are Saw/The Conjuring; no other genre has as many holders.

**Unique movie-genre outlier:**

מי בחר סרט מז׳אנר שאף אחד אחר בקבוצה לא בחר?

Answer: **יעל**, who chose Tron: Ares. The other five choices are Saw/The Conjuring. Science fiction belongs to just one participant; horror/crime/thriller have multiple holders.

**Subgroup:**

מבין מי שבחרו אמנים שמזוהים עם מוזיקה מזרחית, איזה ז׳אנר הכי נפוץ בסרטים שבחרו?

Answer: **אימה**. The subgroup is derived from actual artist choices; the target comes independently from those participants’ movie choices.

The four published fixtures produce eight complete 20-question games across Hebrew/English. The artifact includes every synthetic profile, final question, option, answer, explanation and pipeline count. Additional tests cover comparison without an overall winner, diversity in consent-limited shorter games, and outliers in each media domain.

## Verification

| Command | Result |
|---|---|
| `.venv/bin/python -m pytest backend/tests/unit/test_media_questions.py -q` | 49 media regressions passed; all are also included in the final full-suite run. |
| `.venv/bin/python -m pytest backend/tests -q` | **1,186 passed, 2 skipped**, 18.77 s. The skips require an explicitly configured disposable `MIZEMI_TEST_POSTGRES_URL`; one existing Starlette/httpx deprecation warning remains. |
| `.venv/bin/python scripts/diagnose_media_questions.py --label media-improved --benchmark --output scripts/knowledge/media-question-audit.json` | Eight complete final quizzes; 20 fresh 30-player generations: **18.770 ms median, 22.656 ms maximum** for 20 questions, after the reference bundle is loaded. |
| `.venv/bin/python scripts/check_secrets.py` | No high-confidence secret findings or real local env files. |
| `git diff --check` | Passed. |

Tests assert final `Question[]` answers and domain coverage across three seeds and both languages, not just candidate existence. They also cover hidden-value mutation invariance, too few shared answers, all-unknown inputs, ambiguous titles, ties, a single unknown that could tie the winner, exclusive-genre ambiguity, repeated-title counts, meaningful subgroups, limited candidate budgets, no settled-question repetitions, no technical Hebrew wording, and bounded 30-player generation with filesystem/network access forbidden. Historical engine, integration, auth, reconnect, scoring and persistence tests remain in the full suite.

No frontend tests or deployment checks were rerun for this backend-only revision. The two optional live-PostgreSQL tests were not claimed as passed.

## Reproducing the original comparison

The current fixture definitions can run against an exported earlier backend without changing the working checkout:

```sh
mkdir -p /tmp/mizemi-media-before
git archive 4de891d backend | tar -x -C /tmp/mizemi-media-before
.venv/bin/python scripts/diagnose_media_questions.py \
  --backend /tmp/mizemi-media-before/backend --label 4de891d \
  --output /tmp/mizemi-media-before.json
.venv/bin/python scripts/diagnose_media_questions.py \
  --label media-improved --benchmark --output /tmp/mizemi-media-after.json
```

The benchmark is a local development-machine measurement, not a deployed-host claim. Question content and selection are deterministic for a fixed engine, dataset and seed; timings naturally vary.

## Limits retained deliberately

A real tie remains a tie. For example, choosing only artists classified as both pop and Mizrahi does not justify inventing a Mizrahi winner. Missing or overly broad classifications can still reduce questions; the reference dataset and resolution policy are unchanged. A short quiz cannot guarantee every family in every domain, and one already-disclosed fact never earns a repeated question just to fill a quota. Low-data or consent-limited rooms may return fewer questions. No push or deployment was performed.
