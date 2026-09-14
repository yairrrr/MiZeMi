# CI reliability report

Audit date: 2026-09-14. Scope: remaining **Verify classroom game** failures. No push, merge, deployment, Render change, or Neon access was performed.

## 1. Baseline and scope

Isolated branch: `codex/ci-reliability`, worktree `/private/tmp/mizemi-ci-reliability`, created from fetched `origin/main` at **a89379309e0384a3e0d576ee625e3ef1d7db032b** (PR #49 merge). Both the security commits `2ed96df`, `0eeec2f`, `8b60797` and media improvement `2ea764f` are ancestors. Security implementation files match the merged security fix. Production Question Engine code was not changed.

The original checkout remained on `codex/group-intelligence`; only its pre-existing `frontend/package-lock.json` metadata modification was present. Its SHA-256 before and after this work is `5ce92a07171ded0100886b0ef3ffaacc27f51eefa6f55cea9850c8fa9e82411f`. No files were copied from that checkout's uncommitted changes.

Unchanged baseline: full backend with local PostgreSQL **1,250 passed, 2 warnings, 34.45s**; focused knowledge Playwright **1 failed** after completing all 20 rounds, at `classroom.spec.ts:212`, exactly the obsolete movie-pair assertion. The browser scenario took 9.7s. This reproduction preceded the test changes.

## 2. Backend segfault reproduction

Historical failure: [run 34784683337](https://github.com/yairrrr/MiZeMi/actions/runs/34784683337), commit `3995e7a461cd4347cc3f7200d67edbbf7078a89d`, Python 3.14.7, Ubuntu 24.04 x86-64 runner image `20260907.300`, exit **139**.

The actual failing threads were:

- `asyncio_0`: `purge_expired` → repository `delete_older_than` → SQLAlchemy `do_execute`; the native C stack includes `_sqlite3.cpython-314-x86_64-linux-gnu.so`.
- `asyncio-portal`: application lifespan exit → `engine.dispose` → `StaticPool.dispose` → `do_close` on the shared SQLite connection.
- Main pytest thread: waiting for `TestClient` shutdown inside `test_count_is_strictly_validated_by_server`.

The failure occurred **during a test's application shutdown**, before pytest finished. It was not an interpreter-finalization crash after a green test summary. The step name “Backend including PostgreSQL” does not mean the failing connection was PostgreSQL.

An isolated detached checkout of `3995e7a` ran the current two retention-order regressions: **2 failed, 3 deselected, 1.20s**. Both observed `dispose` before `cleanup finished`. This deterministically reproduces the unsafe lifecycle ordering. Ten independent runs of the historical configuration suite each passed 30 tests (300 total), so **the native signal itself was NOT reproduced on this macOS ARM64 machine**. The report does not equate a local assertion failure with a reproduced SIGSEGV.

Reproduction command (current regression copied only to a temporary test directory):

```sh
PYTHONPATH=backend /private/tmp/mizemi-ci-reliability/.venv/bin/python -X faulthandler -m pytest /private/tmp/mizemi-ci-lifecycle-repro/test_database_lifecycle.py -q -k shutdown_waits
```

Run from the detached historical checkout. Raw logs are local `/private/tmp/mizemi-ci-original-crash.log`, `/private/tmp/mizemi-ci-old-order.log`, and `/private/tmp/mizemi-ci-old-configuration-{1..10}.log`.

## 3. Root cause

The demonstrated application defect was **canceling the asynchronous waiter without joining its background retention thread, then disposing the database engine while that worker could still use the connection**. `asyncio.to_thread` work continues when its waiter is canceled. The original code canceled maintenance and proceeded to disposal; the deterministic test and simultaneous crash stacks agree on this ordering defect. In-memory SQLite uses one `StaticPool` connection with cross-thread access enabled.

The crash's native frames support that lifecycle defect as the cause of the observed SQLite crash. Without a local native signal/core reproduction, no claim is made about an additional CPython-internal defect. Loaded-extension names alone are not evidence that psycopg or greenlet caused this crash.

## 4. Python 3.14 involvement

Python **3.14 is retained**. Locally tested Python 3.14.7 on macOS ARM64, SQLite 3.53.4 and local PostgreSQL 17.11. The latest merged-main [run 34885576813](https://github.com/yairrrr/MiZeMi/actions/runs/34885576813) already passed **1,250 backend tests in 53.60s** on Ubuntu/Python 3.14.7 and passed all five shutdown repetitions. It failed later in Playwright.

The local five complete repetitions below use the historical crash's greenlet 3.5.5. An additional complete suite uses greenlet 3.5.6 observed in the latest runner. There is no evidence justifying an interpreter downgrade.

## 5. Native dependencies

SQLAlchemy **2.0.51** with compiled C extensions enabled; psycopg and psycopg-binary **3.3.5**, with `psycopg.pq.__impl__ == 'binary'`. Greenlet **3.5.5** was explicitly installed only into the disposable ARM64 test environment to include the native module present on the historical x86 runner. Greenlet **3.5.6** was subsequently tested to match the latest runner. No repository requirement or lockfile was changed.

The historical and current runner logs use the same SQLAlchemy/psycopg versions and Python 3.14.7. Current greenlet differs by one patch version; successful runs with 3.5.5 demonstrate that installing 3.5.6 was not required to make the repaired lifecycle pass locally.

## 6. Exact backend fix and CI change

The production fix is already merged from **2ed96df** and was preserved:

1. Signal maintenance to stop and await its running retention operation.
2. Await `hub.shutdown()` to cancel game timers and join the persistence executor, including queued writes.
3. Dispose the SQLAlchemy engine only after both workers have finished.
4. Serialize complete save and retention transactions with a reentrant lock, which protects the single in-memory SQLite connection.

This branch adds verification rather than duplicating that fix: the new lifecycle test pauses the actual retention SELECT with a connection checked out, starts two queued persistence operations, then checks both commits and worker termination before disposal. It runs against in-memory SQLite, file SQLite, and an isolated PostgreSQL schema. The temporary PostgreSQL schema is removed afterward.

`verify.yml` now supplies its existing disposable PostgreSQL service URL to the repeated lifecycle stage, so the new PostgreSQL case runs in each repetition. Python, dependency pins, test selection, error propagation, and all existing stages remain intact. No `continue-on-error`, stderr suppression, ignored exit 139, or coverage removal was added.

## 7. Repeated backend results

Command for each full process: `PYTHONFAULTHANDLER=1 PYTHONUNBUFFERED=1 MIZEMI_TEST_POSTGRES_URL=<disposable-local-test-db> .venv/bin/python -m pytest backend/tests -q`.

| Run | Result | Duration | Process exit |
| --- | --- | --- | --- |
| Full 1, greenlet 3.5.5 | 1,266 passed, 2 warnings | 31.16s | 0 |
| Full 2, greenlet 3.5.5 | 1,266 passed, 2 warnings | 30.74s | 0 |
| Full 3, greenlet 3.5.5 | 1,266 passed, 2 warnings | 28.97s | 0 |
| Full 4, greenlet 3.5.5 | 1,266 passed, 2 warnings | 29.23s | 0 |
| Full 5, greenlet 3.5.5 | 1,266 passed, 2 warnings | 29.72s | 0 |
| Additional full run, current runner greenlet 3.5.6 | 1,266 passed, 2 warnings | 28.56s | 0 |

All five lifecycle-stage processes passed **8 tests** each with PostgreSQL enabled: **9.47s, 9.46s, 9.56s, 9.53s, 9.40s**, all exit 0. Full-process completion was checked, not only the printed pytest summary.

## 8. E2E failure diagnosis

Five recent failing runs were inspected: `34885072538`, `34885094481`, `34885102795`, `34885566701`, and `34885576813`. Their reported failure was the browser assertion, not another backend SIGSEGV. On merged main, the backend and repeated shutdown steps passed; downstream concurrency/audits were skipped by ordinary fail-fast behavior after the browser failure.

The exact obsolete requirement was that one explanation mention both “המסור” and “לזמן את הרוע”, followed by another requiring both “ספורט” and “אימה”. The unchanged test reproduced the first failure locally. Inspection of all explanations also showed the second predicate was false. Its earlier explanation-count assertion had passed.

## 9. Actual 20-round failed quiz

These are the final persisted questions from the baseline failed browser game, matched by question IDs to a fresh internal trace with the same seed. They are synthetic fixture data. Family/domain information was read offline, never exposed through a new API or WebSocket field.

Seed: `1052053811360472261`. Composition: **10 semantic, 3 direct, 4 geographic, 3 cross-domain**.

### Round 1: SEMANTIC_MAJORITY / song

אם מסתכלים על השירים האהובים עליכם, איזה סגנון מוביל?

Options: פופ · רוק · אלקטרונית · אר אנד בי

Correct answer: **פופ**

Explanation: 4 אנשים בחרו שירים בסגנון פופ — יותר מכל סגנון אחר. במקום השני: רוק (2). בין הבחירות: Shake It Off, Blank Space, Yellow ועוד 1.

### Round 2: SEMANTIC_MAJORITY / artist

איזה ז׳אנר מוזיקה הכי נפוץ בין האמנים האהובים שבחרתם?

Options: רוק · מזרחית · ים תיכונית · פופ

Correct answer: **פופ**

Explanation: 4 אנשים בחרו אמנים שמזוהים עם מוזיקת פופ — יותר מכל סגנון אחר. בין הבחירות: עומר אדם, עדן בן זקן, טיילור סוויפט ועוד 1.

### Round 3: SEMANTIC_COUNT / hobby

לכמה מכם יש תחביב שדורש פעילות גופנית?

Options: 3 · 2 · 1 · 4

Correct answer: **3**

Explanation: 3 אנשים בחרו תחביבים עם פעילות גופנית: ריצה, כדורגל, גלישה.

### Round 4: DIRECT_CHOICE / music

איזה סגנון מוזיקה הכי פופולרי כאן?

Options: מזרחית · פופ · ג׳אז · רוק

Correct answer: **מזרחית**

Explanation: 2 אנשים בחרו מוזיקה מזרחית — יותר מכל סגנון אחר.

### Round 5: DIRECT_AGE / age

מי המבוגר ביותר מבין המשתתפים ששיתפו את הגיל שלהם?

Options: עמית · ליאור · דנה · עומר

Correct answer: **ליאור**

Explanation: (Direct round; no explanation.)

### Round 6: DIRECT_UNIQUE / place

מי היחיד/ה שגר/ה ב"באר שבע"?

Options: נועה · דנה · עומר · ליאור

Correct answer: **ליאור**

Explanation: (Direct round; no explanation.)

### Round 7: SEMANTIC_COUNT / food

כמה מהמאכלים שבחרתם הם מהמטבח המזרח תיכוני?

Options: 3 · 1 · 2 · 0

Correct answer: **1**

Explanation: אדם אחד בחר מאכל מזרח תיכוני: פלאפל.

### Round 8: GEO_REGION_MAJORITY / place

רוב הקבוצה גרה באותו אזור. באיזה?

Options: המרכז · הצפון · אזור ירושלים · הדרום

Correct answer: **המרכז**

Explanation: 3 אנשים גרים במרכז — יותר ממחצית הקבוצה.

### Round 9: SEMANTIC_COUNT / song

כמה אנשים בחרו שיר אהוב בסגנון אלקטרוני?

Options: 2 · 1 · 0 · 3

Correct answer: **1**

Explanation: אדם אחד בחר שיר בסגנון אלקטרוני: Blank Space.

### Round 10: GEO_REGION_COUNT / place

כמה מכם מגיעים מהצפון?

Options: 1 · 0 · 3 · 2

Correct answer: **1**

Explanation: אדם אחד גר בצפון: חיפה.

### Round 11: SEMANTIC_COMPARISON / movie

אם מסתכלים על בחירות הסרטים, איזה צד מנצח — הרפתקאות או פשע?

Options: הרפתקאות · פשע

Correct answer: **הרפתקאות**

Explanation: 2 אנשים בחרו סרטי הרפתקאות, לעומת אדם אחד שבחר סרט פשע.

### Round 12: SEMANTIC_UNIQUE / food

מי היחיד/ה בקבוצה שבחר/ה מאכל אסייתי?

Options: דנה · ליאור · עמית · עומר

Correct answer: **עומר**

Explanation: עומר: סושי.

### Round 13: SEMANTIC_DIVERSITY / artist

כמה סגנונות מוזיקה שונים מיוצגים באמנים שבחרתם?

Options: 5 · 6 · 4 · 3

Correct answer: **5**

Explanation: 5 סגנונות: פופ, רוק, מזרחית, ים תיכונית וקאנטרי. בחירה אחת יכולה להשתייך לכמה סגנונות; כל סגנון נספר פעם אחת.

### Round 14: SEMANTIC_UNIQUE / movie

רק אדם אחד בקבוצה בחר סרט פשע. מי זה?

Options: ליאור · עמית · נועה · דנה

Correct answer: **דנה**

Explanation: דנה: המסור.

### Round 15: GEO_CLOSEST_PAIR / place

אילו שניים מכם גרים הכי קרוב זה לזה?

Options: דנה + עמית · נועה + ליאור · נועה + עמית · דנה + עומר

Correct answer: **נועה + עמית**

Explanation: נועה ועמית גרים ברחובות ובראשון לציון, כ־9 ק״מ זה מזה בקו אווירי.

### Round 16: SEMANTIC_COMPARISON / artist

בין האמנים שבחרתם, איזה סגנון מופיע יותר — רוק או קאנטרי?

Options: רוק · קאנטרי

Correct answer: **רוק**

Explanation: 2 אנשים בחרו אמנים שמזוהים עם מוזיקת רוק, לעומת אדם אחד שבחר אמן שמזוהה עם מוזיקת קאנטרי.

### Round 17: GEO_REGION_DIVERSITY / place

מכמה אזורים בארץ מגיעים חברי הקבוצה?

Options: 2 · 4 · 1 · 3

Correct answer: **3**

Explanation: 3 אזורים: הצפון, המרכז והדרום.

### Round 18: CROSS_SUBGROUP_MAJORITY / hobby,music

מבין מי שבחרו תחביב ספורטיבי, איזה סגנון מוזיקה הכי נפוץ?

Options: מזרחית · רוק · ג׳אז · פופ

Correct answer: **מזרחית**

Explanation: 3 אנשים בחרו תחביבי ספורט. מתוכם, 2 בחרו מוזיקה מזרחית — יותר מכל סגנון אחר.

### Round 19: CROSS_SUBGROUP_COMPARISON / food,hobby

מבין מי שבחרו אוכל איטלקי, מה יותר נפוץ — תחביבי ספורט או תחביבי יצירה?

Options: תחביבי ספורט · תחביבי יצירה

Correct answer: **תחביבי ספורט**

Explanation: 3 אנשים בחרו אוכל איטלקי. מתוכם, 2 בחרו תחביבי ספורט ו־1 בחר תחביב יצירתי.

### Round 20: CROSS_INTERSECTION_COUNT / movie,hobby

כמה אנשים בחרו גם סרט הרפתקאות וגם תחביב יצירתי?

Options: 3 · 2 · 1 · 0

Correct answer: **1**

Explanation: אדם אחד בחר גם סרט הרפתקאות וגם תחביב יצירתי: מוצאים את נמו + גיטרה.

## 10. Product versus test verdict

**The test was wrong.** Semantic generation materially affected the final quiz across movies, artists, songs, hobbies, food, geography and cross-domain reasoning. Movie genres in this fixture have several tied leaders, so a decisive comparison such as adventure versus crime is legitimate. Both artist and song selections have a decisive Pop lead (four players); declared favorite music instead leads with Mizrahi (two players). The selected cross-domain questions reasoned about the actual sport/music, Italian-food/hobby and adventure-film/creative-hobby memberships.

No production generation, selection, explanation wording or knowledge data was changed to force obsolete title/category pairs into a quiz.

## 11. Exact E2E assertion changes

The existing rich fixture's values were moved unchanged into `frontend/e2e/fixtures/knowledge-room.json`, along with reviewed expected memberships. The test still drives real host/player browsers through all rounds, reconnects and scoring. It collects only whitelisted public completed-result fields and invokes `backend/tests/classroom_knowledge.py` locally after FINISHED.

The verifier checks:

- Exactly 20 final questions; at least **9 semantic rounds** (45%), at least 2 geographic and 2 cross-domain rounds. Direct questions with explanations cannot inflate the semantic count.
- Selected semantic domains include **movie, artist, song, hobby and food**.
- Exact browser result/question/option/correct-answer agreement with the completed game's persisted record and the same-seed internal generation trace.
- Correct semantic/group answers by independently counting the fixture's expected memberships, including counts, decisive comparisons, unique members, diversity and cross-domain intersections/subgroups.
- Artist and song majority answers are **פופ**, each derived from four submitted choices, rather than being satisfied by a direct favorite-music question.
- Nonempty printable Hebrew explanations, group reasoning/counts for media leaders, and absence of developer/database terms.
- A second trace with identical profiles, player IDs and game seed is identical.

Active-question checks additionally reject internal metadata fields; existing correct-answer/consent-marker/token confidentiality checks remain. No wire contract was changed. Test metadata is available only to the local test process.

## 12. Stability and strength

Assertions concern source coverage and true memberships, not which particular pair or sentence wins the selector's tie-break. The count threshold follows the documented 45% semantic allocation while preserving room for direct, geographic and cross-domain families. This fixture deliberately supports all three media sources; the test imposes no such requirement on arbitrary rooms.

Five fixed-seed backend cases verify this same browser fixture. Eight negative cases confirm the oracle rejects missing movie/artist/song/hobby semantics, a swapped scored answer, a wrong semantic fact, empty explanations, and technical explanations. All **13 passed**. The fixture's semantic expectations are test data, not fixture-specific production rules.

Five fresh browser games passed in **56.0s**, each producing **10 semantic / 3 direct / 4 geographic / 3 cross-domain** rounds. Seeds: `1455714732211528050`, `16074625215457375300`, `5324402926162189535`, `2364000942933781503`, `10913417584557729669`.

Local diagnostics are written to each knowledge test's `test-results/.../knowledge-public-results.json` and `knowledge-final-quiz.json`; these include all 20 questions, options, correct answers and explanations. The internal file also records seed, family, kind and domains. No automatic external artifact upload was added. A proposed broad results-directory upload was rejected by automatic approval review because that payload might contain sensitive artifacts; local evidence files satisfy this task without that upload.

## 13. Full regression matrix

Commands run from the repository root unless labeled `frontend/`. Every PostgreSQL test command received `MIZEMI_TEST_POSTGRES_URL` for the disposable loopback database, never Neon. Full backend commands use faulthandler and unbuffered output. No PostgreSQL test was skipped in those runs.

| Check | Command / method | Result |
| --- | --- | --- |
| Baseline backend | `.venv/bin/python -m pytest backend/tests -q` | 1,250 passed, 2 warnings, 34.45s |
| Historical race | Copied lifecycle order tests against detached `3995e7a` | 2 expected failures; disposal precedes retention completion |
| Historical native reproduction attempt | 10 fresh processes, `pytest backend/tests/integration/test_game_configuration.py -q` | 30 passed each; no local SIGSEGV |
| Unit tests alone | `.venv/bin/python -m pytest backend/tests/unit -q` | 1,028 passed, 15.51s |
| Integration tests alone, PostgreSQL enabled | `.venv/bin/python -m pytest backend/tests/integration -q` | 238 passed, 2 warnings, 14.74s |
| Five complete backend runs | `.venv/bin/python -m pytest backend/tests -q` in five separate processes | 1,266 passed each; all exit 0; durations above |
| Latest runner's greenlet 3.5.6 | Complete backend suite with PostgreSQL enabled | 1,266 passed, 2 warnings, 28.56s; exit 0 |
| PostgreSQL/persistence | `pytest backend/tests/integration/test_postgres.py backend/tests/integration/test_game_repository.py backend/tests/integration/test_persistence_statistics_integration.py -q` | 18 passed, 2 warnings, 1.16s |
| Repeated lifecycle, all three databases | Five × `.venv/bin/python -X faulthandler -m pytest backend/tests/integration/test_database_lifecycle.py -q` | 8 passed each; all exit 0 |
| Retention/shutdown selection | `.venv/bin/python -m pytest backend/tests -q -k 'retention or shutdown'` | 10 passed, 1,256 deselected, 2 warnings, 1.89s |
| Oracle fixed-seed and negative cases | `pytest backend/tests/unit/test_classroom_knowledge_oracle.py -q` | 13 passed, 0.85s |
| Merged security/media/consent fixes | `pytest backend/tests/integration/test_final_security_audit.py backend/tests/integration/test_socket_admission.py backend/tests/unit/test_media_questions.py backend/tests/unit/test_category_first_questions.py -q` | 171 passed, 2 warnings, 3.42s |
| Frontend full unit suite | `frontend/ npm test` | 350 tests, 13 files passed, 1.66s |
| Frontend type-check | `frontend/ npm run type-check` | Exit 0; includes E2E TypeScript |
| Production build | `frontend/ npm run build` | Exit 0; 38 modules; also rebuilt by final E2E |
| Focused classroom knowledge E2E | `frontend/ npm run test:e2e -- --grep knowledge-he` | 1 passed, 14.7s |
| Five fresh knowledge games | `frontend/ npm run test:e2e -- --grep knowledge-he --repeat-each=5` | 5 passed, 56.0s |
| Complete Playwright suite | `frontend/ npm run test:e2e` | 3 passed, 44.1s |
| Complete Playwright, latest runner greenlet 3.5.6 | `frontend/ npm run test:e2e` | 3 passed, 43.6s |
| Classroom concurrency | `.venv/bin/python backend/tests/smoke_classroom.py` | PASS: 1 host, 20 players, 21 real WebSockets, 3 rounds, 0.25s |
| Classroom concurrency, latest runner greenlet 3.5.6 | `.venv/bin/python backend/tests/smoke_classroom.py` | Same complete smoke passed again, 0.19s |
| pip check | `.venv/bin/python -m pip check` | No broken requirements; both greenlet versions |
| npm audit | `frontend/ npm audit --audit-level=low` | 0 vulnerabilities |
| pip-audit | `.venv/bin/python -m pip_audit --progress-spinner off` | No known vulnerabilities; both greenlet versions |
| Current tree/build/report secrets | `.venv/bin/python scripts/check_secrets.py` | 0 high-confidence findings; no local real-env files |
| Full reachable history secrets | `.venv/bin/python scripts/check_secrets.py --history` | 0 findings; full history present |
| Whitespace / patch safety | `git diff --check` | Exit 0 |
| CI workflow validation | `actionlint -shellcheck='' .github/workflows/verify.yml` | Exit 0; actionlint 1.7.12. ShellCheck unavailable and explicitly not executed |
| Remote run of these new commits | GitHub Actions | **NOT EXECUTED — push is not authorized; awaiting user push** |

All checks above were executed. Secret scans include local generated browser evidence and build output; no credential values are included in this report. The existing security implementation and public frontend/backend code have no diff against the audited baseline.

## 14. Remaining risks and limits

- **Remote acceptance remains open.** A new run containing these commits must pass before the overall GitHub Actions issue is called resolved. Existing remote backend success is supporting evidence, not a substitute for that run.
- The native SIGSEGV was observed in GitHub logs, not reproduced locally. The local Mac differs from GitHub's Ubuntu x86-64 runner; the unsafe ordering was reproduced deterministically and the repaired ordering was verified on SQLite/PostgreSQL.
- Two existing deprecation warnings concern Starlette's httpx TestClient support and AnyIO's BlockingPortal alias. They are not native crashes; no unrelated dependency migration was made.
- The test oracle intentionally depends on internal trace/record types. A future semantic family or taxonomy change may require updating its independent expected facts; these internals remain outside the public contract.
- The five-person rich fixture is synthetic and bounded. It does not prove semantic coverage for every possible room; the existing broader media, consent and unknown-value suites continue to run.
- No new production security verdict or deployment readiness claim is made by this CI-focused report. The prior security report remains separate.

## 15. Files changed

- `.github/workflows/verify.yml`: enable the disposable PostgreSQL URL in repeated lifecycle tests.
- `backend/tests/integration/test_database_lifecycle.py`: actual connection/retention/queued-persistence shutdown regression across three database configurations.
- `backend/tests/classroom_knowledge.py`: offline finished-game verifier and diagnostic output.
- `backend/tests/unit/test_classroom_knowledge_oracle.py`: fixed-seed and negative verification cases.
- `frontend/e2e/fixtures/knowledge-room.json`: unchanged rich browser inputs plus independent membership expectations.
- `frontend/e2e/classroom.spec.ts`: meaningful semantic assertions through the offline verifier and local diagnostics.
- `CI_RELIABILITY_REPORT.md`: this report.

## 16. Commits

Verified implementation commits:

- `fadeda094bc3cde1391ed418ff108fd718177d6b` — `test(ci): verify database shutdown with queued native work`
- `31aefaa58bb44557a67d1eaa72347e4a158e8aba` — `test(e2e): verify final quiz semantics from reviewed fixture facts`

This report is committed separately after these two commits so the implementation references are exact. Reachable-history scanning after the implementation commits checked **555 blobs with zero findings**.

## 17. Git status and isolation

Only the files listed above belong to this branch's changes. No `backend/app`, `frontend/src`, knowledge asset, dependency requirement, or lockfile diff against the baseline exists. Exact paths are staged; `git add .` was not used. The original checkout's unrelated lockfile modification is preserved and excluded. After the report commit, the isolated audit worktree is clean; the original checkout retains its intentional lockfile modification.

## 18. Exact user next step

Push **only** `codex/ci-reliability` from `/private/tmp/mizemi-ci-reliability`, then verify **Verify classroom game** for the pushed SHA. Do not use a successful run for another SHA as acceptance. Inspect every stage: backend with PostgreSQL; repeated database shutdown; frontend type-check/tests/build; Browser game; Classroom concurrency; secrets/history/dependency audits.

```sh
git -C /private/tmp/mizemi-ci-reliability push -u origin codex/ci-reliability
```

The exact final branch tip is supplied in the final response. After pushing, check with `gh run list --branch codex/ci-reliability --workflow verify.yml`, match its `headSha` to `git rev-parse HEAD`, and run `gh run watch <run-id> --exit-status`. If it fails, retrieve that run's failed log and diagnose the actual failed stage before changing runtime/dependencies.

**BACKEND CI ISSUE: FIXED** — merged lifecycle fix preserved and locally verified; exact native signal reproduction limit above.

**E2E SEMANTIC ASSERTION: FIXED** — obsolete pair coupling replaced by verified final-game semantics.

**GITHUB ACTIONS: AWAITING REMOTE VERIFICATION**.
