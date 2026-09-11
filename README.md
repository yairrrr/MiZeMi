# MiZeMi

A working classroom icebreaker: the host creates a room, players join from phones, share consented profile facts, and play a live quiz through to a final leaderboard. Question generation is deterministic Python. No runtime AI, accounts, paid APIs, or hosted realtime dependency.

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
4. Answer each question once. The server closes it when all players answer or after 20 seconds, then shows the correct answer, anonymous distribution, and each player's own points.
5. The host shows the leaderboard, advances to the next question, and shows the final results after the last round.

Default: up to 10 generated questions; correct answers earn 500–1,000 points based on server-measured speed, wrong/missing answers earn zero. Ties share ranks and retain join order. If consented data supports fewer questions, the game is shorter. If everyone withholds their data, no questions can be generated; create a new room if participants choose to share different facts.

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
```

Playwright starts its own isolated backend and production frontend preview. The test runs a full 10-question game with one host and three mobile browser sessions, a real timeout, scoring checks, privacy checks, and reloads in multiple states. Ports 4173 and 8765 must be free. The smoke test starts another disposable backend on port 8766 and uses 21 actual WebSockets.

The PostgreSQL integration test runs when `MIZEMI_TEST_POSTGRES_URL` points to a disposable PostgreSQL database whose role can create schemas. It creates and removes a unique schema; do not point it at production. Without that variable, the live PostgreSQL test is explicitly skipped; SQL dialect tests still run.

## Deploy later

See [DEPLOYMENT.md](DEPLOYMENT.md) and [render.yaml](render.yaml). No deployment has been performed. Production uses Neon PostgreSQL and one Render Free web service plus one free static site.

Active games live in a single backend process. Refresh/network reconnect works while that process survives; a restart, redeploy or service sleep ends active rooms. Completed game records are stored in the database and retained for seven days, then purged during maintenance. This is a classroom demo, with no horizontal scaling or durable active-game recovery.

[MASTER_SPEC.md](MASTER_SPEC.md) defines the architecture and contracts. [COMPLETION_REPORT.md](COMPLETION_REPORT.md) records recovery and verification results.
