# MiZeMi — MASTER SPECIFICATION

**Status:** Classroom enhancement, v3.0, 2026-09-11. The completion mission explicitly authorized finalizing the previously deferred MVP decisions. This revision records the behavior on disk and supersedes the earlier proposed baseline. Architecture, no-runtime-AI, consent and zero-cost constraints remain binding.

## 0. Decision Status and Deferred Decisions

The MVP decisions in this revision are finalized: separate token-authenticated host/player roles, profile schema, one accepted answer, deadlines, scoring, ties, room capacity, reconnects, retention, database initialization, browser E2E and deployment configuration. Only active-game recovery after restart, horizontal scaling, profile editing after submission, and future schema migrations remain outside this release. These are limitations, not partially implemented features.

## 1. Product Purpose

MiZeMi is a live multiplayer classroom icebreaker. A host shares a room code; players submit social profiles with per-field consent. The server generates multiple-choice questions from shared facts, accepts answers, scores rounds and displays a final winner/leaderboard.

**No AI at runtime:** no AI SDK, model, LLM API or network generation call exists in the application. Questions come from deterministic Python rules.

**Zero cost:** only free/open-source dependencies and independently sufficient free hosting/database tiers. No paid API, paid realtime provider, payment-gated trial or required upgrade.

## 2. MVP Scope

Room creation and joining; profiles and consent; readiness; host start; timed questions; answers and private acknowledgements; results and anonymous statistics; scores; leaderboard; host progression; final results. Mobile players and projector/laptop host. Session restore and network reconnect while the backend process survives. Finished records in SQLite locally or PostgreSQL in production.

No user accounts, cross-game identity, persistent public history, horizontal scaling, or automatic recovery of interrupted games after server restart. Hosts do not answer as players.

## 3. Future Enhancements

Profile editing, durable active-game recovery and versioned migration tooling can be added when specifically scoped. They must preserve the consent boundary and zero-cost/no-AI constraints.

## 4. Technology Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.12+, FastAPI, Pydantic v2, native WebSockets |
| Domain | Framework-independent object-oriented Python |
| Persistence | SQLAlchemy 2.x, SQLite locally, psycopg 3 / PostgreSQL for Neon |
| Frontend | React 19, strict TypeScript, Vite, native browser WebSocket |
| Tests | pytest, Vitest, React Testing Library, Playwright Chromium |
| Hosting target | Single Render Free Python web service, free static site, Neon Free PostgreSQL |

Do not replace this with Firebase, Supabase Realtime, Socket.IO, Pusher, Ably, Redis, brokers, microservices or runtime AI. Runtime and development dependencies are separate in backend requirements files; frontend dependencies are locked.

## 5. Architecture: Modular Monolith

The backend is one process. Presentation (`api/`, `realtime/`) validates traffic, coordinates connections and serializes application outcomes. Application services orchestrate domain operations and expose persistence interfaces. Domain owns pure game rules, question generation, scoring and statistics. Infrastructure implements settings, credentials, repositories and SQLAlchemy storage. The composition root is `app/main.py`.

Domain imports no FastAPI, SQLAlchemy, Pydantic or IO. Clients render server state and send intents; they never author scores, identities, timestamps, deadlines or correct answers. Database work is off the event loop. Do not add parallel workers: live rooms and token digests are process-local.

## 6. Folder Structure

- `backend/app/api/`: REST schemas/routes and HTTP guards.
- `backend/app/realtime/`: envelope, authentication transport, connections, per-room GameHub and ordered events.
- `backend/app/application/`: use cases, profile validation, gameplay services and repository records/interfaces.
- `backend/app/domain/{game,questions,scoring,statistics}/`: pure domain behavior.
- `backend/app/infrastructure/{database,repositories}/`: schema, sessions, mapping and persistence; settings/credentials/room registry are infrastructure modules.
- `backend/app/main.py` and `__main__.py`: app factory and one-worker process entrypoint.
- `backend/tests/{unit,integration,fixtures}/`, `backend/tests/smoke_classroom.py`.
- `frontend/src/{api,realtime,components,features/host,features/player,hooks,state,types}/`: transport, views and server-derived state/session storage.
- `frontend/e2e/`: real browser scenarios.
- `scripts/`: local verification helpers; `.github/workflows/`: CI.
- `render.yaml`, `DEPLOYMENT.md`, `README.md`, `.env.example` files: deployment/local operation.

Reuse existing modules before adding new ones. New application layers or top-level feature modules require an intentional spec change.

## 7. Module Responsibilities and Team Ownership

Backend/platform owns transport, settings, credentials and persistence. Gameplay owns game/state/scoring. Question Engine owns dataset, rules, validation and selection. Frontend owns views and TypeScript mirrors. Changes across these boundaries must update both contracts and tests. A completion task may span all these roles when explicitly authorized.

## 8. Shared Domain Concepts

**Room** owns one Game and a six-character code from `ABCDEFGHJKMNPQRSTUVWXYZ23456789`. Lookups trim and uppercase; collisions among active rooms regenerate. **Host** is the room creator with its own bearer credential, never a Player. **Player** is an ephemeral game participant. Public identifiers are opaque server-issued strings; clients never infer meaning from them.

**Game** owns state, players in join order, profiles, questions, accepted answers, last round result and scores. **QuestionCandidate** is private engine data. **RoundResult** is an internal immutable result of closing one question, not a public independently managed round resource. **Answer** records the selected option and server receipt time. **Leaderboard** and **Statistics** are server-derived views.

Credentials contain 256 bits of randomness. Only SHA-256 digests are retained server-side, verified with constant-time comparison. Plaintext tokens are returned once to the creating/joining client and kept in per-tab `sessionStorage`; they are never broadcast, logged or saved to the database. Closing a tab loses that seat's credential. Removing a player revokes its token.

## 9. Shared Contracts

Wire keys are snake_case; TypeScript mirrors are in `frontend/src/types/`, Pydantic definitions in `backend/app/api/schemas.py`. No raw domain object is serialized to clients.

### 9.0 Game configuration and languages

