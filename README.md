# MiZeMi

A working classroom icebreaker: the host creates a room, players join from phones, share consented profile facts, and play a live quiz through to a final leaderboard. Question generation is deterministic Python. No runtime AI, accounts, paid APIs, or hosted realtime dependency.

The offline knowledge engine understands films, songs, artists, foods, hobbies, music styles and towns using tens of thousands of compact local entries. Its 27 production rule families discover patterns about the group: shared tastes, counts, majorities, regions and cross-domain connections. Explanations appear after each question. See [KNOWLEDGE_BASE_REPORT.md](KNOWLEDGE_BASE_REPORT.md) for measured coverage, sources, licenses, the question-style audit and verification.

## Run locally

Prerequisites: Python 3.12+ and Node 22.12+ (verified with Python 3.14 and Node 26).

From the repository root:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r backend/requirements-dev.txt
npm --prefix frontend ci
```

Start the backend in one terminal:

```sh
cd backend
../.venv/bin/python -m app
```

Start the frontend in another:

```sh
cd frontend
npm run dev
```

Open http://localhost:5173. Create a room in the host tab, then open separate tabs or browsers for the players. Each tab keeps its own token in `sessionStorage`; refreshing restores that seat. Host credentials are separate from player credentials and never appear in the join link.

For phones on the same Wi-Fi, use the Network URL printed by Vite on **both** the host and phones. Set the backend's `FRONTEND_ORIGIN` to that exact origin, e.g. `http://192.168.1.10:5173,http://localhost:5173`, before starting it. Vite proxies both HTTP and WebSockets; only port 5173 needs to be reachable from the phones. Check the computer's firewall if needed.

## Play

1. The host shares the six-character room code or displayed join link.
2. Players may join until the host starts, even if earlier players already marked ready. Each supplies a unique display name and a profile. Every field has a consent checkbox; personal facts start opted out.
3. Players tap **I'm ready**. The host starts when all players are ready. The host can remove an abandoned seat before starting.
4. Answer each question once. The server closes it when all players answer or after 20 seconds, then shows the correct answer, an explanation for knowledge questions, anonymous distribution, and each player's own points.
5. The host shows the leaderboard, advances to the next question, and shows the final results after the last round.

Default: 20 requested questions, configurable from 1–50 when creating a room; correct answers earn 500–1,000 points based on server-measured speed, wrong/missing answers earn zero. Ties share ranks and retain join order. If consented data supports fewer questions, the game is shorter. If everyone withholds their data, no questions can be generated; create a new room if participants choose to share different facts.

## Verify

```sh
.venv/bin/python -m pytest backend/tests -q
npm --prefix frontend run type-check
npm --prefix frontend test
npm --prefix frontend run build
cd frontend
npx playwright install chromium
npm run test:e2e
cd ..
.venv/bin/python backend/tests/smoke_classroom.py
.venv/bin/python scripts/check_secrets.py
npm --prefix frontend audit --audit-level=low
.venv/bin/python -m pip_audit --progress-spinner off
.venv/bin/python -m pip check
```

Playwright starts its own isolated backend and production frontend preview. It runs a 20-question English game and a 7-question Hebrew game with three mobile players, plus a 20-question Hebrew knowledge game with five mobile players. Scenarios cover a real timeout, scoring, semantic discoveries/explanations, privacy, no external requests, and reloads in multiple states. Ports 4173 and 8765 must be free. The smoke test starts another disposable backend on port 8766 and uses 21 actual WebSockets.

The PostgreSQL integration tests run when `MIZEMI_TEST_POSTGRES_URL` points to a disposable PostgreSQL database whose role can create schemas. They create and remove unique schemas for English and Hebrew games; do not point them at production. Without that variable, the two live PostgreSQL cases are explicitly skipped; SQL dialect tests still run.

## Deploy later

See [DEPLOYMENT.md](DEPLOYMENT.md) and [render.yaml](render.yaml). No deployment has been performed. Production uses Neon PostgreSQL and one Render Free web service plus one free static site.

Active games live in a single backend process. Refresh/network reconnect works while that process survives; a restart, redeploy or service sleep ends active rooms. Completed game records are stored in the database and retained for seven days, then purged during maintenance. This is a classroom demo, with no horizontal scaling or durable active-game recovery.

[MASTER_SPEC.md](MASTER_SPEC.md) defines the architecture and contracts. [COMPLETION_REPORT.md](COMPLETION_REPORT.md) records the earlier recovery; [ENHANCEMENT_REPORT.md](ENHANCEMENT_REPORT.md) records the current enhancement and verification results.


## Bilingual games and Question Engine 2.0

Use the language selector on any screen to switch between English (LTR) and Hebrew (RTL). Your choice stays in this browser. Hosts independently choose the shared game language and 1–50 questions (default 20) when creating a room. Names and typed profile answers keep their original spelling; no translation service is called.

The original rules remain, joined by 26 new deterministic families. Questions progress from easy to medium to hard, balancing rule, field and participant variety. Consented facts are the only input; ambiguity, ties and redundant clues are rejected. Games can be shorter when too few valid questions exist, with an explicit notice. See [MASTER_SPEC.md](MASTER_SPEC.md) for contracts and [ENHANCEMENT_REPORT.md](ENHANCEMENT_REPORT.md) for the complete 29-rule catalog, verification and visual QA.
