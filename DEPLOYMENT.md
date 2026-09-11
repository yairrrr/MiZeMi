# Render + Neon deployment preparation

No account, service or deployment is created by this repository. The prepared target is one **Render Free web service**, one **free Render static site**, and **Neon PostgreSQL Free**. No Redis, broker, paid plan or runtime AI is needed.

## Neon

Create a Neon Free project near the backend's region. Copy the PostgreSQL connection URI from **Connect** and store it privately in the backend's `DATABASE_URL` environment variable. Keep `sslmode=require` (or stronger) and any `channel_binding=require` option supplied by Neon. Direct and pooled URLs are supported. Never put this URI in a Vite variable, committed file, URL query to this app, or screenshot.

Bare `postgres://` and `postgresql://` URLs automatically select SQLAlchemy's installed `psycopg` 3 driver. The engine uses pre-ping, a 300-second connection recycle, a ten-second connect timeout and a pool of two connections plus one overflow. A session owns each transaction; errors roll back when the session closes. SQL is generated/bound through SQLAlchemy.

## Backend service

| Setting | Value |
|---|---|
| Service type / runtime | Web service / Python |
| Plan | **Free** |
| Root directory | `backend` |
| Build | `python -m pip install --upgrade pip && python -m pip install -r requirements.txt` |
| Start | `python -m app` |
| Health check | `/api/v1/health` |
| Instances / workers | Exactly one instance, one Uvicorn worker |

Environment:

- `PYTHON_VERSION=3.14.7`
- `APP_ENV=production`
- `HOST=0.0.0.0`
- `PORT`: Render supplies this automatically; the entrypoint reads it.
- `DATABASE_URL`: private Neon connection URI with required TLS.
- `FRONTEND_ORIGIN`: exact frontend HTTPS origin, no path or trailing slash.
- Optional `MIZEMI_QUESTIONS_PER_GAME=10`, `MIZEMI_QUESTION_TIME_LIMIT_SECONDS=20`, `MIZEMI_MAX_PLAYERS_PER_ROOM=50`, `MIZEMI_ROOM_IDLE_TTL_MINUTES=120`, `MIZEMI_RETENTION_DAYS=7`, `MIZEMI_LOG_LEVEL=INFO`.

Existing `MIZEMI_ENV`, `MIZEMI_DATABASE_URL`, `MIZEMI_HOST`, `MIZEMI_PORT`, and `MIZEMI_CORS_ORIGINS` remain supported and take precedence over aliases. Avoid setting both forms. Production startup rejects SQLite, non-TLS database URLs, wildcard origins and non-HTTPS origins. Uvicorn handles WebSockets on the same port, with pings every 20 seconds and a 64 KiB transport frame cap. Tokens use WebSocket subprotocol headers and are never put in URLs. Access logs are disabled by the production entrypoint.

## Frontend static site

| Setting | Value |
|---|---|
| Service type | Static site (free) |
| Root directory | `frontend` |
| Build | `npm ci && npm run build` |
| Publish directory | `dist` |
| Node version | `26` |
| SPA rewrite | `/*` → `/index.html` |

Public build-time values:

- `VITE_API_BASE_URL=https://YOUR-BACKEND.onrender.com`
- `VITE_WS_BASE_URL=wss://YOUR-BACKEND.onrender.com`

Use origins only; the app appends `/api/v1` and `/ws/...`. Rebuild after changing these values. `VITE_MIZEMI_*` equivalents remain supported; the new names take precedence. Never include host/player tokens or DB credentials in Vite variables. The blueprint supplies static security headers; its CSP permits HTTPS/WSS connections because the backend hostname is chosen during setup. You may narrow `connect-src` to that hostname after setup.

## Schema and retention

Startup runs `Base.metadata.create_all` before the service becomes healthy. This is the explicit initial-schema strategy for the MVP: it creates missing tables, is idempotent, and does **not** alter existing tables. Seven tables store games, players, profile fields, generated questions/options, accepted answers and final scores. The completion change adds the `answers` and `scores` tables without altering earlier tables. Older game records have no historical scores/answers to backfill.

A fresh Neon database requires no manual SQL. The database role must be permitted to create tables. Future column changes require a versioned migration (add Alembic before such changes); `create_all` is not a schema migration engine. Back up existing retained data before a future migration.

Completed games are persisted at `FINISHED`; records can be read through the internal repository, with no public profile/history API. Maintenance runs at startup and every five minutes while the process is running. It deletes entire expired records, including questions that might reveal consented facts, answers and profiles. Default retention is seven days. Idle rooms with no sockets expire after two hours. A sleeping service performs overdue cleanup when it wakes. An interrupted active game cannot be restored after a process restart. Persistence failures log a safe message and do not crash gameplay; there is no durable retry queue.

## External steps remaining

1. Create the Neon project and obtain the private connection URI.
2. Connect this completed Git branch to Render (push/merge it to GitHub if needed; this task does not push).
3. Create the backend and frontend services using `render.yaml` or the settings above, selecting Free. Supply the four application values: `DATABASE_URL`, `FRONTEND_ORIGIN`, `VITE_API_BASE_URL`, `VITE_WS_BASE_URL`.
4. Deploy both services. The frontend/backend hostnames can be configured once Render assigns them. Rebuild the frontend after its public URLs are set.
5. Run the public smoke test: create a room, join three phones, complete profiles/readiness, finish a game, refresh during results, and verify a completed game reached Neon. Check the backend health endpoint and safe logs.

Render Free services can sleep after 15 minutes without inbound traffic and may take about a minute to wake. Their local files are ephemeral, which is why production rejects SQLite. Warm the backend by opening its health URL before class; do not redeploy during a game. No artificial keepalive service is provisioned. Keep usage within both providers' free quotas.

Provider references checked 2026-09-11: [Render Free](https://render.com/docs/free), [WebSockets](https://render.com/docs/websocket), [Blueprint fields](https://render.com/docs/blueprint-spec), [Python versions](https://render.com/docs/python-version), [Neon Python connection guide](https://neon.com/docs/guides/python).