The host sets immutable `Game.config = {question_count, language}` at creation. Count is a strict integer 1–50, default **20**; booleans, strings, floats, null, out-of-range values and unknown keys are rejected. Language is exactly `en` (default) or `he`. Missing request/body fields retain defaults; a deployment may explicitly override the no-body count with MIZEMI_QUESTIONS_PER_GAME (default 20). The public response and all room snapshots include this configuration. Requested count remains intact when quality gates yield fewer questions; `total_questions` reports the actual generated count after start and the requested count in the lobby. The UI explicitly explains shortfalls.

Each browser stores its UI locale in localStorage (`mizemi.language`), independently of per-tab credentials. A persistent selector sets document lang/dir (English LTR, Hebrew RTL). Game language is separately selected by the host, defaults to their UI language, and never changes during play. Questions/options use deterministic bilingual templates on the server, with `language` and `difficulty` in started/ended payloads; clients render that shared text unchanged using its own direction. Player-entered names/values are never translated. Music choices have localized UI labels but stable existing wire values. Errors are localized by stable public error code; backend diagnostic messages remain safe English for older clients.

### 9.1 Player contract

```json
{"player_id":"opaque-id","display_name":"Dana","is_host":false,"connected":true,"has_profile":true,"is_ready":false,"score":0}
```

Display names are trimmed, 1–20 characters, and unique per room under case-folding. New players have no profile, are unready/disconnected and score zero. `is_host` is always false. Scores are stored on Game and mapped into the public player snapshot.

### 9.2 PlayerProfile contract

Submission is exactly `{player_id, fields}`, where each field is `{field_key, value, allow_question_usage}`. Values are strictly strings or integers (not booleans); consent is a strict boolean. Up to nine fields; unknown/duplicate keys and missing required fields are rejected.

| Key | Type / constraints | Required | Initial UI consent |
|---|---|---|---|
| city | Text, 1–40 characters | Yes | Checked |
| favorite_food | Text, 1–40 | Yes | Checked |
| hobby | Text, 1–40 | Yes | Checked |
| favorite_music | Listed choice | Yes | Checked |
| age | Integer, 5–120 | No | Checked |
| favorite_movie | Text, 1–60 | No | Checked |
| favorite_artist | Text, 1–60 | No | Checked |
| favorite_song | Text, 1–60 | No | Checked |
| personal_fact | Text, 1–120 | No | **Unchecked** |

Music choices: Pop, Rock, Hip-Hop / Rap, Electronic, Mizrahi, Classical, Jazz, Metal, Mediterranean, Israeli Pop, House, Techno, Trance, Indie, R&B, Reggae, Folk, Country, Blues, Other. Text is trimmed and whitespace collapsed. Contact-like emails, URLs and runs of seven or more digits are rejected. This heuristic does not claim to detect all sensitive content; the UI explicitly asks players not to enter private details. Use nicknames and light facts for class.

Consent may be withheld for **every** field, including required fields. Empty optional inputs are omitted. Profile submission is initial-only, through `player.profile_submit`; the connection identity must match `player_id`. No public profile-read endpoint and no post-submission editor exist.

### 9.3 Question format

```json
{"question_id":"opaque-id","index":0,"total_questions":20,"question_type":"multiple_choice","text":"Question text","options":[{"option_id":"a","text":"Answer A"},{"option_id":"b","text":"Answer B"}],"difficulty":"EASY","language":"en","time_limit_seconds":20,"started_at":"2026-09-11T08:00:00.000Z"}
```

`index` is zero-based. The production rules generate 2–4 distinct options with exactly one correct option. Option ids are opaque. Default question count is 20 (host-configurable 1–50); default timeout is 20 seconds (1–300). The engine returns fewer questions if fewer valid candidates exist, and rejects starting with none. It never invents non-consented facts to fill a quota.

`correct_option_id` stays server-private until the corresponding question ends. `started_at` is stamped by the server when the question opens, not during generation. Future questions and their answers are never sent early.

### 9.4 Answer submission format

Exactly `{question_id, option_id}`. Each is a nonempty opaque string up to 64 characters. Player identity comes from the authenticated socket. Server receipt time is authoritative; the envelope's client timestamp is never used for scoring. One accepted answer per player/question across all that player's sockets. No changes/resubmissions. Invalid options, wrong question, unknown player and late/duplicate answers are rejected without mutation.

Answers received at the exact deadline are accepted; those after it are rejected. The timer closes the question about 250 ms after the deadline to serialize with receipt handling; that scheduling grace does **not** extend answer acceptance. All answers can close the question sooner. The final answer and timer share the room lock and score exactly once.

### 9.5 Score format

`{player_id, total_score}`. Preserved Phase 1 scoring formula:

- Wrong or no answer: 0.
- Correct: `500 + floor(500 * remaining_ms / limit_ms)`.
- Elapsed time is floored to whole milliseconds; remaining time is clamped to `[0, limit_ms]`.
- Correct answers earn 500–1,000 points. Cumulative scores are applied only on close.

A player's private round result is `{option_id: string|null, is_correct: boolean, points_awarded: number, total_score: number}`. Non-answer: null option, false, zero points. The host receives null for this entire object.

### 9.6 Statistics format

`{question_id, correct_option_id, answer_distribution, answered_count, player_count}`. Each distribution entry is `{option_id, count, percentage}`. Percentages use accepted answers as denominator, rounded to one decimal; all are zero when no one answered. Rounding can make the sum slightly different from 100.

Only aggregate distributions are shared. During QUESTION_ACTIVE, `statistics.updated` is counts-only: `{question_id, answered_count, player_count}`. No answer choice, distribution, correctness or points leak through this event.

### 9.7 Leaderboard format

`{entries: [{rank, player_id, display_name, total_score}]}`. Descending score; equal scores share competition ranks (1,1,3) and retain original join order. Every rank-1 player is a co-winner. No random tie reorder.

## 10. Privacy Rules and Data Minimization

Non-consented fields are absent from ProfileDataset and invisible to rules, including suppression of candidates. Questions describe **shared facts**, not an exhaustive real-world census of the class. Personal facts start opted out. Display names remain public.

No phone/email/address/ID/password/account requirement. No profile values in URLs or logs. No other player's raw profile or individual answer in a client payload. A consenting fact may appear in generated question text/options. Scores, display names and connection/readiness status are public to the room.

