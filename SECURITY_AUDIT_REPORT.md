# MiZeMi final security and reliability audit

Date: 2026-09-14. Scope: committed `origin/main`, isolated security branch, local regressions, reachable history, read-only examination of the original worktree, and low-volume production checks. No push, merge, deployment, history rewrite, repository visibility change, Render configuration change or direct Neon operation was performed.

## 1. Executive summary

**PRODUCTION SECURITY PASS: BLOCKED**

**SAFE TO MAKE REPOSITORY PUBLIC**

The audited code fixes the CI crash mechanism and a reproducible WebSocket admission race. Full local regression passes. No exposed real credentials, authorization bypass, active-answer disclosure, consent derivation leak or executable text injection was found. Publication clearance applies to the audited repository/history and licensed committed assets; it is not a production release clearance or a guarantee against future secret commits.

The production verdict remains blocked because the release-blocking lifecycle fix has not run in GitHub on this branch or been released, and the live frontend lacks the frame/CSP/referrer restrictions already declared in the blueprint. Do not treat this report as evidence that production contains these local fixes. The scope explicitly prohibited pushing and deploying. An authorized release must follow the gates in §43.

## 2. Audited branch and SHA

- Branch: `codex/security-audit`.
- Worktree: `/private/tmp/mizemi-security-audit`.
- Baseline, fetched from origin: `95b92cbcf398cab340882627c1c7da0a01f99bbf`.
- Audited implementation/CI SHA: `0eeec2f1595018da431e4a5b2b826bda6db82be6`.
- This report is a subsequent documentation commit; use the branch's final HEAD when pushing.
- The original worktree was on `codex/group-intelligence`. It contained uncommitted Question Engine changes and the unrelated `frontend/package-lock.json` change. None was copied, staged, restored or modified. The lockfile's SHA-256 remained `5ce92a07171ded0100886b0ef3ffaacc27f51eefa6f55cea9850c8fa9e82411f`.
- No file under `backend/app/domain/questions/` changed on this branch. The parallel agent's ongoing Question Engine changes, including its later documentation/tests, are outside this implementation audit. Revalidate after integrating them.

## 3. Baseline test state

Fresh isolated installs used the committed dependency files. Local runtime: CPython 3.14.7, macOS ARM64, SQLite 3.53.4, PostgreSQL 17.11 in a disposable UTF-8 cluster on loopback port 55439. No real `.env` was loaded. Docker was unavailable; no equivalent Ubuntu VM was provisioned.

| Baseline check | Actual result |
|---|---|
| Full backend with local PostgreSQL | 1,139 passed; 2 deprecation warnings; 23.43 s |
| Frontend type-check | Exit 0 |
| Frontend unit tests | 300 passed in 12 files |
| Production build | Exit 0 |
| Multiplayer browser E2E | 3 passed; 43.4 s |
| Classroom smoke | 1 host, 20 players, 21 real WebSockets, 3 rounds; passed |

The warnings are Starlette's deprecated `httpx` TestClient support and AnyIO's BlockingPortal alias. They were not suppressed. Initial install/network attempts inside the sandbox failed; authorized temporary-environment retries succeeded. These were environment restrictions, not passing checks.

## 4. GitHub Actions segfault root cause

