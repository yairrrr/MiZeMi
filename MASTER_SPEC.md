# MiZeMi — MASTER SPECIFICATION

**Status:** Implemented classroom MVP, v2.0, 2026-09-11. The completion mission explicitly authorized finalizing the previously deferred MVP decisions. This revision records the behavior on disk and supersedes the earlier proposed baseline. Architecture, no-runtime-AI, consent and zero-cost constraints remain binding.

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

Additional question rules, profile editing, localization, durable active-game recovery and versioned migration tooling can be added when specifically scoped. They must preserve the consent boundary and zero-cost/no-AI constraints.

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

### 9.1 Player contract

```json
{"player_id":"opaque-id","display_name":"Dana","is_host":false,"connected":true,"has_profile":true,"is_ready":false,"score":0}
```

Display names are trimmed, 1–20 characters, and unique per room under case-folding. New players have no profile, are unready/disconnected and score zero. `is_host` is always false. Scores are stored on Game and mapped into the public player snapshot.

### 9.2 PlayerProfile contract

Submission is exactly `{player_id, fields}`, where each field is `{field_key, value, allow_question_usage}`. Values are strictly strings or integers (not booleans); consent is a strict boolean. Up to seven fields; unknown/duplicate keys and missing required fields are rejected.

| Key | Type / constraints | Required | Initial UI consent |
|---|---|---|---|
| city | Text, 1–40 characters | Yes | Checked |
| favorite_food | Text, 1–40 | Yes | Checked |
| hobby | Text, 1–40 | Yes | Checked |
| favorite_music | Listed choice | Yes | Checked |
| age | Integer, 5–120 | No | Checked |
| favorite_movie | Text, 1–60 | No | Checked |
| personal_fact | Text, 1–120 | No | **Unchecked** |

Music choices: Pop, Rock, Hip-Hop / Rap, Electronic, Mizrahi, Classical, Jazz, Metal, Other. Text is trimmed and whitespace collapsed. Contact-like emails, URLs and runs of seven or more digits are rejected. This heuristic does not claim to detect all sensitive content; the UI explicitly asks players not to enter private details. Use nicknames and light facts for class.

Consent may be withheld for **every** field, including required fields. Empty optional inputs are omitted. Profile submission is initial-only, through `player.profile_submit`; the connection identity must match `player_id`. No public profile-read endpoint and no post-submission editor exist.

### 9.3 Question format

```json
{"question_id":"opaque-id","index":0,"total_questions":10,"question_type":"multiple_choice","text":"Question text","options":[{"option_id":"a","text":"Answer A"},{"option_id":"b","text":"Answer B"}],"time_limit_seconds":20,"started_at":"2026-09-11T08:00:00.000Z"}
```

`index` is zero-based. The production rules generate 2–4 distinct options with exactly one correct option. Option ids are opaque. Default question count is 10 (configurable 1–50); default timeout is 20 seconds (1–300). The engine returns fewer questions if fewer valid candidates exist, and rejects starting with none. It never invents non-consented facts to fill a quota.

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

Default database retention: seven days, with entire expired game trees removed (including generated questions containing facts). Cleanup runs at startup and every five minutes while running; overdue cleanup runs after a sleeping service wakes. Rooms with no connections are removed after 120 idle minutes. Credentials expire with their room. Connected rooms remain in memory while their process lives.

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

Production rules: unique value, most common value with a strict winner, and value count. Rules normalize whitespace/case for grouping, draw plausible distractors from the dataset or nearby counts, and shuffle options deterministically. Rule-level tests prove semantic correctness and consent exclusion. The shared validator enforces nonempty/distinct text/ids, exactly one designated correct option, and valid dataset references. Current generated lengths are bounded by the validated input schema.

Selection removes normalized duplicate text and repeated `(rule, fields, subject)` signatures. It prioritizes rule and field diversity, quality, player spread, then text for stable order. Adding a rule requires a class, registration, and truth/consent tests; it must preserve these invariants.