Default database retention: seven days from the last database save, with entire expired FINISHED game trees removed (including generated questions containing facts). Cleanup runs at startup and every five minutes while running, at most 100 expired games per transaction; outages/backlogs can delay deletion. The same transaction removes up to 500 legacy raw-profile rows from FINISHED games regardless of age, without changing their retention clock or touching active records. Shutdown waits for maintenance and persistence workers before engine disposal. Rooms with no connections are removed after 120 idle minutes. Credentials expire with their room. Connected rooms remain in memory while their process lives.

## 11. Game State Machine

```text
LOBBY → PROFILE_COLLECTION → READY
READY --new player joins--> PROFILE_COLLECTION
READY --game.start--> QUESTION_ACTIVE
QUESTION_ACTIVE --all answers or timeout--> QUESTION_RESULTS
QUESTION_RESULTS --game.next--> LEADERBOARD
LEADERBOARD --game.next, more questions--> QUESTION_ACTIVE
LEADERBOARD --game.next, no questions left--> FINISHED
```

First valid profile automatically enters PROFILE_COLLECTION. All current players must have submitted profiles and marked ready; disconnected players still count. Joins are allowed in LOBBY/PROFILE_COLLECTION/READY until the host starts. A new arrival in READY returns the game to PROFILE_COLLECTION; earlier players keep their profiles/readiness. This fixes early students accidentally preventing the rest of the class from joining. Host removal is allowed before play in LOBBY/PROFILE_COLLECTION/READY. Readiness after removal is recalculated where applicable. An empty READY room cannot start; a new join reopens profile collection.

Only a verified host starts or advances. Generation occurs at host start from READY. State changes produce authoritative `room.updated` then relevant stage data. Illegal transitions leave the state unchanged. FINISHED is terminal.

## 12. Question Generation Engine

Pure pipeline: `ProfileDataset → QuestionRule[] → QuestionValidator → QuestionQualityScorer → QuestionSelector → Question[]`. Seed is a stable SHA-256-derived integer from game id; identical dataset/config/seed yields identical questions. Randomness is local seeded Python Random, never global or an external service.

The historical catalog contains 29 direct/profile rules, 18 v4 semantic rules and the v5 group families. The current production composition (§12.3, §12.6) uses **5 simple direct families and 30 category-first discovery families** (16 semantic, 8 geographic, 5 cross-domain, 1 social). The other historical algorithms remain available to pure callers and regression tests, but the deployed composition does not select them.

Difficulty is explicit EASY/MEDIUM/HARD metadata on candidates and final questions. Legacy selection targets 25% easy, 45% medium and 30% hard. The current group-first selector plans the mix in §12.3, uses these difficulty bands as a secondary preference, then orders selected questions EASY → MEDIUM → HARD. Data availability determines the actual difficulty proportions. Within each band a greedy selector balances rule, field and subject diversity and recent-use penalties. When those signals tie, demonstrated semantic reasoning depth takes precedence over basic lookup, then coverage and stable text order apply; scoring of player answers is unchanged. It suppresses normalized text duplicates and semantic signatures across equivalent families; it does not fabricate or repeat questions to fill a quota.

Comparison normalization is Unicode NFC, collapsed whitespace and casefold; displayed user text keeps its original spelling. Fixed bilingual field labels/templates are selected from an allowlist, never dynamic paths. Similarity counts equal shared values once per field among city, favorite food, hobby, music and movie; age and personal facts are excluded. Similarity families require at least two preference fields shared by every compared participant and use that same field set, explicitly named in the question. Ties are rejected. Inequality/exclusion/age rules require consented data for every field actually tested; missing values are never treated as a different value. Minimal fingerprints require every smaller clue subset to remain ambiguous.

Rules operate only on ProfileDataset, cache consent-safe indexes and pair overlap counts, cap candidate output and bound combination work. Distractors are real participants/pairs/categories or bounded neighboring integers. Every candidate passes structural/length/option/metadata validation; each family owns and tests its mathematical uniqueness gate. No eval, dynamic template execution, AI or network IO exists in generation.

### 12.1 Offline knowledge extension (v4, explicitly authorized)

Reference knowledge lives in compact version-controlled assets under `backend/app/data/knowledge/`, not in Neon. Development-only scripts may retrieve licensed public facts; deployment and generation never fetch reference sources. An infrastructure loader validates the entire bundle and its provenance/schema before constructing immutable domain knowledge and alias indexes. The composition root injects this knowledge into the pure Question Engine; rules never open files, query databases or make network calls. Unknown and ambiguous aliases supply no semantic facts, while existing direct rules retain the original consented answer.

Only player-consented facts, deterministic mathematics and trusted local classifications may determine an answer. Preferences never imply playlists, personality, demographics or behavior. Multi-label classifications are not exclusive identities; absent or incomplete classification must not become a negative fact. Group claims follow the coverage policy in §12.3; unknown answers are never counted as non-membership and private participants never appear in counts, denominators or options. Geographic questions compare locality representative coordinates and straight-line distances, never home locations or travel times, and reject close/tied results within documented precision margins (1 km for distances; 0.01° for latitude).

Semantic candidates carry a concise localized `explanation` and a private knowledge version. `question.ended` adds `explanation` (empty for legacy questions); it is NEVER included in active events because it can reveal the answer. Reconnect during QUESTION_RESULTS repeats the explanation. LEADERBOARD and FINISHED retain their existing stage-specific replay, without sending unnecessary historical question data. Finished records preserve it in an additive cascading `question_explanations` table, so no existing column migration is needed. Public reference attribution is available in the UI; source manifests document licenses, retrieval dates and transformations. Scoring, envelopes, host authorization and game configuration remain unchanged.

The music dropdown retains existing wire choices and adds the supported styles Mediterranean, Israeli Pop, House, Techno, Trance, Indie, R&B, Reggae, Folk, Country and Blues. These remain explicit player selections. In v5, artist/song metadata supports group counts and patterns only when players actually select artists/songs; the former genre-to-artist trivia bridge is disabled. Human question templates in both languages describe movies, food, hobbies and places without database/field/value terminology.

`KNOWLEDGE_BASE_REPORT.md` records actual coverage, sources, all new rules, demonstrations, benchmarks, limitations and final verification. Dataset refresh is deliberate development work with validation/review; production uses the committed version unchanged.

