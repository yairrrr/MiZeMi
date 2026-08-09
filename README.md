# MiZeMi

MiZeMi ("מי זה מי" — "Who's Who") is a real-time multiplayer group icebreaker game, similar in interaction style to Kahoot. Players join a room from their phones, submit a short profile, and the app **algorithmically** generates quiz questions from the group's own answers — who's the only one from Haifa, how many picked pizza as their favorite food, whose hobby is rock climbing.

**No AI at runtime.** Question generation is purely rule-based and deterministic. The application uses no LLMs, ML APIs, or generative-AI services during gameplay.

**Zero cost.** The MVP must be developable, testable, deployable, and demonstrable without paying for any service — free and open-source software, and genuinely free service tiers only.

## Development Status

**Pre-implementation.** The shared engineering specification is in place; no application code has been built yet.

## Architecture Summary

- **Modular monolith** — one deployable backend, strict internal module boundaries across Presentation / Application / Domain / Infrastructure layers.
- **Backend:** Python, FastAPI, Pydantic, SQLAlchemy, SQLite (MVP), pytest. The backend is the single authoritative source of game state. Core logic is object-oriented Python.
- **Frontend:** React, TypeScript, Vite.
- **Communication:** REST for commands/resources; WebSockets for realtime gameplay events, with a common `{event, payload, timestamp, game_id}` envelope.
- **Question Generation Engine:** a pipeline of independent `QuestionRule` implementations producing candidates that are validated, quality-scored, and diversity-filtered — all deterministic.
- **Privacy:** no user accounts in the MVP; per-field `allow_question_usage` consent; ephemeral game data.

## For Contributors

**Read [MASTER_SPEC.md](MASTER_SPEC.md) before writing any code.** It defines the shared contracts (models, events, error format, state machine), folder structure, conventions, and the rules for changing any of them — including guardrails that bind AI coding agents working in this repo.
