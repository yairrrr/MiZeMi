# MiZeMi

## Visit MiZeMi

- **Project / landing page:** [MiZeMi Project Page](https://yairrrr.github.io/MiZeMi/) — what the game is and how it works.
- **Live application:** [Play MiZeMi](https://mizemi-frontend.onrender.com) — create a room or join your group on Render.

The static project page lives in `docs/`. See [GitHub Pages setup](GITHUB_PAGES.md) for the manual publication steps. The multiplayer application continues to run on Render.

A working classroom icebreaker: the host creates a room, players join from phones, share consented profile facts, and play a live quiz through to a final leaderboard. By default, question generation is deterministic Python with no accounts, paid APIs or hosted realtime dependency. An **optional AI mode** (off unless the operator configures their own Anthropic key) lets a host have Claude write questions from the joined players' consented answers; see [AI question mode](#ai-question-mode-optional).

The offline knowledge engine understands films, songs, artists, foods, hobbies, music styles and towns using tens of thousands of compact local entries. A category-first stage turns the group's answers into shared facts — horror films, Italian food, sports hobbies, the north — and 18 discovery families ask about them (counts, majorities, comparisons, regions, cross-domain subgroups), alongside a small share of simple social questions. Explanations appear after each question. See [QUESTION_ENGINE_DIAGNOSTIC.md](QUESTION_ENGINE_DIAGNOSTIC.md) for how questions are chosen and [KNOWLEDGE_BASE_REPORT.md](KNOWLEDGE_BASE_REPORT.md) for measured coverage, sources and licenses.

## Source visibility and rights

MiZeMi is a source-visible portfolio project. No general open-source software license is granted. Except for separately licensed material, copyright remains with the respective rights holders; public visibility does not grant general permission to reuse, modify or redistribute the software, including commercially. GitHub's [Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) still permit viewing, forking and other uses through the platform, and applicable legal exceptions remain unaffected. Public access is not a technical restriction on copying. Request permission from the relevant rights holders for uses beyond those rights.

The reference datasets have separate permissions: Wikidata-derived data and the identified local reference adaptations use CC0; locality data contains information from GeoNames under CC BY 4.0, filtered, normalized and adapted by MiZeMi. Preserve the [data licenses and attribution](backend/app/data/knowledge/LICENSES.md) and [source manifest](backend/app/data/knowledge/manifest.json). This software notice does not restrict those data licenses or third-party dependency licenses. The MiZeMi logo and branding are separate from the reference-data dedication.

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

## AI question mode (optional)

When creating a room the host chooses **Classic** (default; offline knowledge engine) or **AI mode**. In AI mode, Claude writes the questions from the consented answers of the players who joined, so they are about *this* group. The toggle appears only if the server has AI enabled; otherwise MiZeMi behaves exactly as before.

Enable it locally by exporting the key in the terminal that starts the backend. Do not put it in a file you commit, in chat, or in any `VITE_` variable:

```sh
export MIZEMI_AI_ENABLED=true
export MIZEMI_ANTHROPIC_API_KEY=...   # your own key, typed only in your terminal
cd backend && ../.venv/bin/python -m app
```

What to know:
- Only fields a player allowed for question use are sent, without player ids and with exact age reduced to a range. The profile form and `/privacy` disclose this.
- Each AI question passes deterministic privacy/quality filters, the shared validator and an independent verification call. This reduces wrong answers but, unlike the algorithmic engine, cannot prove them.
- Generating 20 questions can take a few minutes. The server stays responsive and the host sees a progress message. Any AI failure falls back to Classic.
- A per-hour game limit (`MIZEMI_AI_MAX_GAMES_PER_HOUR`) and a provider-side spend limit on a dedicated key are recommended. Full contract: [MASTER_SPEC.md §12.7](MASTER_SPEC.md).

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

Playwright starts its own isolated backend and production frontend preview. It runs a 20-question English game and a 7-question Hebrew game with three mobile players, plus a 20-question Hebrew knowledge game with five mobile players. Scenarios cover a real timeout, scoring, semantic discoveries/explanations, privacy, no external requests, and reloads in multiple states. Ports 4173, 8765 and 8770 must be free. It also checks bilingual legal pages, keyboard-only game journeys, axe-core accessibility, 320px layouts, enlarged text and the local GitHub Pages presentation. The smoke test starts another disposable backend on port 8766 and uses 21 actual WebSockets.

The PostgreSQL integration tests run when `MIZEMI_TEST_POSTGRES_URL` points to a disposable PostgreSQL database whose role can create schemas. They create and remove unique schemas for English and Hebrew games; do not point them at production. Without that variable, the two live PostgreSQL cases are explicitly skipped; SQL dialect tests still run.

## Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) and [render.yaml](render.yaml) for the application deployment configuration. The live game uses Render, with Neon PostgreSQL for persistence. GitHub Pages serves only the separate project presentation in `docs/`.

Active games live in a single backend process. Refresh/network reconnect works while that process survives; a restart, redeploy or service sleep ends active rooms. Finished records become eligible for deletion seven days after their last save; bounded maintenance runs at startup and every five minutes while running. Outages or backlogs can delay deletion. Raw profiles are cleared at finish and are not written into new finished records; names, generated content (which can contain consented facts), answers and scores remain until cleanup. This is a classroom demo, with no horizontal scaling or durable active-game recovery.

[MASTER_SPEC.md](MASTER_SPEC.md) defines the architecture and contracts. [COMPLETION_REPORT.md](COMPLETION_REPORT.md) records the earlier recovery; [ENHANCEMENT_REPORT.md](ENHANCEMENT_REPORT.md) records the current enhancement and verification results.


## Bilingual games and Question Engine 2.0

Use the language selector on any screen to switch between English (LTR) and Hebrew (RTL). Your choice stays in this browser. Hosts independently choose the shared game language and 1–50 questions (default 20) when creating a room. Names and typed profile answers keep their original spelling; no translation service is called.

Knowledge-backed games use the category-first engine ([QUESTION_ENGINE_DIAGNOSTIC.md](QUESTION_ENGINE_DIAGNOSTIC.md), [QUESTION_STYLE_AUDIT.md](QUESTION_STYLE_AUDIT.md)); the original rules remain for knowledge-free generation. Questions progress from easy to medium to hard, balancing family, domain and participant variety. Consented facts are the only input; ambiguity, ties and redundant clues are rejected. Games can be shorter when too few valid questions exist, with an explicit notice. See [MASTER_SPEC.md](MASTER_SPEC.md) for contracts and [ENHANCEMENT_REPORT.md](ENHANCEMENT_REPORT.md) for the complete 29-rule catalog, verification and visual QA.


## Privacy and accessibility information

The game includes bilingual `/privacy`, `/terms` and `/accessibility` pages, a visible collection notice, and precise per-field question-use labels. Pages support direct language links (`?lang=he` / `?lang=en`). GitHub Pages links to the Render application’s authoritative copy. Legal routes do not join a room. Runtime dependency notices ship as `/THIRD_PARTY_NOTICES.txt`; reference data notices remain in [LICENSES.md](backend/app/data/knowledge/LICENSES.md).

The profile form checks `GET /api/v1/privacy-info` before allowing submission, so its retention/minimization statements match the backend. A matching backend release must precede offering the updated frontend. No deployment was performed as part of this implementation.

**Contact:** the public operator identification is `yairrrr`. [MiZeMi GitHub Issues](https://github.com/yairrrr/MiZeMi/issues) is the owner-approved route for an initial non-sensitive privacy/access/correction/deletion or accessibility message. Do not publish personal data, game identifiers or credentials there. It requires a GitHub account and repository access; the repository was private when checked on 19 September 2026. Confidential details and identity verification need a separately agreed private channel, not public Issues. No email or other private contact detail is published. Before broader use, make initial contact accessible to intended users and establish safe private follow-up where required. There is no account-based deletion portal. The fixed question timer and assistive-technology evaluation still need attention. See [LEGAL_IMPLEMENTATION_REPORT.md](LEGAL_IMPLEMENTATION_REPORT.md) and [LEGAL_READINESS_REPORT.md](LEGAL_READINESS_REPORT.md). These pages do not certify legal or accessibility compliance.