### 12.2 Group intelligence revision (v5)

MiZeMi is a social group-discovery game. Production questions use knowledge to understand consented answers, then compare the group. Entity trivia, artist guessing, person-to-person similarity puzzles and opaque profile fingerprints are disabled in the production composition. Historical rule implementations remain available for regression/replay compatibility. Direct identification is a limited EASY fallback.

Selection (superseded in detail by §12.3) balances simple, semantic, geographic and cross-domain questions, redistributing when suitable candidates are unavailable. It caps direct identifications, repeated pairs, repeated families and person-answer questions; equivalent membership facts are not asked once as a count and again as a unique-person clue. The selected questions progress from EASY through MEDIUM to HARD. Reasoning creates difficulty; the wording stays conversational.

Canonical artists and songs are resolvable independently of music genres. Optional `favorite_artist` and `favorite_song` text fields (1–60 characters) each retain their own consent flag and existing contact-detail filtering. Empty optional answers are omitted. The seven previous wire fields and music choices stay valid; the submission envelope allows at most nine fields. A song's genre comes from the song's own supported facts, never its performer's usual genre. Style choices never prove a playlist.

The expanded bundle uses schema 2, adds songs and optional compact release/country/series/performer/locality-type details, and remains version-controlled backend data. Those details support resolution/provenance; no per-entity trivia rule consumes them. Lookup uses cached in-memory indexes and shared classification sets. Targets: assets ≤20 MB (review at 30 MB), retained knowledge memory ≤60 MB (review at 80 MB), uninstrumented load ≤1 second (acceptable ≤2), 30-player/20-question generation ≤200 ms (review at 500).

Broad regions are an explicitly documented grouping of districts: Northern+Haifa, Central+Tel Aviv, Southern, and Jerusalem separately. Unknown regions stay unknown. Region plurality wording says “most”; “majority” requires strictly more than half. Geographic outlier means the greatest average great-circle distance to every other participant's locality reference point, with a 1 km margin over the runner-up. Closest/farthest pairs reject equal/near ties and same-town answers. No score tie-break creates a supposedly unique question answer.

Activity families describe activities, never people’s personalities. Indoor/outdoor classifications refer to supported conventional activity settings; explicitly flexible activities belong to neither side of the two-way comparison. Questions/explanations do not claim where anyone actually practises the hobby. Derived fields inherit their source's consent absolutely. Group claims follow the coverage policy in §12.3. Unknown is never a negative membership.

Legacy literal group rules reject fields containing different recognized aliases for the same entity. This prevents alternate spellings from becoming false separate favorites. Semantic diversity questions are limited to 2–6 represented families. Selection caps person-answer questions at five in a 20-question game and suppresses repeated count/unique discoveries about the same source field and membership set.

The updated KNOWLEDGE_BASE_REPORT.md and committed sample-game audit record measured coverage, source/alias ambiguity, actual performance, the production registry, and GOOD/ACCEPTABLE/BAD wording reviews. No Render/Neon changes, deployment, external accounts, credentials or push are part of this revision.

### 12.3 Category-first discovery (v6)

Diagnosis (QUESTION_ENGINE_DIAGNOSTIC.md): v5 group families required every player's answer in a dimension to be recognized, so realistic 20-person rooms lost almost all of them and games fell back to literal lookups — or ended early. v6 replaces that all-or-nothing gate with a category-first stage and a coverage policy.

**Stage.** Before any question is considered, `group_summary.py` classifies each consented answer, once per generation, into the comparable categories of each semantic dimension: film genre; cuisine family; broad hobby family, physical activity and outdoor/indoor setting; music family for the chosen style, artist and song; region. Each answer is *classified*, *neutral* (recognized but in no compared category — a flexible-setting hobby, the "Other" music choice) or *unknown*. Withheld answers are absent: they change no count, denominator or wording. Categories are compared at one taxonomy level per dimension (running's fitness label folds into sport; Japanese/Chinese/Thai/Korean/Indian dishes are Asian food and hummus is Middle Eastern; trance is electronic). Films classified into more than five genres, and dishes in more than two cuisine families, are too broad to count. A name shared by several reference entities keeps identity unknown but contributes the categories all of them share; a Hebrew doubled-vav/yod spelling fold applies only after the exact name misses. Explanations show what players typed.

**Families.** Seven semantic families (count, majority — with a named three-way "what characterizes the group" variant — comparison, unique member, diversity, minority, distribution), eight geographic families (region majority, comparison, count, unique member, diversity; northernmost/southernmost; closest pair; furthest from the group) and three cross-domain families (subgroup majority, subgroup comparison, intersection count) apply to every compatible dimension; only wording differs by domain. Literal facts about a listed music choice that no grouping changed are classified as direct. Direct questions keep five clear literal families; music choices and counts of one are excluded from them.

**Coverage and ambiguity.** Any group question needs three shared, recognized answers. Counts need 75% recognition and state the rate when below 100%. Comparisons need 70% and a lead larger than the number of unknown answers; ties are rejected, the smaller side needs two people once eight or more answered, neither side may have more than three times the other, and categories whose members mostly coincide (subset or ≥ half) are not compared; overlapping categories use "appears more" wording and explain the overlap. Majority, "most popular in the group", minority and distribution claims need 80% recognition, five recognized answers, at least half the room sharing, a leader with ≥ 20% of recognized answers and a lead larger than the unknown count; minority/distribution reject ties at their boundary. An explanation names a runner-up only when it leads third place by more than the unknown count. "Most of the group" requires more than half of the visible room. Exclusive claims (only one person, how many different categories, extremes) require every shared answer recognized; coordinate questions require every shared town uniquely identified and reject near ties (0.02° latitude, 2 km pair gap, 5 km average-distance gap). Cross-domain subgroups need at least max(3, 20% of the room) members and 80% target recognition inside them.

**Selection.** Candidates collapse to one per fact. Quotas prefer 45% semantic, 25% direct, 15% geographic and 15% cross-domain, capped by supply and redistributed; nothing is padded. Caps per N questions: family ⌈N/5⌉, domain ⌈N/4⌉ (a cross-domain question counts for both), one domain/family pair per 12 questions, supporting families once per 20, person answers ⌊N/4⌋, two literal lookups per rule, one age question; membership signatures prevent asking about the same people twice, including one intersection seen from either subgroup. No question may be settled by one shown before it: counts, rankings, subgroup facts and raw-answer counts/majorities/comparisons declare what they disclose and what would settle them, and the check follows the EASY → MEDIUM → HARD presentation (a majority excludes a later comparison involving its leader or named runner-up; a count of one excludes a later least-common question; a count holding half the shared answers excludes a later comparison with that category). Of two conflicting facts the one that settles the other is preferred when it reasons at least as deeply; a settled question is never admitted: when too few unsettled facts exist the game is shorter, and every question's `total_questions` is the actual length. Within a kind the least-used family and domain win, then difficulty spread, then information value (`DiscoveryValueScorer`: 0.4 reasoning depth, 0.3 group share, 0.2 result informativeness weighted by how clearly members' choices are classified, 0.1 recognition coverage). Caps relax only when nothing else fits. Questions are presented EASY → MEDIUM → HARD without back-to-back domains.