[Failed run 34784683337](https://github.com/yairrrr/MiZeMi/actions/runs/34784683337) failed at `Backend including PostgreSQL` with exit 139. Runner: Ubuntu 24.04, image `ubuntu24/20260907.300`, CPython 3.14.7, SQLAlchemy 2.0.51, psycopg/psycopg-binary 3.3.5, greenlet 3.5.5, PostgreSQL service 17.11.

The fatal trace identifies **SQLite**, despite the job's PostgreSQL name:

- `asyncio_0`: SQLAlchemy `do_execute` → repository `delete_older_than` → `_Database.purge_expired`.
- `asyncio-portal`: SQLAlchemy pool `dispose`/`do_close` → the app's lifespan shutdown.
- Main test: `test_game_configuration.py::test_count_is_strictly_validated_by_server`, exiting TestClient.
- Native stack: `_sqlite3.cpython-314-x86_64-linux-gnu.so`, not a psycopg or greenlet frame.

The lifespan cancelled the maintenance coroutine and immediately disposed its engine. Cancelling a waiter cannot stop already-running thread work. The shared in-memory SQLite connection could therefore close during a native query. The same connection also lacked whole-transaction serialization between retention and persistence. This was app shutdown, **not interpreter finalization**. Interpreter/executor cleanup occurs too late to make that premature disposal safe. Python's [Future cancellation contract](https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.Future.cancel) explains why a running worker continues; [SQLAlchemy's SQLite threading guidance](https://docs.sqlalchemy.org/en/20/dialects/sqlite.html#threading-pooling-behavior) is relevant to the shared connection.

Deterministic local instrumentation reproduced premature disposal for successful and failing retention workers: **2 failed before the fix, 2 passed after**. It records operation ordering without deliberately crashing the host. Exact native exit 139 was **not reproduced on macOS**; the GitHub trace plus deterministic ordering regression establish the defective lifecycle mechanism.

The same failing commit had a successful sibling run, and [baseline main run 34880284751](https://github.com/yairrrr/MiZeMi/actions/runs/34880284751) succeeded on Python 3.14. There is no evidence supporting a blanket Python downgrade or blaming loaded native modules merely for being present. Psycopg [documents Python 3.14 support](https://www.psycopg.org/psycopg3/docs/basic/install.html). Python, psycopg, SQLAlchemy and Render runtime pins remain unchanged.

## 5. CI remediation

Maintenance now stops cooperatively, finishes its current worker operation, and is awaited before persistence executor shutdown and engine disposal. An RLock serializes complete `_Database` write/retention transactions, including their schema check. Existing off-loop persistence and PostgreSQL coverage remain.

The workflow retains the full backend/PostgreSQL suite, frontend type-check/tests/build, Chromium E2E, classroom concurrency and dependency audits. It additionally enables fault-handler/unbuffered diagnostics, repeats the deterministic lifecycle suite five times, checks `pip check`, fetches full history and scans deleted/reachable content. A failing repeated test propagates its exit code. No retries hide failures, and no suite was removed or weakened.

Dedicated actionlint 1.7.12 validation passed; Render YAML parsed successfully. Actionlint's optional shellcheck integration was unavailable and explicitly disabled for that invocation; the shell commands themselves were executed locally. GitHub execution of the new SHA and Ubuntu x86-64 reproduction are **NOT EXECUTED**. Pushing to trigger CI was not authorized.

## 6. Findings by severity

No CRITICAL finding or active credential exposure was found.

| ID / severity | Impact | Evidence | Fix / status | Verification |
|---|---|---|---|---|
| H1 HIGH, reliability / release blocker | Native crash while shutting down; a green local run alone cannot establish reliability | CI concurrent SQLite execution/disposal stacks; two deterministic failures before remediation | Join maintenance before disposal; serialize transactions. Fixed locally; rollout/remote CI pending | 1,201-test full suite; five repeated 5-test lifecycle runs; failing-worker and unavailable-DB cases |
| M1 MEDIUM | Authenticated clients bypass four-socket cap with concurrent handshakes, increasing resource exhaustion risk | Eight simultaneous upgrades admitted eight sockets for both roles before fix | Reserve a per-role/per-player slot before `accept` yields; release on failure/disconnect. Fixed locally | Both reproductions fail before and pass after; failed-handshake slot cleanup; classroom/E2E |
| M2 MEDIUM | Visually indistinguishable/control-laden names can confuse classroom identity; formatting controls propagate into generated text | Zero-width/bidi names accepted at baseline; canonical-equivalent names used different duplicate keys | Reject nonprintable name/profile text; NFC/collapsed-whitespace/casefold comparison for duplicate names. Fixed locally | New adversarial names/profiles; legitimate mixed Hebrew/English and Hebrew marks; full regressions |
| M3 MEDIUM, deployed configuration | Frontend can be framed; missing defense in depth against injected scripts/referrer leakage | Live HTML lacks CSP, X-Frame-Options and Referrer-Policy although `render.yaml` declares them | No direct Render change permitted. Apply the existing restrictions in a separately authorized release | Live headers inspected; existing blueprint CSP tested against built assets in Chromium, with mocked HTTPS/WSS; zero CSP violations |
| L1 LOW | Large retention backlog loads every expired aggregate; query does not explicitly exclude active records | Unbounded `.all()` on expiry query; runtime currently persists only finished games | Limit to 100 oldest FINISHED records per transaction. Fixed locally | 101 expired records removed in 100+1 batches; active and recent records retained; PG/SQLite cascades |
| L2 LOW | Malformed production origins/URLs allow broken unsafe configuration to reach startup | Wildcard hostname, userinfo and malformed-port origin cases | Restrict DB dialect/host/database and validate exact HTTPS origin structure; safe error text. Fixed locally | Invalid-origin corpus, DB TLS requirements and startup tests |
| L3 LOW | A huge numeric Content-Length produces integer-conversion error rather than bounded rejection; attacker-supplied paths could enter unexpected-error logs | 5,000-digit header; prior path logging | Bound before integer conversion; remove request path from unexpected-error log. Fixed locally | Header now returns 413; source review and safe-error regression |
| L4 LOW, deployed configuration | Missing API HSTS and Permissions-Policy on both services reduce defense in depth | Actual response headers | Reported; no header blindly added. HTTPS/WSS URLs and HTTP redirects already enforced by deployed architecture | HTTP→HTTPS 301; browser no insecure requests; API/WSS valid TLS |

The HIGH finding is a demonstrated release reliability failure, not an assertion that PostgreSQL credentials or player authorization were compromised. The active-record clause in L1 is an additional safety boundary; no evidence showed production persisting active games or deleting them.

## 7. Current-tree secret scan

The existing scanner, independent byte-pattern searches, names-only `rg` inventory and Gitleaks 8.30.1 were run. Coverage included tracked/untracked files, documentation/reports, JSON/YAML, scripts, tests, both worktrees, ignored SQLite files, browser artifacts and production build output. Installed environments/dependencies and Git internals are excluded from source scans; dependencies are audited separately. The scanner now includes `dist`, binary printable content and previously size-skipped artifacts, without printing matches.

No real credential matches and no real `.env` files were found. A names-only sensitive-field inventory located 45 tracked files for review; examples/tests use placeholders or synthetic tokens. No tracked database, private-key, log, node_modules, dist or browser test-result artifact was present. Gitleaks current-tree and original-worktree scans both reported no leaks. Detectors cannot recognize every arbitrary custom secret; this is evidence from multiple scans and source review, not an absolute guarantee.

## 8. Git-history secret scan

The baseline reachable graph contained 123 commits and 525 unique blobs. An independent `rev-list --objects --all` / `cat-file --batch` scan examined every blob, including deleted files, and found no credential matches. The maintained scanner now has `--history`, refuses shallow history, scans all reachable blobs and reports introduction commits without values. A temporary-repository regression proves it catches a deleted synthetic token and reports its introducing commit, not its deletion.

Gitleaks independently scanned all reachable history with `--log-opts=--all --redact=100` and found no leaks. Its commit count reflects patch-bearing commits and differs from the full graph count; the full-blob scan covers merge/snapshot content as well. Both scans were rerun after the implementation commits. The other agent may advance additional reachable refs during work; findings remain tied to the scans performed. Unreachable/dangling objects, GitHub caches, forks and private deployment logs were not inspected. No credential rotation or history cleanup is indicated by the findings. No history was rewritten.

## 9. Public repository readiness

**SAFE TO MAKE REPOSITORY PUBLIC** for the audited content and reachable history. Do not change visibility as part of this task.

Environment examples contain placeholders; database/build/browser artifacts are ignored. The original `backend/mizemi.db` has zero game/player/profile/answer rows. Its ignored `frontend/.e2e.db` has three games and eleven players: every display name and profile value matches committed synthetic E2E fixtures. Neither file was changed. No sensitive local participant database was identified. Publish through Git, not by uploading a whole working-directory archive. Preserve knowledge attribution notices and UI credits. The application has no general open-source license grant; selecting a software license is an owner decision, separate from the verified knowledge-data redistribution terms.

## 10. Frontend secret exposure

The final build used the actual public HTTPS/WSS backend URLs plus dummy unprefixed server-secret canaries. All four output files were inspected: no canary, DATABASE_URL, Neon host, private key, GitHub credential marker or localhost network URL appeared. The deployed JS likewise contains the expected public HTTPS/WSS URLs and no searched private-configuration markers. VITE variables are browser-public; the two documented public URL variables and their legacy URL aliases are the only referenced Vite configuration. Host/player tokens arrive at runtime only to their respective creators.

## 11. HTTPS / WSS

Both production sites returned HTTPS 200; HTTP requests redirected with 301 to HTTPS. Real WSS connections succeeded using the correct origin and valid credentials. Certificate verification was enabled. Live Chromium loaded the frontend/logo with zero page errors and zero HTTP/WS requests. No mixed content, localhost production address or downgrade was observed.

## 12. CORS

For `https://mizemi-frontend.onrender.com`, health GET and POST preflight returned the exact Access-Control-Allow-Origin. Malicious and localhost GET requests returned the public health response without ACAO; their preflights returned 400. Missing-Origin health returned 200 without ACAO. `allow_credentials=False`; no cookie authentication. CORS is a browser response-reading policy, not authorization or a prohibition on nonbrowser access to intentionally public endpoints.

## 13. WebSocket Origin

Origin was tested separately from HTTP CORS for both host/player routes with **valid credentials**. Correct origin: 101. Malicious and localhost origins: 403. Missing origin: 101 by documented nonbrowser policy, still requiring the token. Invalid credentials with correct origin: 403. Local tests additionally reject literal `Origin: null`. The response subprotocol contains only the role, never the credential. Browsers send an Origin and cannot omit it through normal WebSocket JavaScript.

## 14. Host authorization

A player cannot start, advance or remove another player. Host commands require a host connection and exact payload schemas. Player/missing/wrong/cross-room host credentials fail. Credentials use `secrets.token_urlsafe(32)` (256 random bits), separate from the room code. Only SHA-256 digests remain in memory; `hmac.compare_digest` checks them. No plaintext credentials are persisted in the DB. They are absent from snapshots, results, logs and public errors. No JWT or encryption architecture was introduced.

## 15. Player authorization

The server binds a connection to its verified player ID/token. Another player's token cannot reconnect as that identity. Profile IDs must match; readiness accepts only an empty payload; answers accept only question/option IDs. Tests reject injected player identity, score, correctness and answer time. Removed-player credentials are revoked. Names remain display labels, never authorization identifiers.

## 16. Room security

Room codes are shareable admission information, not host credentials. Room creation/join are intentionally public. Joining closes after gameplay starts; capacity and duplicate names are enforced. No REST room-list/snapshot/history endpoint exists. Invalid-room requests expose no profile/game state. Up to 100 rooms and 50 players per room by default; idle rooms with no sockets expire after two hours. Open admission permits nuisance joins by someone who knows a room code; the host can remove participants before start. No stronger classroom roster authentication is claimed.

## 17. Correct-answer confidentiality

Every `correct_option_id` occurrence in backend/frontend was reviewed. Active payloads use `PublicQuestionSchema`, which cannot serialize the answer key. `room.updated` has no question object; active statistics contain counts only; acknowledgement reveals only the player's own selection. Reconnect reuses the same active public question/deadline and private acknowledgement, with no answer key. The key exists internally for scoring/persistence and is exposed through results only after closure. Frontend types/rendering consume it only in results. No public REST read path exposes repository records.

## 18. Answer integrity

Early, late, duplicate, invalid-option, wrong-question and malformed submissions are rejected. Extra identity/time/score/correctness properties are rejected. The service supplies receipt time, validates state/deadline/options, and accepts one answer per player/question. Client envelope timestamps are not used to determine score or deadlines.

## 19. Timer / race safety

Room mutations, final-answer closure and deadline closure run under the same room RLock. Closing checks current state/question and cancels the timer. Tests exercise real timeout, partial timeout, close twice, simultaneous answer bursts and a barrier-driven duplicate-final-answer versus timeout race. Only one closure/score application occurs; repeat close returns false. Maintenance and persistence now join safely before disposing DB resources. The five-repeat CI check deliberately propagates failures.

## 20. Scoring integrity

Correctness, time bonus and totals are calculated server-side. Tests confirm score remains within the single-round maximum, duplicate submissions cannot increase it, rejected/late submissions add nothing, and state cannot rescore after closure. Finished-game writes use whole-tree transactions; PostgreSQL tests verify idempotent upsert, answers/scores and rollback in both languages. Persistence failure leaves authoritative in-memory final scores unchanged and no partial committed tree.

## 21. Input validation

Backend schemas forbid unexpected properties, strictly type consent/int values, bound fields/options/counts and reject unsupported languages/music enums. API and realtime malformed JSON/type/null/empty/large/negative/control input cases were exercised. HTTP raw body cap is 16,384 bytes, including chunked bodies; WS application cap is 16,384 characters inside a 65,536-byte transport frame cap. Huge Content-Length fails with 413 before integer conversion. Names retain valid Hebrew/English/combining marks; nonprintable controls are rejected. Duplicate comparisons normalize canonical equivalence and whitespace. General cross-script visual homoglyph detection is not claimed; private identity still depends on tokens.

## 22. XSS

No production `dangerouslySetInnerHTML`, `innerHTML`, `document.write`, `eval` or `new Function` rendering path was found. Fifty new React tests cover both roles through ready/active/results/leaderboard/finished with script, image-onerror, SVG-onload, mixed Hebrew/English/bidi and long text payloads. They assert no executable nodes/handlers are created. Existing tests cover escaped knowledge explanations, forms and language boundaries. Text is rendered through React text nodes and bidi isolation, not interpreted as markup. Backend length rules reject oversized names even though renderer tests deliberately bypass the backend to verify defense in depth.

## 23. SQL / database security

Production data access uses SQLAlchemy expressions/ORM bindings. No user-controlled SQL interpolation or raw SQL execution path was found. Sessions own transactions and close/rollback on error; SQLAlchemy hides parameters. Test schema names are generated UUIDs and use SQLAlchemy DDL objects. Production filesystem DB paths derive from operator configuration, never room/player fields. Startup failure is generic. A local non-listening PostgreSQL port fails safely; failure injected after flushing a complete game tree leaves zero rows committed and preserves in-memory scores.

## 24. Neon credential safety

DATABASE_URL is backend-only, excluded from Settings repr, absent from builds/responses/log excerpts. Production startup requires PostgreSQL and `sslmode=require`, `verify-ca` or `verify-full`. Engine uses pre-ping, recycle=300 s, pool size 2 plus one overflow and a ten-second connection timeout. Stronger certificate verification remains advisable when configuring a connection. The real Neon URL/TLS settings, roles, backups and provider retention were **NOT READ / NOT MODIFIED**. This audit validates application requirements and failure behavior, not live account configuration.

## 25. Persistence / privacy / retention

Only terminal games are written by runtime. Finished records include raw profiles and their consent flags, questions, answers and scores; they are internal and not publicly queryable. Consent for question use is not a promise never to store a submitted field. Default retention is seven days, checked at startup and every five minutes while awake, now at most 100 expired FINISHED aggregates per run. Entire child trees cascade; active and recent records survive. Cleanup can lag during sleep/DB failure or a backlog. Connected rooms can retain in-memory data beyond seven days until they disconnect and reach idle expiry. There is no strict wall-clock erasure guarantee or provider-backup erasure verification.

## 26. Consent boundary

ProfileDataset copies only consented fields and retains no raw Player/profile reference. The Knowledge Engine derives categories, aliases, counts, distractors, explanations and cross-domain reasoning only from that dataset. Mutation-versus-omission tests cover movie, song, artist, music, food, hobby and city; they compare complete generated questions and raw candidates. Withheld Saw/horror is excluded. Withheld values cannot become semantic categories or influence a scored answer. Existing full tests passed; a focused knowledge/privacy selection separately passed 68 tests. The generation behavior was not changed.

## 27. Knowledge Engine security

The validated offline bundle contains 33,831 entities, version `2026-09-14.1`. Fixed filenames, no symlinks, aggregate byte/entity budgets, duplicate-key checks, schema/type/hash validation, source/license/date checks and bounded metadata guard loading. Corruption/NaN/bad provenance tests fail closed. Runtime reads no network, performs no eval/exec/unsafe deserialization, dynamically imports no data-specified module and accepts no player-controlled path. Build scripts are development-only; production only loads committed assets. Format controls are rejected at input, and bounded parser/normalization expressions show no obvious catastrophic backtracking path.

## 28. Knowledge licensing / supply chain

Committed structured Wikidata facts are CC0; [Wikidata's primary licensing policy](https://www.wikidata.org/wiki/Wikidata:Licensing) confirms structured-data terms. Locality data uses CC BY 4.0, confirmed by the [GeoNames distribution notice](https://download.geonames.org/export/dump/readme.txt). Repository LICENSES.md, manifest and accessible frontend credits provide attribution and adaptation notices. No plots, lyrics, descriptions, posters or raw source dumps are committed.

Scripts require explicit development fetch/refresh, use fixed public sources and transform JSON/tabular facts; the GeoNames ZIP reads one named member with compressed/uncompressed bounds, never `extractall`. Runtime neither fetches nor auto-updates. Compromised data can still be factually wrong, but does not become executable code; manifest hashes detect corruption, not trusted-source vandalism. Source revisions/queries, curation and dates are documented. No government/MusicBrainz data with unclear or incompatible terms was imported according to code/provenance review. Re-fetching remote datasets was not necessary and was not performed.

## 29. False-attribution review

Style preferences never imply a specific artist/playlist/personality; songs use their own genre facts. Unknown unique identity remains unknown. Normalized alias collisions, remakes and spelling collisions fail closed for identity; only categories shared by every contender may inform category claims under the explicit current contract. Unknown answers do not become negative memberships. Tests cover genre/artist separation, collision/unknown behavior and unsupported stereotype/diet claims. Community taxonomy correctness is not exhaustively provable across all 33,831 entities and remains an informational maintenance risk.

## 30. Logging / error disclosure

API validation errors do not echo input; unexpected responses are generic. Production disables access logs; WS credentials travel in subprotocol headers rather than URL queries and are not echoed. Application logs contain safe event/failure labels, not Authorization headers, token values, profile payloads, SQL parameters or DB URLs. Unexpected-error logs now omit attacker-controlled paths. Live malformed requests/404/docs/schema showed no searched traceback/filesystem/SQLAlchemy/Neon markers. Production private logs were not accessed.

## 31. Rate / resource protections

Local tests exercise room/join spam, spoofed X-Forwarded-For/X-Real-IP, invalid auth, message floods, body/frame limits, bounded slow-writer queues and socket capacity. HTTP allows 240 POSTs/minute per ASGI client address with at most 2,048 tracked buckets; health stays accessible. WS allows 120 messages/10 s per connection, at most four sockets per authenticated identity/role (including pending upgrades after the fix), queue length 256 and five-second send timeout. Rooms/timers/credentials are swept; close/failure paths release admission slots.

The HTTP guard itself ignores forwarded headers. Uvicorn 0.52.1 trusts loopback by default or operator-configured `FORWARDED_ALLOW_IPS`; it resolves trusted proxy chains from the right. Actual Render proxy/env configuration was not read. Do not set trust to `*` without a verified edge sanitation boundary. If all clients appear as one proxy, NAT-safe limits may become shared and restrictive. No aggressive production load testing occurred.

Limits are MVP safeguards, not DoS immunity: public room admission can fill the room quota, connected rooms persist, there is no global pre-auth socket rate limiter, and the persistence executor has no separately configured queue cap/durable retry. Slow database queries have no application statement deadline, so orderly shutdown can wait for native work; do not force-close its connection to make the crash disappear.

## 32. Reconnect / multi-socket

Local tests/E2E cover lobby, READY, active before/after answer, results, leaderboard and FINISHED for appropriate roles. Replay preserves deadline, active answer confidentiality and own accepted answer; later snapshots restore results. Multiple player sockets retain connected status until the last closes and cannot duplicate scores. Admission failures/disconnects release slots. Process restart loses active rooms and credentials by design; reconnect is not durable recovery.

## 33. HTTP security headers

Live frontend: nosniff and HSTS (`max-age=315360000; includeSubdomains; preload`) present; public static caching with edge TTL 300 s; CSP, Referrer-Policy, Permissions-Policy and X-Frame-Options absent. Live API: no-store, nosniff, no-referrer and DENY present on tested application responses; HSTS/CSP/Permissions-Policy absent. CORS preflights are produced outside the application guard and do not carry those guard headers; they contain no session data.

No header configuration was changed on this branch. Existing blueprint CSP permits self Vite JS/CSS/logo assets and HTTPS/WSS API connections; it blocks objects and third-party framing. Chromium verified built JS/logo and mocked HTTPS API/WSS under that exact policy with zero violations. This is a local CSP compatibility test, not proof that Render serves the policy or an end-to-end TLS proxy test. `connect-src` remains broad HTTPS/WSS for configurable deployment hosts; narrow it when applying verified production settings. No external fonts are required.

## 34. Browser storage / CSRF / clickjacking

Host/player credentials, room/game/player IDs and the player's display name use sessionStorage for tab-scoped reconnect. Explicit leave/back-to-start clears it; tab closure expires it. localStorage stores UI language only. Finished-game credentials may remain until the user leaves/closes the tab; they expire server-side with room lifetime. XSS could read sessionStorage: it is not a secure enclave. No raw profiles are stored there.

There is no ambient cookie-authenticated action, so classic cookie CSRF middleware is not applicable. Bearer possession and WS origin checks govern private actions. Cross-origin requests can still invoke intentionally public room admission, subject to resource limits. No documented third-party embed use exists; the existing frame-ancestors/DENY intent is appropriate. The live frontend drift should be corrected in the authorized release.

## 35. API inventory

Enumerated from `app.openapi()` and the registered WS routers; FastAPI's lazy included-router entries require this rather than assuming every top-level route object has a path.

| Method / path | Classification | Assessment |
|---|---|---|
| GET `/api/v1/health` | PUBLIC | Static status only; does not test current DB connectivity |
| POST `/api/v1/rooms` | PUBLIC | Issues a private host token only in the creator response |
| POST `/api/v1/rooms/{room_code}/players` | PUBLIC | Open admission; issues only the new player's credential |
| WS `/ws/rooms/{room_code}?player_id=…` | PLAYER | Token, origin, identity, state and message gates |
| WS `/ws/rooms/{room_code}/host` | HOST | Separate host credential; host-only commands |
| GET/HEAD `/docs`, `/redoc`, `/openapi.json`, `/docs/oauth2-redirect` | PUBLIC | Framework documentation/schema; no private records; no OAuth credentials configured |
| Finished-game repository / maintenance | INTERNAL | No public route |

No debug/admin/test or public history/profile/snapshot route was found. Keeping OpenAPI is reasonable for this small API; disabling docs would not secure the public routes. The external docs UI dependency is unnecessary for player flows but is not a reason to redesign authorization.

## 36. Dependency audits

`npm audit --audit-level=low`: zero vulnerabilities. `pip-audit`: no known vulnerabilities, including a final audit with greenlet 3.5.5 installed. `pip check`: no broken requirements. Direct dependencies/lockfile were not upgraded. psycopg/binary 3.3.5, SQLAlchemy 2.0.51 and CPython 3.14.7 match the failed runner; greenlet was explicitly added to the isolated ARM test environment because SQLAlchemy's platform marker did not initially install it there. Full regression then passed with that native version loaded. Linux wheel/OS differences remain a reason to require the new GitHub run, not evidence of an upstream compatibility defect. Vulnerability databases are time-specific and transitive Python dependencies are not fully locked; rerun audits when releasing.

## 37. Production black-box results

Only the two specified hosts were tested. One audit room and one synthetic player were created for valid-credential origin tests; no profile was submitted, no game started, and no finished record written. All sockets closed. The disconnected room follows normal idle cleanup. 31 recorded checks cover frontend/build, redirects, CORS/preflights, malformed requests, unauthorized routes, docs/schema, safe creation/join, and ten WSS handshake outcomes. A separate Chromium page-load check did not create another room. No brute force, flood, load test, direct DB query or provider modification occurred.

## 38. Classroom concurrency

Both baseline and final real-TCP smoke runs completed 1 host + 20 players, 21 simultaneous WebSockets and three rounds. Concurrent joins/connections/answer bursts produced identical room broadcasts, result counts and final leaderboards; sockets disconnected cleanly. Final runtime was 0.22 s after server startup. No crash or deadlock observed. This is a classroom functional smoke test, not a sustained multi-class capacity certification.

## 39. Full regression — exact matrix

Commands below run from the audit worktree unless noted. PostgreSQL commands used `MIZEMI_TEST_POSTGRES_URL=postgresql://postgres@127.0.0.1:55439/mizemi_test`, a disposable passwordless loopback test instance. CI uses its own service on localhost:5432. The pytest command is unchanged apart from that environment value. Results marked as part of the full suite were actually executed within it.

| CHECK | COMMAND / METHOD | RESULT |
|---|---|---|
| Backend full suite | `.venv/bin/python -m pytest backend/tests -q` with PostgreSQL and fault-handler env | **1,201 passed**, 2 warnings, 27.87 s; final native versions |
| PostgreSQL integration | `.venv/bin/python -m pytest backend/tests/integration/test_postgres.py -q` with test URL | **3 passed**: DDL plus English/Hebrew real PG persistence/rollback/retention |
| CI shutdown repetition | Five iterations of `.venv/bin/python -X faulthandler -m pytest backend/tests/integration/test_database_lifecycle.py -q` | **5 passed per iteration**; all five runs exit 0 |
| Frontend unit tests | `npm --prefix frontend test` | **350 passed**, 13 files |
| Frontend type-check | `npm --prefix frontend run type-check` | PASS, exit 0 |
| Frontend production build | `npm run build` in frontend, public Render URLs and dummy unprefixed private canary env | PASS; four output files inspected |
| E2E | `npm run test:e2e` in frontend | **3 passed**, 42.7 s; English, Hebrew, knowledge scenario |
| Classroom concurrency | `.venv/bin/python backend/tests/smoke_classroom.py` | PASS, 21 real sockets / 3 rounds |
| Host authorization | Full suite: `test_game_flow_hardening.py::TestAuthorization` and host command tests | PASS |
| Player impersonation | Full suite: player websocket/profile tests; `test_final_security_audit.py` | PASS |
| Correct-answer leakage | Full suite: active broadcast and answered-reconnect confidentiality | PASS |
| Duplicate-answer race | Full suite: barrier-driven test in `test_final_security_audit.py` | PASS |
| Timeout race | Same barrier test, `TestQuestionClosing`, real deadline cases | PASS; repeat closure no score change |
| Reconnect | Full suite state matrix + 3 browser E2E scenarios | PASS |
| Multi-socket | Player connection tests; `test_socket_admission.py` concurrent/failure tests | PASS; 4 per identity, correct connected status |
| XSS | `npm test`, including `SecurityRendering.test.tsx` | PASS; 50 new malicious/bidi/long-text rendering cases |
| SQL review | ORM/raw-SQL source search; PG transaction tests; flushed-write failure regression | REVIEWED / PASS for executed rollback checks |
| Database unavailable/failure | `test_database_lifecycle.py` and `test_final_security_audit.py` in full suite | PASS; safe startup error, zero partial rows, scores unchanged |
| Consent / Knowledge derivation | Full suite plus focused `pytest` on knowledge/group/category files with `-k 'consent or withheld or collision or unknown or stereotype or genre_does_not or corrupt or no_network or invalid_provenance'` | **68 passed** focused; full suite also passed |
| Offline assets | `.venv/bin/python scripts/build_knowledge_base.py` | PASS; 33,831 entities validated; no fetch |
| Input / Unicode / headers | New adversarial API tests + existing schema/security tests in full suite | PASS |
| Current-tree secrets | `.venv/bin/python scripts/check_secrets.py`; redacted Gitleaks dir; independent scans | No findings; both worktrees, build and artifacts included |
| Git-history secrets | `.venv/bin/python scripts/check_secrets.py --history`; redacted `gitleaks git . --log-opts=--all`; independent full-blob scan | No findings; rerun after implementation commits |
| npm audit | `npm --prefix frontend audit --audit-level=low` | Zero vulnerabilities |
| pip-audit | `.venv/bin/python -m pip_audit --progress-spinner off` | No known vulnerabilities |
| pip check | `.venv/bin/python -m pip check` | No broken requirements |
| Production CORS | Low-volume GET/preflight origin matrix | Expected exact-origin/missing/evil/localhost outcomes |
| Production WS Origin | Real WSS for both roles with valid token and varied Origin | Correct/missing 101; malicious/localhost 403; invalid auth 403 |
| Production security headers | Actual HTTP header inspection | EXECUTED; frontend drift/API HSTS gaps, §33 |
| Production information disclosure | Malformed JSON/types, unauthorized read paths, 404, docs/schema | No searched sensitive markers observed |
| Browser / CSP compatibility | Chromium live load; local production build under existing CSP with mocked HTTPS/WSS | PASS; logo/script/API/WSS; zero unexpected CSP violations |
| CI configuration validation | `actionlint 1.7.12 -shellcheck='' .github/workflows/verify.yml`; Ruby YAML parse of render.yaml | PASS; optional ShellCheck NOT EXECUTED (not installed) |
| Git whitespace | `git diff --check` and staged diff checks | PASS |
| New GitHub run | Push new SHA and observe workflow | **NOT EXECUTED**: no push authorization |
| Ubuntu x86-64 execution | Equivalent Linux runner | **NOT EXECUTED**: Docker daemon unavailable; no VM provisioned |
| Actual Neon account/TLS/retention settings | Provider inspection | **NOT EXECUTED**: direct provider access out of scope |
| Production load / completed-game persistence | Stress or finish a real production game | **NOT EXECUTED**: prohibited stress; no production DB write needed for low-volume checks |

Pre-fix failures were retained as evidence: lifecycle ordering 2 failures, socket cap 2 failures. During test authoring a surrogate was correctly rejected earlier by Pydantic (422 rather than 400), and a new scanner test exposed deletion-versus-introduction commit attribution; both expectations/implementation were corrected. The final full results above supersede those intermediate runs, without hiding them.

## 40. Exact fixes made

- `backend/app/main.py`: cooperative maintenance stop/join, whole-transaction RLock, safe production URL/origin validation, safe unexpected-error log.
- `backend/app/realtime/connections.py`, `host_connection.py`, `player_connection.py`: reserve socket slots before yielding and release on all tested failure/disconnect paths.
- `backend/app/application/join_player.py`, `profile_rules.py`: visible text checks and canonical duplicate-name comparison; no generation/rule modification.
- `backend/app/api/guards.py`: bounded Content-Length parsing.
- `backend/app/infrastructure/repositories/game_repository.py`: bounded FINISHED-only retention batches.
- `.github/workflows/verify.yml`: full-history checkout/scan, repeated shutdown checks, diagnostics and pip check; all existing verification retained.
- `scripts/check_secrets.py`: build/artifact and full reachable history coverage, value suppression and correct introducing-commit attribution.
- Four new backend security/lifecycle/scanner test modules and one frontend hostile-rendering test module.
- No package-lock, dependency pin, runtime pin, Question Engine asset/rule, Render blueprint or Neon setting changed.

## 41. Commits created

1. `2ed96df` — `fix(security): close database and socket admission races`.
2. `0eeec2f` — `ci: verify shutdown ordering and scan full reachable history`.
3. The subsequent report-only commit contains this document; the final task response identifies that HEAD for pushing.

All commits are local on `codex/security-audit`; exact paths were staged. No unrelated work was staged. The branch's final Git status is checked separately after committing the report.

## 42. Remaining risks

Release blockers: verify the new commit on GitHub and subsequently validate an authorized rollout; address the observed frontend header drift. No claim is made that the deployed service has the new lifecycle/admission/input fixes.

MVP limitations, explicitly retained: one process/in-memory rooms, cold starts, restart loss, no distributed socket registry, best-effort finished persistence without a durable retry queue, connected-room retention beyond the idle policy, delayed cleanup while unavailable, shared-IP throttling/proxy configuration dependence and no sustained DoS guarantee. These do not constitute a discovered token/authentication/consent bypass. Transitive Python updates, community data quality and missing general software licensing require ongoing maintenance. Browser storage remains readable by same-origin XSS, making escaping and deployed CSP/frame restrictions important.

## 43. Exact next actions

1. Review the isolated security branch and this report. Keep the other agent's uncommitted Question Engine work separate. From `/private/tmp/mizemi-security-audit`, inspect `git log --oneline origin/main..HEAD` and the final HEAD reported by the audit.
2. **The user**, when ready, runs `git push -u origin codex/security-audit`. This audit did not push. That pushes the final report HEAD and both implementation commits.
3. Verify **Verify classroom game** on that exact SHA. Require backend with PostgreSQL, five shutdown-regression runs, frontend tests/build, browser E2E, classroom smoke and secrets/dependency scans to pass. Do not merge on the strength of local pytest alone. If CI fails, preserve its logs and investigate; do not retry until green as a substitute for diagnosis.
4. Re-run the complete matrix after integrating any parallel Question Engine changes. Resolve only finished, reviewed overlaps in an explicitly authorized integration/release task.
5. Separately authorize release/Render changes. Apply and verify the existing frontend CSP/frame/referrer policy, assess API HSTS/Permissions-Policy and confirm proxy trust and Neon TLS settings privately. Deploy only with that later authorization; then repeat the production matrix and confirm the deployed SHA before lifting the production block.

MIZEMI SECURITY AUDIT COMPLETE
