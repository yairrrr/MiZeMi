# MiZeMi — MASTER SPECIFICATION

**Status:** Proposed baseline — awaiting team review (v1.4, 2026-08-10). Only items explicitly marked as **Approved** (the product constraints in §1, the profile categories in §9.2, the privacy principles in §10, and the contract decisions recorded in v1.3–v1.4 across §8, §9.2, §9.3, §11, §13, §14) reflect confirmed team decisions; the rest is the proposed technical baseline.
**Audience:** All contributors, human and AI coding agents.
**Rule zero:** Read this document before writing any code. Changes to this document follow the process in [§21 Rules for Modifying Shared Contracts](#21-rules-for-modifying-shared-contracts).

---

## Table of Contents

0. [Decision Status and Deferred Decisions](#0-decision-status-and-deferred-decisions)
1. [Product Purpose](#1-product-purpose)
2. [MVP Scope](#2-mvp-scope)
3. [Future Enhancements](#3-future-enhancements)
4. [Technology Stack](#4-technology-stack)
5. [Architecture: Modular Monolith](#5-architecture-modular-monolith)
6. [Folder Structure](#6-folder-structure)
7. [Module Responsibilities and Team Ownership](#7-module-responsibilities-and-team-ownership)
8. [Shared Domain Concepts](#8-shared-domain-concepts)
9. [Shared Contracts](#9-shared-contracts)
10. [Privacy Rules and Data Minimization](#10-privacy-rules-and-data-minimization)
11. [Game State Machine](#11-game-state-machine)
12. [Question Generation Engine](#12-question-generation-engine)
13. [REST / API Conventions](#13-rest--api-conventions)
14. [Realtime (WebSocket) Conventions](#14-realtime-websocket-conventions)
15. [Persistence Conventions](#15-persistence-conventions)
16. [Environment Variable Conventions](#16-environment-variable-conventions)
17. [Error Response Format](#17-error-response-format)
18. [Naming Conventions](#18-naming-conventions)
19. [Testing Conventions](#19-testing-conventions)
20. [Git Conventions](#20-git-conventions)
21. [Rules for Modifying Shared Contracts](#21-rules-for-modifying-shared-contracts)
22. [AI Coding-Agent Guardrails](#22-ai-coding-agent-guardrails)

---

## 0. Decision Status and Deferred Decisions

Every statement in this document belongs to one of three categories:

1. **Approved decisions** — product/team decisions that have been explicitly approved (e.g., the no-AI constraint, the Zero-Cost Constraint, the approved profile categories, per-field privacy consent, no user accounts in MVP).
2. **Technical baseline** — architecture and engineering decisions needed to begin development (e.g., the modular monolith, FastAPI, layer boundaries, event names, wire conventions). These are binding but changeable through the process in §21.
3. **Deferred decisions** — intentionally *not* decided yet. They are marked **Deferred** where they appear. Contributors — human or AI — must not fill in a deferred decision to make code or documentation look complete; deciding one requires its named design stage plus a spec update (§21).

**Deferred decisions register:**

| Deferred decision | To be decided during | See |
|---|---|---|
| Final PlayerProfile field schema (field keys, value types, validation rules, enum vs. free text, required vs. optional) | PlayerProfile design stage | §9.2 |
| Exact scoring formula, including whether/how answer speed affects points | Scoring design stage | §9.5 |
| Auxiliary score/statistics fields beyond the core shapes | Scoring/statistics design stage | §9.5, §9.6 |
| Data retention / cleanup duration | Persistence & privacy design stage | §10, §15 |
| Room code exact format and generation rules | Room design stage | §8 |
| Host authorization mechanism (distinguishing Host actions from Player actions) | Backend/Room design stage | §8, §14.1 |
| Public id format (e.g., which UUID variant, if any) | Backend implementation design | §8, §13, §15 |
| Display-name validation rules (length limits, uniqueness handling) | Player/Room design stage | §9.1 |
| Answer-option count bounds, question time limits, questions per game | Gameplay/question design stage | §9.3, §12.3 |
| Answer resubmission policy and deadline/late-submission handling | Gameplay design stage | §9.4 |
| Late-join and reconnection rules | Room/gameplay design stage | §11 |
| Database migration tooling and strategy | When the schema stabilizes | §15 |
| Exact persistence points and restart/recovery guarantees | Backend implementation design | §15 |
| Python formatter/linter toolchain | Dev-tooling setup | §18.1 |
| Frontend E2E testing with Playwright | First stable backend-connected vertical slice | §19 |
| CI system and configuration | Dev-tooling setup | §19 |
| Room capacity limit (the rule that triggers `ROOM_FULL`) | Room design stage | §17 |
| Internal host representation (whether the host is modeled as a Player) | Room/Game design stage | §8, §9.1 |
| Canonical transport for profile submission (REST vs. the `player.profile_submit` WS event) | Room/gameplay design stage | §13, §14.2 |
| Leaderboard tie-breaking rules | Scoring design stage | §9.7 |
| React major version | Frontend scaffolding (when the repo actually installs it) | §4 |

---

## 1. Product Purpose

MiZeMi ("מי זה מי" — "Who's Who") is a **real-time multiplayer group icebreaker game**, similar in interaction style to Kahoot.

- A **host** creates a room and displays it on a shared screen.
- **Players** join the room from their phones using a short room code.
- Each player submits a small **profile** (name, and a handful of fun facts/preferences).
- The application **algorithmically generates quiz questions from the group's own submitted information** (e.g., "Who is the only one whose hobby is rock climbing?", "How many people picked pizza as their favorite food?").
- Players answer in real time; scores and statistics are shown between questions; a leaderboard crowns a winner.

The product goal is social connection: the group learns about each other through questions built from their own answers.

### Critical Product Constraint — No AI at Runtime

**The MiZeMi application must not use AI, LLMs, machine-learning APIs, or generative-AI services during gameplay or question generation.** Question generation is purely algorithmic (deterministic rules over the group's submitted data — see [§12](#12-question-generation-engine)).

AI coding assistants (Claude Code, Codex, etc.) are **development tools only**. No AI SDK, API client, or model may appear in application dependencies or runtime code paths.

### Critical Product Constraint — Zero Cost

The MiZeMi MVP must be **developable, testable, deployable, and demonstrable without paying for any service.**

The project **may** use:

- Free and open-source software.
- Genuinely free service tiers — only when the free tier is, by itself, sufficient for the project's needs.

The project must **not** depend on:

- Paid APIs.
- Paid databases.
- Paid hosting.
- Paid realtime services.
- Paid AI services (AI is banned at runtime regardless — see above).
- Free trials that later require payment.
- Services that require upgrading to a paid plan for the MVP to function.

Any future service that could introduce cost requires **explicit team approval and a MASTER_SPEC.md update (§21) before adoption.**

---

## 2. MVP Scope

### In scope

- Host creates a game room; players join via room code from a phone browser (no app install).
- Player profile submission based on the approved profile categories (final field schema **deferred** — see [§9.2](#92-playerprofile-contract)).
- Per-field privacy opt-out via `allow_question_usage` (see [§10](#10-privacy-rules-and-data-minimization)).
- Algorithmic question generation from submitted profiles (multiple-choice questions only).
- Real-time gameplay: synchronized question display, timed answering, per-question results, running leaderboard.
- Server-authoritative, deterministic scoring (exact formula **deferred** to the scoring design stage — see [§9.5](#95-score-format)).
- Between-question statistics (answer distribution — see [§9.6](#96-statistics-format)).
- Single game session lifecycle: lobby → profile collection → gameplay → final results (see [§11](#11-game-state-machine)).
- **No user accounts.** Players are ephemeral, identified per-game by a server-issued player id and a self-chosen display name.
- SQLite persistence; single-process deployment.

### Out of scope for MVP

- User accounts, authentication, or cross-game identity.
- Multiple simultaneous games per host beyond simple isolation by room code (basic multi-room support is in; host account management is not).
- Question types other than multiple choice.
- Persistent player history or analytics across games.
- Internationalization framework (write user-facing strings so extraction is easy, but no i18n library in MVP).
- Native mobile apps.
- Horizontal scaling / multi-node deployment.

---

## 3. Future Enhancements

This list is deliberately conservative: it contains only directions that originate from the MiZeMi product requirements. These are candidate ideas — **not** commitments — and none may be started without a spec update (§21). Any enhancement must also satisfy the Zero-Cost Constraint (§1) or obtain explicit team approval for its cost first.

- Additional question types.
- Additional profile categories.
- More game modes, including a teams mode.
- Advanced analytics/statistics.
- Localization (e.g., Hebrew/English UI).
- Persistent accounts / player history, if ever desired.

---

## 4. Technology Stack

### Backend

| Concern | Choice |
|---|---|
| Language | Python 3.12+ |
| Web framework | FastAPI |
| Validation / DTOs | Pydantic v2 |
| ORM | SQLAlchemy 2.x |
| Database (MVP) | SQLite |
| Testing | pytest |
| Realtime | FastAPI WebSockets (built-in, Starlette) |

### Frontend

| Concern | Choice |
|---|---|
| Language | TypeScript (strict mode) |
| Framework | React (major version chosen when the frontend is scaffolded; not locked by this document) |
| Build tool | Vite |
| Unit testing | Vitest |
| Component testing | React Testing Library with `jsdom` |
| Test interactions / DOM assertions | `@testing-library/user-event` / `@testing-library/jest-dom` |
| E2E testing | Playwright (**deferred** until the first stable backend-connected vertical slice) |
| Realtime | Native browser WebSocket |

### Communication

- **REST** for commands and resources where realtime delivery is unnecessary (room creation, profile submission, fetching static room info).
- **WebSockets** for realtime game state and gameplay events (state transitions, question broadcast, answer acknowledgment, leaderboards).

Every item in this stack is free and open-source, as the Zero-Cost Constraint (§1) requires.

### Explicitly excluded

The following must **not** be introduced unless this document is deliberately changed by the team through the process in §21:

- Microservices (of any kind)
- Redis, Kafka, RabbitMQ, Celery (or any external broker/queue/cache service)
- GraphQL
- AI services, LLM APIs, ML libraries in application code (hard product constraint — see §1)
- Any dependency on a paid service, paid tier, or payment-gated trial (Zero-Cost Constraint — see §1)

The core application logic (domain layer and question generation engine) is written in **object-oriented Python**: domain concepts are classes with behavior, rules are polymorphic class implementations of a shared interface, and state transitions are methods on aggregate objects — not loose dict-passing functions.

---

## 5. Architecture: Modular Monolith

MiZeMi is a **modular monolith**: one deployable backend process, internally divided into modules with strict boundaries. Modules communicate through Python interfaces in-process — never through network calls, queues, or shared mutable globals.

### Layers

```
┌─────────────────────────────────────────────────────┐
│ Presentation      backend/app/api/  +  realtime/    │  HTTP/WS in-out only
├─────────────────────────────────────────────────────┤
│ Application       backend/app/application/          │  Use-case orchestration
├─────────────────────────────────────────────────────┤
│ Domain            backend/app/domain/               │  Pure business logic (OOP)
├─────────────────────────────────────────────────────┤
│ Infrastructure    backend/app/infrastructure/       │  DB, repositories, IO
└─────────────────────────────────────────────────────┘
```

### Layer boundaries (dependency rules)

- **Presentation** (`api/`, `realtime/`) parses/serializes HTTP and WebSocket traffic and calls **Application** services. It contains no business logic and never touches the database directly.
- **Application** (`application/`) implements use cases ("player joins room", "host starts game", "advance to next question"). It orchestrates domain objects and repositories, owns transactions, and emits realtime events. It contains no framework-specific (FastAPI) types and no SQL.
- **Domain** (`domain/`) is pure Python OOP: entities, value objects, domain services, the game state machine, and the question generation engine. It imports **nothing** from other layers — no FastAPI, no SQLAlchemy, no Pydantic network DTOs. It is fully unit-testable without IO.
- **Infrastructure** (`infrastructure/`) implements persistence (SQLAlchemy models, repository implementations) behind repository interfaces defined by the application/domain side. Only infrastructure knows SQL/SQLite exists.

Allowed dependency direction: `presentation → application → domain`, and `infrastructure → (application interfaces + domain)`. **Domain depends on nothing above it. Nothing skips a layer.**

### Authoritative server

**The backend is the single authoritative source of game state.** Clients render state and send intents (join, answer, advance); they never compute game outcomes locally. Every state change is decided by the backend and broadcast to clients via WebSocket events. Client-side timers are cosmetic; the server clock decides question deadlines and scoring.

---

## 6. Folder Structure

```
MiZeMi/
├── MASTER_SPEC.md
├── README.md
├── .gitignore
├── backend/
│   ├── app/
│   │   ├── api/                  # REST routers, request/response schemas (Pydantic)
│   │   ├── realtime/             # WebSocket connection manager, event envelope, dispatch
│   │   ├── application/          # Use-case services, repository interfaces, event emission
│   │   ├── domain/
│   │   │   ├── game/             # Game aggregate, Room, Player, state machine
│   │   │   ├── questions/        # Question Generation Engine (see §12)
│   │   │   ├── scoring/          # Score calculation policies
│   │   │   └── statistics/       # Answer-distribution and group statistics
│   │   └── infrastructure/
│   │       ├── database/         # Engine/session setup, SQLAlchemy models, migrations
│   │       └── repositories/     # Repository implementations
│   └── tests/
│       ├── unit/                 # Pure domain/application tests, no IO
│       ├── integration/          # API + WebSocket + DB tests
│       └── fixtures/             # Shared pytest fixtures and factory data
└── frontend/
    └── src/
        ├── api/                  # Typed REST client functions
        ├── realtime/             # WebSocket client, envelope types, event handlers
        ├── components/           # Reusable presentational components
        ├── features/
        │   ├── host/             # Host screens (create room, control game, big screen)
        │   ├── player/           # Player screens (join, profile form, answer pad)
        │   └── game/             # Shared gameplay views (question, results, leaderboard)
        ├── hooks/                # Reusable React hooks
        ├── types/                # Shared TypeScript types mirroring backend contracts
        └── utils/                # Pure helper functions
```

New top-level folders in `backend/app/` or `frontend/src/` require a spec update. The root `main.py` currently in the repository is a placeholder from project creation and will be removed when the `backend/` scaffold is created; the backend entrypoint will live under `backend/app/`.

---

## 7. Module Responsibilities and Team Ownership

| Module | Responsibility | Owner |
|---|---|---|
| `backend/app/api/` | REST endpoints, request validation, HTTP error mapping | Backend/Platform |
| `backend/app/realtime/` | WebSocket lifecycle, room broadcast, event envelope | Backend/Platform |
| `backend/app/application/` | Use-case orchestration, transactions, repository interfaces | Backend/Platform |
| `backend/app/domain/game/` | Game aggregate, room membership, state machine | Backend/Gameplay |
| `backend/app/domain/questions/` | Question Generation Engine and all QuestionRules | Backend/Question Engine |
| `backend/app/domain/scoring/` | Scoring policies (deterministic, server-authoritative; formula deferred — §9.5) | Backend/Gameplay |
| `backend/app/domain/statistics/` | Answer distributions, group stats | Backend/Gameplay |
| `backend/app/infrastructure/` | SQLAlchemy models, repositories, DB session management | Backend/Platform |
| `frontend/src/features/host/` | Host experience | Frontend |
| `frontend/src/features/player/` | Player experience | Frontend |
| `frontend/src/features/game/` | Shared gameplay views | Frontend |
| `frontend/src/api/`, `realtime/`, `types/` | Backend contract mirrors | Frontend (changes gated by §21) |
| `MASTER_SPEC.md` | Shared contracts and architecture | Whole team (process in §21) |

Until the team grows, one person may hold several ownership roles; the boundaries still apply — a change crossing an ownership boundary gets a review from that area's owner (or explicit self-review noted in the PR).

Ownership also sets the **implementation boundary**: the shared game/player domain contracts are implemented as shared contracts, the Question Generation Engine classes (§12.1) are implemented only within the Question Engine workstream, and the scoring policy class (§9.5) only within the scoring workstream. The proposed design is **not** a single implement-everything-together unit — no workstream implements classes owned by another workstream preemptively.

---

## 8. Shared Domain Concepts

Ubiquitous language — use these names in code, APIs, events, and conversation:

- **Room** — a joinable session identified by a unique, short, human-friendly `room_code`. **Deferred:** the exact code format and generation rules will be determined during the Room design stage. A room hosts exactly one **Game** in MVP.
- **Host** — the client that created the room and controls game flow; not a user account. The backend must be able to distinguish authorized Host actions from Player actions. **Deferred:** the concrete mechanism (the simplest workable option for the MVP) will be chosen during backend/Room design; no host-credential shape is a shared contract yet.
- **Player** — a participant in a room. Ephemeral; exists only within one game.
- **PlayerProfile** — the structured facts a player submits about themselves.
- **Game** — the aggregate root: owns state machine, players, question sequence, answers, and scores.
- **Question** — a generated multiple-choice question presented to all players simultaneously.
- **QuestionCandidate** — an internal engine artifact: a potential question produced by a rule, prior to validation/selection (never leaves the engine).
- **Answer** — a player's choice for a specific question, timestamped by the server.
- **Score** — a player's accumulated points.
- **Leaderboard** — ranked players by score at a point in time.
- **Statistics** — aggregate answer/group data shown between questions.

Identifiers: all public ids (`game_id`, `player_id`, `question_id`) are server-generated, unique, opaque strings — created by the backend, never by clients. **Deferred:** the concrete id format (e.g., which UUID variant, if any) is an implementation choice made during backend design. `room_code` is the only human-facing identifier.

**Deliberately absent — Round (approved):** the MVP defines no Round domain concept. `Question.index` plus the game state machine (§11) cover per-question progression. A Round abstraction may be reconsidered only if a later concrete requirement justifies it.

---

## 9. Shared Contracts

These are **shared contracts**: the backend Pydantic schemas, the frontend types in `frontend/src/types/`, and the wire formats below must stay in lockstep. Changing any of them follows §21.

Field shapes are shown as JSON wire format (snake_case keys — see §13).

### 9.1 Player contract

```jsonc
{
  "player_id": "uuid",           // server-generated, stable for the game
  "display_name": "string",      // validation rules (length, uniqueness handling) deferred — see §0
  "is_host": false,              // host is not a player in MVP; reserved
  "connected": true,             // realtime connection status
  "has_profile": true,           // profile submitted
  "is_ready": false,             // ready flag during PROFILE_COLLECTION/READY
  "score": 0                     // current total score
}
```

### 9.2 PlayerProfile contract

A profile is a set of **fields**. Every field carries a per-field privacy flag. The envelope structure below is the approved shape; the concrete field list is **not** final.

```jsonc
{
  "player_id": "uuid",
  "fields": [
    {
      "field_key": "favorite_food",      // illustrative — final field keys are deferred
      "value": "pizza",
      "allow_question_usage": true       // player consent for use in questions
    }
  ]
}
```

**Approved conceptual profile categories** (team-approved; these are categories, not final field keys):

- display name (captured when joining the room; lives on the Player contract, §9.1)
- age
- city
- favorite food
- hobby
- personal fact (optional)
- favorite music
- favorite movie

**Deferred — PlayerProfile design stage:** the exact final field schema — field keys, value types, validation rules, enum vs. free-text decisions, and which fields are required vs. optional — will be finalized during the dedicated PlayerProfile design stage. Once finalized, the field list becomes part of this shared contract and subsequent changes follow §21. **Approved interim typing:** until that stage, domain code may type a field's `value` as `str | int`; this is intentionally temporary and not part of the final schema.

Approved privacy behavior, regardless of the final schema:

- Every field carries `allow_question_usage` (see §10).
- The personal fact is optional, and its `allow_question_usage` must be an explicit player choice (no silently pre-set `true`).
- Personal information remains optional where appropriate.

### 9.3 Question format

```jsonc
{
  "question_id": "uuid",
  "index": 3,                       // 0-based position in the game
  "total_questions": 10,
  "question_type": "multiple_choice",  // only value in MVP
  "text": "How many players picked pizza as their favorite food?",
  "options": [                      // exactly one correct option; count bounds deferred
    { "option_id": "a", "text": "3" },
    { "option_id": "b", "text": "5" },
    { "option_id": "c", "text": "7" },
    { "option_id": "d", "text": "9" }
  ],
  "time_limit_seconds": 20,
  "started_at": "ISO-8601 UTC"      // server time the question opened
}
```

The *fields* above are the contract; the example values are illustrative. **Approved:** `option_id` is an opaque string — values such as `"a"`–`"d"` may appear in examples but are not a required identifier format. **Deferred — gameplay/question design stage:** answer-option count bounds, default/allowed time limits, and questions per game.

The correct `option_id` is **never** sent to clients while the question is active. It is revealed only in the `question.ended` event.

#### 9.3.1 Server-domain Question lifecycle

The shared server-domain types separate generated question content from the
runtime data added when a question opens:

- `QuestionType` has the single MVP value `multiple_choice`.
- `QuestionOption` contains `option_id` and `text`; `option_id` remains an
  opaque string.
- `Question` contains `question_id`, `index`, `total_questions`,
  `question_type`, `text`, `options`, `correct_option_id`, and
  `time_limit_seconds`.

`Question.correct_option_id` is server-private domain data. It must identify
exactly one option and is omitted from the active-question payload above. The
application/presentation flow reveals it only through `question.ended`.

`started_at` is not stored on a generated domain `Question`. The authoritative
server clock supplies it when that question becomes active, and the
application/presentation layer combines it with the domain question to build
the §9.3 active-question payload. This permits the Question Engine to generate
the complete deterministic question sequence before future questions have an
opening time.

**Migration impact:** this clarification does not change the §9.3 or §9.6 wire
shapes and therefore requires no frontend field migration. Backend Game and
Question Engine code consume the shared domain `Question`; presentation code
must continue to omit `correct_option_id` while a question is active and add
the server-owned `started_at` value at serialization time.

### 9.4 Answer submission format

Sent over WebSocket as the payload of `answer.submit`:

```jsonc
{
  "question_id": "uuid",
  "option_id": "b"
}
```

Server behavior: the server records each submission with its own clock (`answered_at`) — client timestamps are ignored, and the server alone decides whether a submission counts (§5). **Deferred — gameplay design stage:** whether a player may change an answer while the question is open, and exact deadline/late-submission handling.

### 9.5 Score format

```jsonc
{
  "player_id": "uuid",
  "total_score": 1730
}
```

Scoring is owned by `domain/scoring/` and must be **deterministic and server-authoritative** — client clocks and client-side math never decide points. **Deferred — scoring design stage:** the exact scoring formula, point values, and whether/how answer speed affects points have not been approved; speed-based scoring may be considered at that stage. The formula will live in one policy class; tuning it will not change this contract, but changing the *fields* above does. Auxiliary score fields (e.g., points earned on the last question, per-player correct/answered counts) are likewise deferred to that stage and would be added via §21. Implementing the policy class belongs to the scoring workstream (§7) and happens in that workstream's dedicated tasks.

### 9.6 Statistics format

```jsonc
{
  "question_id": "uuid",
  "correct_option_id": "b",
  "answer_distribution": [
    { "option_id": "a", "count": 2 },
    { "option_id": "b", "count": 6 },
    { "option_id": "c", "count": 1 },
    { "option_id": "d", "count": 0 }
  ],
  "answered_count": 9,
  "player_count": 11
}
```

Statistics are aggregate-only: they never expose which specific player gave which answer. **Deferred — scoring/statistics design stage:** any statistics fields beyond the aggregate distribution above (e.g., speed-related callouts).

### 9.7 Leaderboard format

```jsonc
{
  "entries": [
    { "rank": 1, "player_id": "uuid", "display_name": "Dana", "total_score": 2410 }
  ]
}
```

**Deferred — scoring design stage:** tie-breaking rules for equal scores.

---

## 10. Privacy Rules and Data Minimization

1. **Per-field consent.** Every profile field carries `allow_question_usage`. The Question Generation Engine must treat a field with `allow_question_usage: false` as if it does not exist. There is no override.
2. **`personal_fact` is special.** It is optional, and it must **never** be used in question generation when its `allow_question_usage` is `false`. The submission UI must present this choice explicitly (no pre-checked box).
3. **No user accounts in MVP.** No emails, phone numbers, passwords, or third-party logins are collected. A player is a display name plus a game-scoped id.
4. **Data minimization.** Collect only fields within the approved profile categories of §9.2. Do not log profile values. Do not add tracking/analytics that captures profile content.
5. **Ephemeral by default.** Game data (profiles, answers) exists to run the game; it is temporary, and completed games' profile data is deleted or anonymized by a cleanup routine. **Deferred:** the exact cleanup/retention duration will be determined later; no configuration variable is defined for it yet. Aggregate, non-identifying stats may be kept.
6. **Profiles are private to the engine.** Raw profile values of one player are never sent to other clients. Players see only questions, aggregate statistics, and leaderboard entries. (A question may of course reveal a fact — e.g. "Whose hobby is rock climbing?" — but only through fields the player consented to.)
7. **No profile data in URLs.** Room codes and ids may appear in URLs; profile values never.

---

## 11. Game State Machine

Owned by `domain/game/`. The backend enforces transitions; clients merely render the current state.

```
LOBBY
  └─ first valid profile accepted (automatic) ─► PROFILE_COLLECTION
PROFILE_COLLECTION
  └─ all players ready ──────────► READY
READY
  └─ game.start (host) — question set generated ─► QUESTION_ACTIVE
QUESTION_ACTIVE
  └─ all answered OR timeout ────► QUESTION_RESULTS
QUESTION_RESULTS
  └─ game.next (host) ───────────► LEADERBOARD
LEADERBOARD
  ├─ game.next (host), more questions ─► QUESTION_ACTIVE
  └─ game.next (host), none left ─────► FINISHED
FINISHED   (terminal)
```

Linear flow: `LOBBY → PROFILE_COLLECTION → READY → (QUESTION_ACTIVE → QUESTION_RESULTS → LEADERBOARD)* → FINISHED`.

Rules:

- State names are part of the shared contract and appear verbatim (UPPER_SNAKE) in payloads.
- Players join during the pre-game phases, and a disconnected player must be able to reconnect with the same `player_id`. **Deferred — Room/gameplay design stage:** exactly which states permit late joining and the precise reconnection rules.
- Illegal transition attempts return/emit `error` with code `INVALID_STATE_TRANSITION`; the state does not change.
- **Approved — question-generation timing:** the game's question set is generated when the host starts the game via `game.start` (the `READY → QUESTION_ACTIVE` transition) — never merely because the game entered `READY`. All consented profile data is available by that point.
- **Approved — start vs. next:** `game.start` is used only to start the game from `READY`. `game.next` advances the post-round flow (`QUESTION_RESULTS → LEADERBOARD`, then `LEADERBOARD → QUESTION_ACTIVE` or `FINISHED`). No new event name is introduced.
- **Approved — entering profile collection:** a newly created Room begins in `LOBBY`, and players may join while it is in `LOBBY`. Profile submission is valid in both `LOBBY` and `PROFILE_COLLECTION`. When the server accepts the **first** valid profile submission, it automatically transitions `LOBBY → PROFILE_COLLECTION` — no host command is required and no new realtime event exists for it; the transition is announced through the existing `room.updated` snapshot and may also be reflected in the submitter's `player.updated`. `PROFILE_COLLECTION → READY` remains governed by the existing readiness contract; no additional readiness rules are defined here.
- Every transition is broadcast via `room.updated` carrying the new state (plus the specific event, e.g. `question.started`).

---

## 12. Question Generation Engine

Lives in `backend/app/domain/questions/`. **Purely algorithmic — no AI, no external services, no network calls** (see §1). Deterministic given (dataset, seed).

### 12.1 Pipeline architecture

Six separated responsibilities. **This section is a design specification — these classes are not implemented yet and must not be implemented as part of documentation tasks.** They belong to the Question Generation Engine workstream (§7): they are implemented in that workstream's dedicated tasks, and other workstreams must not implement them preemptively.

```
ProfileDataset (consented fields only)
      │
      ▼
QuestionGenerator                 — orchestrates the pipeline below
      │  runs each registered
      ▼
QuestionRule (many implementations)
      │  each produces 0..N
      ▼
QuestionCandidate                 — text, options, correct answer, metadata
      │  filtered by
      ▼
QuestionValidator                 — rejects invalid/ambiguous candidates
      │  scored by
      ▼
QuestionQualityScorer             — ranks candidates by interest/quality
      │  chosen by
      ▼
QuestionSelector                  — picks final set: quality + diversity + dedup
      │
      ▼
List[Question]                    — the game's question sequence
```

- **QuestionGenerator** — entry point. Builds the consented `ProfileDataset`, invokes every registered `QuestionRule`, then pipes candidates through validation → scoring → selection. Accepts a random seed for reproducibility in tests.
- **QuestionRule** — abstract base class; one concrete subclass per question idea (see 12.2).
- **QuestionCandidate** — value object: question text, options, correct option, source rule id, source field keys, involved player ids, and rule-supplied metadata for scoring/diversity.
- **QuestionValidator** — rejects candidates that break correctness invariants (see 12.3).
- **QuestionQualityScorer** — assigns each valid candidate a quality score (see 12.4).
- **QuestionSelector** — picks the final ordered set under diversity and dedup constraints (see 12.5).

### 12.2 QuestionRule extensibility model

- Each `QuestionRule` implementation is **independent**: it receives the consented `ProfileDataset` and returns **zero or more** `QuestionCandidate` objects, depending entirely on whether the dataset supports its pattern. (A "unique city" rule yields nothing if no city is unique; a frequency rule yields nothing with 3 players.)
- Rules are registered with the generator (explicit registry list); adding a new rule means adding one new class and one registry entry — **no changes to the generator, validator, scorer, or selector**.
- A rule must never read fields with `allow_question_usage: false`; the dataset given to rules already excludes them, and rules must not reach around it.
- Rules are pure: no IO, no randomness except via the provided seeded RNG.

The engine's rule set must eventually support (roadmap for rule implementations, not an MVP checklist; example questions are illustrative against the approved profile categories of §9.2 — concrete rules will target the final schema):

- **Frequency analysis** — "What is the most common favorite food in this group?"
- **Counts** — "How many players are younger than 30?"
- **Matching players to values** — "Which player's hobby is rock climbing?"
- **Uniqueness detection** — "Who is the only player from Haifa?"
- **Duplicate detection** — "Which two players picked the same favorite movie?"
- **Majority/minority analysis** — "Are there more rock fans than pop fans in this group?"
- **Comparisons** — "Who is older, Dana or Omer?"
- **Reasonable distractor generation** — wrong options that are plausible (drawn from the same value space / nearby numbers), not absurd.
- **Unambiguous answer validation** — exactly one defensibly correct option (validator's job, see 12.3).
- **Candidate quality scoring** — see 12.4.
- **Question diversity** — see 12.5.
- **Near-duplicate prevention** — see 12.5.

### 12.3 Candidate question validation

`QuestionValidator` rejects any candidate where:

- The correct answer is not **exactly one** option (zero or multiple defensible answers → ambiguous → rejected). E.g. "Who is the only player from Haifa?" is invalid if two players are from Haifa.
- Any distractor is accidentally also correct against the dataset.
- Options are not distinct after normalization (trim, case-fold).
- Option count is outside the allowed bounds (bounds deferred — see §9.3).
- The question references a player who has left the game.
- The question uses any non-consented field (defense in depth; the dataset should already prevent this).
- Text or options are empty/over length limits.

Validation is against the **actual dataset**, not the rule's intent: rules can be buggy; the validator is the safety net.

### 12.4 Candidate quality scoring (concept)

`QuestionQualityScorer` assigns each valid candidate a numeric score. Conceptual signals (weights to be tuned during implementation, not fixed here):

- **Coverage** — questions involving more of the group score higher than ones about a single value.
- **Surprise** — answers that are not trivially guessable (a 50/50 majority split beats a 10/1 split).
- **Distractor plausibility** — how close the distractors are to the correct answer's value space.
- **Player spotlight balance** — boost candidates featuring players not yet featured (evaluated with selection context).
- **Rule variety pressure** — mild penalty for rules that already produced many high-ranked candidates.

Scoring is a pure function of (candidate, dataset, selection-context); no IO.

### 12.5 Diversity and duplicate filtering (concept)

`QuestionSelector` picks the final N questions from ranked candidates under constraints:

- **Exact-duplicate elimination** — identical normalized question text/answers never both selected.
- **Near-duplicate prevention** — candidates that share the same (rule, field, subject-player) signature, or whose normalized texts are highly similar, are treated as one group; at most one is selected. Similarity is computed with simple deterministic techniques (normalized token overlap / signature keys) — **not** ML embeddings.
- **Rule diversity** — cap per rule type in one game (no game of 10 questions where 8 are "count" questions).
- **Field diversity** — spread questions across profile fields.
- **Player spotlight spread** — avoid the same player being the subject of many questions.
- **Ordering** — final sequence interleaves rule types; a light-to-personal progression is preferred.

Selection is deterministic given (candidates, seed).

---

## 13. REST / API Conventions

- Base path: `/api/v1/`. Version bumps only via §21.
- Resource-oriented, plural nouns: `/api/v1/rooms`, `/api/v1/rooms/{room_code}/players`.
- JSON everywhere; all JSON keys are `snake_case` (REST **and** WebSocket — the frontend maps to camelCase in its own layer if desired, but wire format is snake_case).
- Timestamps: ISO-8601 UTC with `Z` suffix. Ids: server-generated opaque strings (format deferred — see §8).
- Methods: `POST` create/commands, `GET` reads, `PATCH` partial updates, `DELETE` removal. No verbs in URLs — commands that don't map to a resource use a sub-resource action noun sparingly (avoid where the WS event already covers it).
- Success codes: `200` read/update, `201` create, `204` delete/no-content.
- Every response body is an object (never a bare array).
- Errors follow §17.
- REST is used for: room creation, room lookup, join, profile submission. Gameplay flow (start, next, answers) is WebSocket-only — one authoritative channel for realtime mutation, no dual paths. **Deferred — Room/gameplay design stage:** the single canonical transport for profile submission (this REST path vs. the `player.profile_submit` event, §14.2); until decided, the spec lists both.
- Request/response schemas are Pydantic models in `backend/app/api/`; mirrored TypeScript types live in `frontend/src/types/`.

---

## 14. Realtime (WebSocket) Conventions

### 14.1 Endpoint

`/ws/rooms/{room_code}?player_id=...`. The host's connection must be identifiable as the authorized host; **deferred:** the concrete host-authorization mechanism is chosen during backend/Room design (see §8) and is not yet a shared contract. One WebSocket per client.

### 14.2 Event naming

Event names are `snake_case` segments joined by a dot: `<domain>.<action>`, past tense for server→client facts, imperative for client→server intents.

**Client → Server (intents):**

| Event | Sender | Meaning |
|---|---|---|
| `player.join` | player | Announce/bind connection to a joined player |
| `player.profile_submit` | player | Submit profile fields |
| `player.ready` | player | Mark ready during profile collection |
| `game.start` | host | Start the game from `READY`: the backend generates the question set, then opens the first question |
| `answer.submit` | player | Submit an answer (payload: §9.4) |
| `game.next` | host | Advance the post-round flow (results → leaderboard → next question or finish) |

`LOBBY → PROFILE_COLLECTION` has no client trigger event: it happens automatically when the server accepts the first valid profile submission (§11), announced via `room.updated` (and the submitter's `player.updated`).

**Server → Client (facts):**

| Event | Meaning |
|---|---|
| `room.updated` | Room/game state snapshot changed (carries current state + players) |
| `player.joined` | A player joined |
| `player.updated` | A player changed (ready, connected, profile status) |
| `game.started` | The game started from `READY` (question set generated; first `question.started` follows) |
| `question.started` | A question opened (payload: §9.3, without correct answer) |
| `answer.accepted` | This client's answer was recorded (ack, sent only to the answerer) |
| `question.ended` | Question closed; payload includes correct option + statistics (§9.6) |
| `statistics.updated` | Aggregate stats refresh |
| `leaderboard.updated` | Leaderboard snapshot (§9.7) |
| `game.finished` | Terminal state; final leaderboard |
| `error` | Request-scoped error (format: §17) |

Renaming events or changing payloads is a shared-contract change (§21).

### 14.3 Message envelope

Every message in both directions is wrapped in the same envelope:

```jsonc
{
  "event": "question.started",     // event name, as above
  "payload": { },                  // event-specific body (contracts in §9)
  "timestamp": "2026-08-09T18:30:00.000Z",  // sender time, ISO-8601 UTC
  "game_id": "uuid"                // the game this message belongs to
}
```

- Unknown `event` values must be ignored by clients (forward compatibility) and answered with `error` (`UNKNOWN_EVENT`) by the server.
- The server may batch state into `room.updated` snapshots; clients must treat snapshots as authoritative over any locally-derived state.

---

## 15. Persistence Conventions

- SQLAlchemy 2.x, declarative models, all models in `backend/app/infrastructure/database/`.
- SQLite for MVP: single file, path from env (§16). Write code against the SQLAlchemy API without SQLite-only features, so a future move to another SQL database (e.g., PostgreSQL) stays feasible if ever needed.
- Access via the **repository pattern**: application code depends on repository interfaces (defined application-side); implementations live in `infrastructure/repositories/`. No SQLAlchemy sessions or models above the infrastructure layer.
- Tables: plural snake_case (`players`, `game_questions`). Columns: snake_case. PKs: opaque string ids generated by the domain, never by the database (id format deferred — see §8).
- Every table has `created_at`/`updated_at` (UTC).
- **Deferred:** migration tooling and strategy will be decided once the schema begins to stabilize; until then, schema changes must be called out in the PR description.
- Hot game state (the active question, in-flight answers) may be held in process memory for latency, but the database remains the durable record — process memory is a cache, never the long-term source of truth. **Deferred — backend implementation design:** exact persistence points and restart/recovery guarantees.
- Retention: see §10.5 — a cleanup routine purges profile data after the retention window (exact duration **deferred**; see §10.5).

---

## 16. Environment Variable Conventions

- All variables are prefixed `MIZEMI_`, UPPER_SNAKE case.
- Loaded once at startup into a typed Pydantic settings object (`pydantic-settings`); application code reads settings, never `os.environ` directly.
- A committed `.env.example` documents every variable with a safe default; real `.env` files are gitignored. No secrets in code or in the repo.

Initial set:

| Variable | Default | Purpose |
|---|---|---|
| `MIZEMI_ENV` | `development` | `development` \| `test` \| `production` |
| `MIZEMI_DATABASE_URL` | `sqlite:///./mizemi.db` | SQLAlchemy URL |
| `MIZEMI_HOST` | `127.0.0.1` | Bind address |
| `MIZEMI_PORT` | `8000` | Bind port |
| `MIZEMI_CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed origins |
| `MIZEMI_LOG_LEVEL` | `INFO` | Logging level |

(A retention-window variable will be added once the retention duration is decided — see §10.5.)

Frontend: Vite env vars prefixed `VITE_MIZEMI_` (e.g. `VITE_MIZEMI_API_BASE_URL`, `VITE_MIZEMI_WS_BASE_URL`).

---

## 17. Error Response Format

One error shape everywhere — REST bodies and the WS `error` event payload:

```jsonc
{
  "error": {
    "code": "ROOM_NOT_FOUND",        // stable UPPER_SNAKE machine code
    "message": "No room exists with code K7PW3N.",  // human-readable, safe to display
    "details": { "room_code": "K7PW3N" }            // optional structured context
  }
}
```

- REST: this body plus the appropriate HTTP status (`400` validation, `404` not found, `409` conflict/illegal state, `422` schema violation).
- WebSocket: the same object as the `payload` of an `error` envelope.
- Error codes are part of the shared contract. Initial registry: `ROOM_NOT_FOUND`, `ROOM_FULL`, `NAME_TAKEN`, `INVALID_STATE_TRANSITION`, `QUESTION_CLOSED`, `ALREADY_ANSWERED`, `NOT_HOST`, `VALIDATION_ERROR`, `UNKNOWN_EVENT`, `INTERNAL_ERROR`. Additions append to this list via a spec PR. `ROOM_FULL` and `ALREADY_ANSWERED` are **reserved** codes: the rules that trigger them (room capacity; answer finality) are deferred to the Room and gameplay design stages respectively.
- `message` must never contain another player's profile data or internal stack traces.

---

## 18. Naming Conventions

### 18.1 Python

- Modules/packages: `snake_case`. Classes: `PascalCase` (`QuestionGenerator`, `GameStateMachine`). Functions/methods/variables: `snake_case`. Constants: `UPPER_SNAKE`.
- Private members: single leading underscore.
- Abstract bases: plain descriptive names (`QuestionRule`), not `IQuestionRule`/`AbstractQuestionRule`.
- Full type hints on all public functions/methods; enable strict-ish checking as tooling is added.
- Enums for closed sets (game states, event names, error codes) — no magic strings in logic.
- **Deferred:** the formatter/linter toolchain will be chosen during dev-tooling setup; until then, follow the conventions above and match surrounding code.

### 18.2 TypeScript

- Files: `PascalCase.tsx` for components, `camelCase.ts` for everything else. Components/types/interfaces/enums: `PascalCase` (no `I` prefix). Variables/functions/hooks: `camelCase`; hooks start with `use`. Constants: `UPPER_SNAKE` only for true module-level constants.
- `strict: true`; no `any` except at guarded IO boundaries with a comment.
- Wire types (mirroring §9) live in `frontend/src/types/` and keep **snake_case** field names to match the wire exactly — no renaming layer in MVP.
- Prefer type aliases for data shapes; interfaces for extendable object contracts.

---

## 19. Testing Conventions

- Backend: `pytest`. Layout mirrors `app/`: `backend/tests/unit/` (pure domain/application, no IO, no network, no DB), `backend/tests/integration/` (FastAPI TestClient, WebSocket flows, real SQLite in temp file/memory), `backend/tests/fixtures/` (shared fixtures/factories, e.g. profile dataset builders).
- Test names: `test_<unit>_<behavior>[_<condition>]`, e.g. `test_uniqueness_rule_yields_nothing_when_no_unique_value`.
- Domain logic — especially the Question Generation Engine and the state machine — must be testable **without any IO**; engine tests pass a fixed seed and assert deterministic output.
- Every `QuestionRule` gets unit tests covering: produces expected candidates on a supporting dataset, produces **zero** candidates on a non-supporting dataset, and never uses non-consented fields.
- Every bug fix adds a regression test.
- Frontend unit tests use **Vitest**. React component tests use **React Testing Library** with **`jsdom`** as the DOM environment, **`@testing-library/user-event`** for user interactions, and **`@testing-library/jest-dom`** for DOM assertions.
- Frontend tests assert user-observable behavior rather than component implementation details. Pure TypeScript utilities are unit-tested without DOM or network IO; component tests cover rendering and user interaction at the smallest useful boundary.
- Frontend E2E testing uses **Playwright** and is **deferred** until the first stable backend-connected vertical slice exists. E2E tooling must not be added before that trigger is reached.
- Tests are contracts: **deleting or weakening a test to make a change pass is prohibited** (see §22). If a test is genuinely wrong, the PR must say so explicitly and explain why.
- Principle: automated tests must pass before a merge. **Deferred:** the CI system and its exact configuration.

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