**Language and determinism.** Every template is an English/Hebrew pair; variants are chosen by a stable hash of the fact, so the same seed selects the same facts, answers and option order in both languages. No template uses storage or engine vocabulary. Generation stays pure, offline and seeded; questions are still generated once at start and replayed, persisted and scored exactly as before. Wire contracts, schema and scoring are unchanged.

### 12.4 Media discoveries (v6.1)

Movies, artists and songs retain their own selection domains. An artist and a song may share the music taxonomy, but neither competes for the music-style dropdown's single domain/family allowance. Within the semantic share, the selector first represents each supported media source with a genre discovery, preferring a decisive genre leader, then comparison/outlier/diversity over a simple count. This preference never bypasses validation, question capacity, person limits or the prohibition on questions already answered by earlier results. A source with no supported discovery receives no reserved slot. Family candidate limits interleave field scopes so earlier dimensions cannot exhaust the budget before artist/song candidates are seen.

Media leaders describe **the choices shared**, not the taste of every person in the room. They need at least three recognized, consented choices, 80% recognition and a meaningful lead that unknown choices cannot tie; they do not require five choices or half the room to answer an optional field. Other whole-group claims retain §12.3's thresholds. Media counts count participants' choices, including repeated titles/artists; when recognition is incomplete their wording explicitly limits the count to recognized choices. Genre diversity includes movies, artists and songs, with complete recognition and 2–6 represented genres.

The generic media outlier asks who chose a work/artist representing a genre nobody else's choice represents. Every shared answer must be classified, and all singleton genres must belong to exactly one person; several singleton genres belonging to different people reject the question. Generic outlier and media diversity also require uniquely resolved works/artists: genres shared by ambiguous title matches cannot prove other genres absent. Named-genre unique questions remain available and share the same membership deduplication. Artist/hobby, artist/movie, song/movie and movie/song subgroup discoveries use actual independent submitted choices. Media subgroup conditions must be completely recognized; target-side unknowns must not be able to change the winner. A song's genre is never inferred from its artist.

No reference facts, resolution policy, wire contract, scoring, persistence or frontend behavior change in this revision. [MEDIA_QUESTIONS_REPORT.md](MEDIA_QUESTIONS_REPORT.md) records the measured before/after pipeline and final-quiz regressions; the reproducible fixture audit is `scripts/knowledge/media-question-audit.json`.

### 12.5 Conservative knowledge resolution (v6.2)

The seven knowledge domains share a staged, offline resolver. Full canonical names and reviewed aliases remain authoritative; Unicode NFKC, whitespace, case, punctuation/hyphens and Hebrew quotes/niqqud are normalized. A unique Hebrew full/defective spelling or word-final-letter variant may resolve after a full-name miss. Collisions reject identity, including canonical-versus-alias collisions.

Internal outcomes are EXACT, ALIAS, NORMALIZED, PARTIAL_HIGH_CONFIDENCE, FUZZY_HIGH_CONFIDENCE, AMBIGUOUS and UNKNOWN. Outcomes include a reason and, for fuzzy comparisons, best/runner-up scores. They are never public game payloads. Only accepted identities supply entity-specific facts. The existing exception for common positive categories of a **full-name** ambiguity remains: identity stays unknown, and no exclusive claim may treat that intersection as a complete classification. Ambiguous partial/fuzzy inputs supply no categories.

Partial matching is limited to movies, songs and artists: a unique English article-omission spelling, or at least two complete significant tokens in order with at least 80% significant-character coverage. Every plausible full-token contender participates in ambiguity rejection, including long titles and low-coverage contenders. Shortened franchises are never assigned to one film. Other domains require full-name normalization or a qualified typo match.

Fuzzy matches allow one insertion, deletion, substitution or adjacent transposition. Non-space input/reference minima are Latin 7 for media, 5 for foods and 6 otherwise; Hebrew 6 for songs and 5 otherwise. Scripts must agree. Similarity is `1 - edit_distance / min(max(name_length, input_length), 20)`, at least 0.82, with at least a 0.08 gap over the next distinct entity. The length cap ensures names outside the searched two-edit radius cannot silently violate the margin. Numbers and movie/song Roman tokens must remain identical. Approximate queries are capped at 64 characters; full names retain the existing 200-character bound. Candidate overflow rejects instead of truncating to a potentially wrong winner.

Reference names are indexed once by script, length and bigrams using packed integer postings and character masks. At most 256 narrowed names receive bounded edit-distance calculations per query; JSON parsing and full-catalog distance scans never occur during a game. A consent-only dataset caches classifications locally during generation; no player-query cache crosses room boundaries. Withheld fields never enter the resolver or affect categories, candidates, counts, distractors or explanations.

The group-first selector defers `unique_value` person lookups until no eligible non-lookup question remains, including under relaxed family/domain caps. At most one such EASY fallback is allowed, and that cap never relaxes. Useful literal group counts and comparisons remain distinct from these lookups. The no-settled-question rule remains absolute; games can be shorter than requested. See [KNOWLEDGE_RESOLUTION_REPORT.md](KNOWLEDGE_RESOLUTION_REPORT.md) and its frozen evaluation artifacts for before/after final-quiz evidence, limitations and resource measurements. No reference facts, dependencies, public contracts, scoring or deployment configuration change.