## 13. REST / API Conventions

Base `/api/v1`, JSON objects, snake_case, UTC ISO-8601 `Z`. Public endpoints:

| Method/path | Request | Success |
|---|---|---|
| GET `/health` | None | 200 health response |
| POST `/rooms` | No payload required | 201 `{room_code, game_id, host_token}` |
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
| room.updated | `{room_code, state, players: Player[], current_question_index: number|null, total_questions}` |
| game.started | `{total_questions}` |
| question.started | §9.3, no correct answer |
| answer.accepted | `{question_id, option_id}` to answerer's sockets only |
| statistics.updated | Active counts-only §9.6 |
| question.ended | `{question_id, text, options, correct_option_id, statistics, player_result}` |
| leaderboard.updated | §9.7 |
| game.finished | `{leaderboard: Leaderboard, winners: LeaderboardEntry[]}` |
| error | §17 error object |

`question.ended.text` and `.options` repeat the public content so a reconnect needs no earlier question event to render results. Correct answer/statistics are only emitted after that question closes. `player.joined` and `player.updated` remain registered for compatibility; complete room snapshots currently carry their information.

### 14.3 Message envelope

Both directions use **exactly**:

```json
{"event":"question.started","payload":{},"timestamp":"2026-09-11T08:00:00.000Z","game_id":"opaque-id"}
```

Server time is serialized in UTC with milliseconds and Z. Client timestamps must be timezone-aware but never determine game outcomes. Wrong game id, malformed JSON, binary frames, malformed payloads and unknown events receive safe errors (UNKNOWN_EVENT or VALIDATION_ERROR). Clients ignore unknown events. Extras are forbidden by the relevant schemas.

All room mutations and event enqueueing occur under one room lock. Each socket drains an independent FIFO queue. Limits: 16,384 text characters per app frame; 65,536 transport bytes; 120 incoming frames per socket per ten seconds; 256 queued outbound messages, five-second send timeout. Slow/flooding clients close and can reconnect; they do not block the class. HTTP limits are 16 KiB body, 240 POSTs per IP/minute, 100 active rooms and default 50 players per room. IP limits allow classroom NAT sharing and are not an enterprise DDoS system.

## 15. Persistence Conventions

SQLAlchemy declarative models and repository interfaces. ORM/bound statements only; no input-interpolated SQL. Every row has UTC created/updated timestamps. Sessions own transactions; commit explicitly, roll back on failure/close. SQL error parameter printing is disabled.

One finished game stores players, profiles/consent, generated questions/options, accepted answers with server times, and final scores. The seven tables are `games`, `players`, `profile_fields`, `game_questions`, `question_options`, `answers`, `scores`. Answers/scores are additive tables, so old retained games have empty answers/scores. Writes occur off-loop at FINISHED; shutdown waits for submitted writes before disposing the engine. Persistence failure emits a safe log message, without credentials/query parameters; no durable retry queue exists.

Active rooms, token digests and active games are memory-only; process restart invalidates their credentials and loses unfinished games. Finished records are internal read-only repository records, not rehydrated active rooms. Whole-tree upserts, rollback and retention cascades work on SQLite and PostgreSQL.

**Initial schema strategy:** `Base.metadata.create_all` before startup becomes healthy, on local or production databases. It creates missing tables only; no automatic column alteration. A fresh Neon project needs no manual SQL. Add versioned migrations before future existing-table changes. See DEPLOYMENT.md.

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
| MIZEMI_QUESTIONS_PER_GAME | 10 |
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

pytest tests mirror backend modules. Pure domain tests have no IO; integration tests use real ASGI routes/sockets and isolated databases. Fake clocks test boundary times; short real timers test integration. Every regression gets coverage. TypeScript uses Vitest/Testing Library; Playwright exercises the actual production build with one host and three mobile browser contexts through ten rounds, timeout, answer privacy, scoring and reconnects. A standalone smoke test uses 21 real TCP WebSockets.

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