### 12.6 Question variety (v6.3)

A game must discover things about the group, not restate the profile form. Every candidate carries a
**semantic signature** `(operation, topic, fact…)` and an **idea key** `(idea class, idea topic)`
alongside the membership signature. `operation` is the reasoning act; `topic` is the subject as a
player experiences it, so artist and song genres collapse to one music topic, and mirror-image
shapes (most/least, agree/differ, the three “who else?” forms) share one idea class. A signature, an
idea, a scoped subgroup and a person's anchoring answer may each be used once per game. Raw question
text is never the duplicate test.

Music style, artist and song are one subject with one budget; film, place, food, hobby, age and
personal are the others. In a 20-question game no subject exceeds 30% of the requested count and
that ceiling never relaxes; a reasoning pattern is used once, may return only on a subject it has
not been applied to, and repeats only in a final relaxation. The strongest two facts per subject are
reserved before variety staging so headline discoveries survive. Direct answer lookups are capped at
10% with at most one raw identity lookup. Selection stays a bounded greedy fill with an explainable
deterministic ranking; there are no arbitrary bonuses and no random tie-breaking.

New families: attribution of a consented personal fact to its writer, taste twins, the most typical
member, where the group agrees or differs most, unanimity, everyone-except-one, the other person in
your category, a song by someone else's favourite artist, two films of one series, age spread, the
one person in both of two groups, and region counts and uniques. New derived dimensions: age bands
(12 and under, 13–15, 16–18, 19–24, 25–34, 35–49, 50+), food formats and music-making hobbies. **No
question or explanation reveals an exact age**, and individual age evidence is never listed.

Free-text personal facts are quoted, never interpreted: the only question they support asks who
wrote a fact, and only when its writer consented and did not withhold their name. No inference is
made from arbitrary text; where meaning cannot be derived the value stays unknown. Reference
"series" values that are studio catalogues or curated lists do not make two films a series: a
shared distinctive title word in one of the game languages is also required.

Targets for rooms with real data, per game: at least six distinct reasoning families, at least five
profile fields, no subject above 30%, no repeated signature, direct lookups at most 10%, and zero
questions answered by an earlier one. Quality still beats length — a short game is preferred to a
repeated idea. Evidence, before/after metrics and limitations:
[QUESTION_VARIETY_DESIGN.md](QUESTION_VARIETY_DESIGN.md) and
[QUESTION_VARIETY_REPORT.md](QUESTION_VARIETY_REPORT.md).

## 13. REST / API Conventions

Base `/api/v1`, JSON objects, snake_case, UTC ISO-8601 `Z`. Public endpoints:

| Method/path | Request | Success |
|---|---|---|
| GET `/health` | None | 200 health response |
| POST `/rooms` | Optional `{question_count: 20, language: "en"}` | 201 `{room_code, game_id, host_token, config}` |
| POST `/rooms/{room_code}/players` | `{display_name}` | 201 `{game_id, player, player_token}` |

The private credential belongs only to the response recipient. HTTP responses use no-store. Unknown room: 404; duplicate name, non-joinable room or full room: 409. Validation errors: 400/422. Oversized HTTP body: 413. Request bursts: 429. Global room cap reached: 503. Error bodies follow §17 without echoing untrusted input.

## 14. Realtime (WebSocket) Conventions

### 14.1 Endpoint

- Player: `/ws/rooms/{room_code}?player_id=...`, subprotocol list `["mizemi.player", player_token]`.
- Host: `/ws/rooms/{room_code}/host`, subprotocol list `["mizemi.host", host_token]`.

Only the role protocol is echoed on acceptance. Invalid room/identity/credential/origin is rejected before acceptance without an envelope. Browser Origin must match configured origins; non-browser clients still need valid tokens. No tokens in query parameters.

Up to four simultaneous sockets per identity. `connected` remains true while any player socket remains; only the last disconnect marks false. Answer acknowledgements go to all sockets for that player. New/reconnecting sockets first receive exactly one room snapshot, followed by: active question/counts/own accepted answer; self-contained question results; leaderboard; or final result, depending on state. Other participants receive the changed connection state.

Clients reconnect with bounded backoff and restore their per-tab session after refresh. They ignore messages from old socket instances/other games. They do not replay potentially stale host commands automatically. Pending profile/answer UI state is released on disconnect so the authoritative replay or an explicit retry can resolve it.

### 14.2 Event naming and payloads

| Client event | Role | Payload |
|---|---|---|
| player.join | Either | Resync request; identity is already bound |
| player.profile_submit | Player | §9.2 |
| player.ready | Player | Exactly `{}` |
| answer.submit | Player | §9.4 |
| game.start | Host | Exactly `{}` |
| game.next | Host | Exactly `{}` |
| player.remove | Host | `{player_id}` |

| Server event | Payload |
|---|---|
| room.updated | `{room_code, state, players: Player[], current_question_index: number|null, total_questions, config}` |
| game.started | `{total_questions}` |
| question.started | §9.3, no correct answer |
| answer.accepted | `{question_id, option_id}` to answerer's sockets only |
| statistics.updated | Active counts-only §9.6 |
| question.ended | `{question_id, text, options, difficulty, language, explanation, correct_option_id, statistics, player_result}` |
| leaderboard.updated | §9.7 |
| game.finished | `{leaderboard: Leaderboard, winners: LeaderboardEntry[]}` |
| error | §17 error object |

`question.ended.text`, `.options`, `.difficulty` and `.language` repeat the public content so a reconnect needs no earlier question event to render results. Correct answer, localized explanation (up to 1,200 characters; empty on direct/legacy questions) and statistics are only emitted after that question closes. `knowledge_version` remains private and is stored with the completed question. `player.joined` and `player.updated` remain registered for compatibility; complete room snapshots currently carry their information.

### 14.3 Message envelope

Both directions use **exactly**:

```json
{"event":"question.started","payload":{},"timestamp":"2026-09-11T08:00:00.000Z","game_id":"opaque-id"}
```

Server time is serialized in UTC with milliseconds and Z. Client timestamps must be timezone-aware but never determine game outcomes. Wrong game id, malformed JSON, binary frames, malformed payloads and unknown events receive safe errors (UNKNOWN_EVENT or VALIDATION_ERROR). Clients ignore unknown events. Extras are forbidden by the relevant schemas.

All room mutations and event enqueueing occur under one room lock. Each socket drains an independent FIFO queue. Limits: 16,384 text characters per app frame; 65,536 transport bytes; 120 incoming frames per socket per ten seconds; 256 queued outbound messages, five-second send timeout. Slow/flooding clients close and can reconnect; they do not block the class. HTTP limits are 16 KiB body, 240 POSTs per IP/minute, 100 active rooms and default 50 players per room. IP limits allow classroom NAT sharing and are not an enterprise DDoS system.

## 15. Persistence Conventions

SQLAlchemy declarative models and repository interfaces. ORM/bound statements only; no input-interpolated SQL. Every row has UTC created/updated timestamps. Sessions own transactions; commit explicitly, roll back on failure/close. SQL error parameter printing is disabled.

One finished game stores player names/IDs/status, generated questions/options/explanations, accepted answers with server times, and final scores. New snapshots never store raw profile fields or per-field consent rows. The FINISHED transition clears raw in-memory profile values, retaining an empty profile marker for reconnect/status compatibility; generated game content can still contain consented facts. The original seven tables are `games`, `players`, `profile_fields`, `game_questions`, `question_options`, `answers`, `scores`. Answers/scores are additive tables, so old retained games have empty answers/scores. Writes occur off-loop at FINISHED; shutdown waits for submitted writes before disposing the engine. Persistence failure emits a safe log message, without credentials/query parameters; no durable retry queue exists.

Active rooms, token digests and active games are memory-only; process restart invalidates their credentials and loses unfinished games. Finished records are internal read-only repository records, not rehydrated active rooms. Whole-tree upserts, rollback and retention cascades work on SQLite and PostgreSQL.

**Initial schema strategy:** `Base.metadata.create_all` before startup becomes healthy, on local or production databases. It creates missing tables only; no automatic column alteration. A fresh Neon project needs no manual SQL. The enhancements add `game_configurations`, `question_details` and `question_explanations` as separate cascading tables, retaining compatibility with existing databases without altering old columns. Old retained records without details read as English/EASY and retain their recorded actual length. New records preserve the requested config, difficulty/rule metadata, explanation and knowledge version. There are ten application tables; reference entities and indexes are not stored in SQL. Add versioned migrations before future existing-table changes. See DEPLOYMENT.md.

## 16. Environment Variable Conventions

Frozen typed Pydantic settings loaded once, optional backend `.env`, real env files ignored by Git. Prefixed names win when both aliases exist.

| Preferred alias / existing name | Default |
|---|---|
| APP_ENV / MIZEMI_ENV | development |
| DATABASE_URL / MIZEMI_DATABASE_URL | sqlite:///./mizemi.db |
| HOST / MIZEMI_HOST | 127.0.0.1 |
| PORT / MIZEMI_PORT | 8000 |
| FRONTEND_ORIGIN / MIZEMI_CORS_ORIGINS | http://localhost:5173,http://127.0.0.1:5173 |
| MIZEMI_LOG_LEVEL | INFO |
| MIZEMI_QUESTIONS_PER_GAME | 20 |
| MIZEMI_QUESTION_TIME_LIMIT_SECONDS | 20 |
| MIZEMI_MAX_PLAYERS_PER_ROOM | 50 |
| MIZEMI_ROOM_IDLE_TTL_MINUTES | 120 |
| MIZEMI_RETENTION_DAYS | 7 |

Production requires PostgreSQL with `sslmode=require` or stronger and explicit HTTPS frontend origins with no path/trailing slash. `python -m app` respects HOST/PORT and starts one worker. Pool pre-ping/recycle reconnect after Neon idle suspension. PostgreSQL URLs normalize to `postgresql+psycopg`.

Frontend: `VITE_API_BASE_URL` and `VITE_WS_BASE_URL`, public origins only. Existing `VITE_MIZEMI_*` aliases remain supported; new names win. Without explicit WS URL, derive it from API URL or page origin. Empty API URL uses same-origin Vite proxy locally. All Vite values are public build-time values: never credentials. See both `.env.example` files and `render.yaml`.

## 17. Error Response Format

```json
{"error":{"code":"VALIDATION_ERROR","message":"The request is not valid."}}
```

Optional `details` may provide safe context. WebSockets wrap this object as the envelope payload. Registry: ROOM_NOT_FOUND, ROOM_FULL, NAME_TAKEN, INVALID_STATE_TRANSITION, QUESTION_CLOSED, ALREADY_ANSWERED, NOT_HOST, VALIDATION_ERROR, UNKNOWN_EVENT, INTERNAL_ERROR, ROOM_NOT_JOINABLE, NO_QUESTIONS_AVAILABLE. No internal exceptions, stack traces, DB errors, raw profiles or secrets are sent to clients.

## 18. Naming Conventions

Python snake_case modules/functions, PascalCase classes, Enum states/events. TypeScript PascalCase components/types, camelCase functions and hooks, strict types. Wire fields remain snake_case. Match the surrounding module style, avoid broad formatting-only changes, and keep IO guarded at boundaries.

## 19. Testing Conventions

pytest tests mirror backend modules. Pure domain tests have no IO; integration tests use real ASGI routes/sockets and isolated databases. Fake clocks test boundary times; short real timers test integration. Every regression gets coverage. TypeScript uses Vitest/Testing Library; Playwright exercises the actual production build with one host and three mobile browser contexts through twenty English rounds and a shorter Hebrew game, timeout, answer privacy, scoring and reconnects. A standalone smoke test uses 21 real TCP WebSockets.

PostgreSQL tests compile all table DDL and, with `MIZEMI_TEST_POSTGRES_URL`, verify real schema creation, complete game persistence, rollback, upsert and cleanup inside a temporary schema. Never point tests at production. CI runs the backend with PostgreSQL, frontend checks/build/browser test, secrets check and audits. Local commands are in README.md. No test may be deleted/weakened merely to turn a failure green; test corrections must explain the faulty expectation.

---

## 20. Git Conventions

- Default branch: `main`, always releasable/green. No direct commits to `main` once the initial scaffold lands — work on branches, merge via PR.
- Branch names: `<type>/<short-kebab-topic>` — `feature/question-engine-skeleton`, `fix/answer-deadline-race`, `docs/spec-update-scoring`, `chore/tooling-setup`.
- Commits: Conventional Commits — `type(scope): summary` with types `feat`, `fix`, `docs`, `test`, `refactor`, `chore`. Scope = module (`questions`, `game`, `api`, `frontend`). Imperative mood, ≤ 72-char subject.
- Spec changes (`MASTER_SPEC.md`) are always their own commit with type `docs(spec)` and are never buried in a feature commit.
- PRs: small and single-purpose; description states what/why and names any contract touched (which triggers §21 review).
- No force-push to shared branches; rebase local branches freely before first push.

---

## 21. Rules for Modifying Shared Contracts

**Shared contracts** are: the data shapes in §9, the state machine (§11), event names and envelope (§14), error format and code registry (§17), the REST conventions and route shapes (§13), profile field keys (§9.2), environment variable names (§16), and the module/layer boundaries (§5–§6).

Process for any change to a shared contract:

1. **Propose first.** Open a PR that modifies `MASTER_SPEC.md` (and only docs) describing the change, its motivation, and its migration impact on backend + frontend.
2. **Review by owners.** The owners of every affected module (see §7) approve.
3. **Land the spec, then the code.** The spec change merges before or together with the first implementing PR — never after.
4. **Both sides together.** Backend schema change and frontend type mirror change land in the same PR or in back-to-back PRs within the same day; the wire never disagrees with `frontend/src/types/`.
5. **Additive over breaking.** Prefer adding optional fields/events over renaming/removing. Breaking changes to WS events or REST routes bump the API version.
6. **No silent drift.** If implementation reveals the spec is wrong, stop, update the spec via this process, then continue. Code that contradicts the spec is a bug in one of them — decide which, explicitly.

---

## 22. AI Coding-Agent Guardrails

These rules bind every AI coding agent (Claude Code, Codex, or any other) working in this repository. They exist because agents act quickly and confidently; the spec is the leash.

An AI coding agent must **not**, on its own initiative:

1. **Redesign the architecture** — no switching away from the modular monolith, no re-layering, no new top-level modules.
2. **Alter shared contracts** (§21 list) — payload shapes, state names, field keys, error codes.
3. **Rename realtime events** or invent new ones outside §14's tables.
4. **Change shared models** — Player, PlayerProfile, Question, Score, Statistics shapes.
5. **Introduce major frameworks** — a different web framework, ORM, state-management library, CSS framework, etc.
6. **Introduce infrastructure services** — Redis, Kafka, RabbitMQ, Celery, external queues/caches/brokers, additional databases (§4 exclusion list).
7. **Create duplicate modules** — before creating any class, service, model, utility, or component, search the repo for an existing implementation and extend/reuse it.
8. **Replace established technologies** — e.g., swap pytest for another runner, Vite for another bundler.
9. **Modify unrelated code** — keep diffs scoped to the task; no drive-by refactors, reformatting sweeps, or "improvements" outside the task's boundary.
10. **Delete or weaken tests to make a change pass** — a failing test is information, not an obstacle.
11. **Add AI/LLM/ML services to application code** — hard product ban (§1), with no exception process short of changing §1 itself.
12. **Add any dependency on a paid service** — paid APIs, databases, hosting, realtime services, paid tiers, or payment-gated trials (Zero-Cost Constraint, §1).
13. **Decide a deferred decision** (§0 register) — deferred items are resolved in their named design stage via §21, never inline while implementing something else.

**If such a change appears necessary:** stop, and report the conflict — what the task asked, what the spec says, and the recommended resolution — instead of implementing it. A human decides; the agent may then implement the decided change following §21.

Additional agent obligations:

- Read `MASTER_SPEC.md` before making changes; when a task conflicts with it, surface the conflict rather than silently choosing.
- Preserve compatibility with existing modules; never break a green test suite knowingly.
- Match existing code style and naming (§18) rather than personal preference.
- When creating files, follow the folder structure (§6) exactly.

---

*End of MASTER_SPEC.md. If you are about to write code and haven't read §21 and §22 — go back and read them.*


## Legal information and accessibility implementation (18 September 2026)

Public frontend routes `/privacy`, `/terms`, `/accessibility` have English/Hebrew text and `?lang=en|he` deep links. They do not initialize a game socket. Shared footer links open separately during play with `noopener noreferrer`, preserving drafts and tab credentials. GitHub Pages links to these authoritative Render pages. They are disclosures, not legal certification.

`GET /api/v1/privacy-info` is PUBLIC and returns only `policy_version`, configured `retention_days`, `room_idle_ttl_minutes`, `maintenance_interval_seconds`, and `raw_profiles_persisted=false`. The collection notice fetches these facts without credentials/cache; submission remains disabled if the policy version/capability is incompatible or unavailable. This prevents deploying new storage promises against an old backend. Other public game and WebSocket contracts are unchanged.

Question-use labels explicitly control question generation/derivation, not transmission/storage. A visible pre-submission notice explains sharing, retention, optionality and the lack of profile editing. No new consent checkbox, age gate, tracking, cookie banner or automated deletion API was added. Owner-approved public operator identification is `yairrrr`. Legal pages and the collection notice link to `https://github.com/yairrrr/MiZeMi/issues` for initial non-sensitive contact only. They warn against public personal details and state the GitHub-account/repository-access requirement. Private verification/details must wait for a separately agreed private channel; Issues is not that channel. No email, phone or private address is published. Repository accessibility and confidential follow-up remain practical limits. The contact-text update date is 19 September 2026; the backend privacy capability version remains unchanged because data processing did not change.

Accessibility work includes landmarks/skip link, associated field errors, keyboard stage focus, text connection/rank/result cues, contrast, 320px reflow and reduced motion. The readable timer is not a live announcement each second; it announces only the near-deadline warning and expiry. Standard 20-second rules remain. Individual time extensions, real assistive-technology spoken-output evaluation and legal applicability review remain unresolved. See `LEGAL_IMPLEMENTATION_REPORT.md` for verification and limits.
