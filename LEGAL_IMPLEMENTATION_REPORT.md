# MiZeMi legal, privacy and accessibility implementation

Date: **18 September 2026**. This records implemented behavior and engineering verification, not a legal opinion, certification or guarantee of compliance. **Implemented locally; not deployed.** No push, merge, repository-visibility change, Render settings change or direct Neon operation was performed.

Branch: `codex/legal-readiness-implementation`, worktree `/private/tmp/mizemi-legal-implementation`.
Base: `eca8bdca8ec2444e0ed38a7a05d04093290a82cc` (fetched `origin/main`).
Implementation commits:

- `9414918125eb9a8a861b8473e8a86f8ff85aa469` — minimize finished profiles and expose retention facts.
- `aeff9b9a16969cb2b90139f2b9a8e09452f19603` — bilingual legal pages, accessibility, tests and deployment documentation.

This report and the updated historical audit are committed separately after verification. Their enclosing commit is available from `git log -1 -- LEGAL_IMPLEMENTATION_REPORT.md`.

## 1. Privacy implementation

Public `/privacy`, `/terms` and `/accessibility` pages work without joining a room, in English and Hebrew. `?lang=en` / `?lang=he` links choose language and direction explicitly. Legal routes do not initialize a game connection, including when a tab already holds session credentials. During play, legal links use a separate tab with `noopener noreferrer`, preserving the profile draft and avoiding credential copying through an opener.

Privacy text was checked against the current profile schema, session module, game domain, repository mapping, maintenance worker, network layer and hosting blueprint. It distinguishes collection, question use, room disclosure, live memory, finished database records and browser storage. It describes optional age/movie/artist/song/personal fact, required city/food/hobby/music and display name, answers, server times, correctness, scores, connection/readiness and group rankings. It does not promise anonymity, local-only cloud processing, infallible security, a deletion SLA or legal certification.

A public, narrowly allowlisted `GET /api/v1/privacy-info` returns policy version, configured retention days, idle minutes, maintenance interval and `raw_profiles_persisted=false`. No URL, secret or full settings object is returned. Existing API middleware makes it `Cache-Control: no-store`. The browser fetch omits credentials and cache, times out after 15 seconds, validates the response, and offers retry. The collection form cannot submit when the backend cannot substantiate this version of the notice. Other game/WS contracts remain unchanged.

## 2. Data-collection notice

The profile form now shows a readable notice before its submit control, with a full-policy link. It explains offline classification/group reasoning, audience disclosure, disabled-field exclusion, raw-profile minimization, saved result content, configured cleanup timing, optionality, lack of post-submission editing and the unresolved contact limitation. There is no extra blanket legal checkbox.

The notice is visible text, not a tooltip or tiny footer disclaimer. Submission against an old backend that lacks the new privacy endpoint is deliberately unavailable; deploy the matching backend first in a separately authorized release.

## 3. Consent wording

Both languages explicitly label each checkbox as permission to use that answer for game questions. Visible labels and accessible names match. Help text says unchecking does not prevent the server receiving the submitted value. Initial flags remain unchanged: personal fact off, other fields on. Consent is still enforced server-side before literal, derived, distractor and group reasoning. No scoring or question-generation rule was changed.

The code does not offer retrospective profile/flag editing. That limitation is disclosed. This implementation does not establish that default-on choices constitute legally sufficient consent in every future audience/context; that remains a professional review question.

## 4. Retention and minimization changes

| Data/location | Implemented behavior |
|---|---|
| Unsubmitted profile | Browser component memory; not intentionally put in persistent browser storage |
| Submitted raw profile during active play | Server memory; preserved through lobby/ready/active reconnect |
| Raw profile at FINISHED | Replaced with an empty profile marker; `has_profile`, player identity, generated rounds, answers and scores remain usable |
| New database snapshots | No raw profile values or per-field consent rows, even for enabled fields; retain names/IDs/status, game configuration/state/timestamps, questions/options/explanations, accepted answers/server times and scores |
| Generated game content | Can contain consented personal facts. Removing raw profile copies does not anonymize the retained quiz |
| Existing database profiles | Maintenance deletes at most 500 legacy profile rows per transaction, only for FINISHED games; does not alter game timestamps or active records |
| Finished game expiry | Existing default **7 days from last save**; delete at most 100 expired FINISHED game trees per transaction |
| Maintenance | Startup and every 300 seconds while running; service sleep/failure/backlog can delay deletion. Graceful shutdown joins maintenance and persistence workers before disposal |
| Disconnected rooms | Existing 120-minute idle default, checked during maintenance, only with no sockets. Connected result rooms can retain generated content until closure/restart |
| Browser session | `sessionStorage['mizemi.session']` retains seat identifiers, display name and private credential; Leave/Play again/Back to start clears it. Browser session restoration can extend its lifetime |
| Language | `localStorage['mizemi.language']` until changed/cleared |
| Provider logs/backups | Retention not verified; the policy does not promise live-row deletion instantly erases all backups |

No retention period was invented or shortened silently. No database migration drops a table. Legacy profile decoding remains for compatibility/cleanup only. ORM joins/filters and bounded deletes use SQLAlchemy expressions; rollback tests verify no half-deletion. New PostgreSQL tests also verify legacy cleanup leaves the retention timestamp unchanged.

The knowledge E2E oracle previously reconstructed its input from saved profiles. The first complete regression therefore correctly failed after minimization. It now reconstructs the reviewed synthetic fixture using persisted player IDs/names, asserts stored profiles are empty, and compares the exact final public/stored/replayed questions and answers. Playwright additionally asserts the exact outbound synthetic profile fields and flags. Semantic media/domain coverage, independent classification/count checks, supporting explanations and determinism were retained. No debug metadata was exposed to production clients.

## 5. Privacy request mechanism — owner action remains

No dedicated authorized public contact method or operator identity was supplied or found in the repository. Private Git-author email addresses were **not** repurposed. The pages truthfully say the channel has not yet been published; an arranged demonstration can use an existing private organizer/operator channel. Users without that channel are told to avoid real personal information.

The text explains requests for access/correction/deletion where applicable, verification before disclosure, and why a room code/name alone is insufficient. It discourages public GitHub issues containing personal data or credentials. No unauthenticated deletion endpoint or unsafe identity lookup was added. A host's pre-game removal is not presented as a general privacy-deletion service.

**Before real-user promotion:** owner must provide the public operator identification and an authorized private contact channel, appoint someone to receive requests and establish proportionate verification/handling. The fallback is not a complete public rights-request service. No guaranteed response period is invented.

## 6. Terms implementation

English/Hebrew terms cover voluntary group play, self-submitted information, third-party privacy/content rights, unlawful/abusive content, interference/impersonation, unauthorized hosted security testing, existing host removal/resource controls, intellectual-property scope, availability/restarts and limitations of friendly quiz scores. They preserve applicable non-waivable rights and contain no absolute liability exclusion, invented jurisdiction clause, numeric age gate or blanket transfer of submissions.

The audience remains classroom/group/portfolio demonstration. The service is explicitly not reviewed for child-directed use. Organizers considering minors must resolve the relevant notices, permissions and safeguards first; optional age is not verification. An adult-only policy was not silently invented while awaiting the owner's audience decision.

## 7. Accessibility fixes

- Main/banner/navigation landmarks; one page-level heading; skip link; native controls and legal-page table of contents.
- English `lang=en`/LTR and Hebrew `lang=he`/RTL; mixed player text retains directional isolation.
- Solid visible focus; stage-heading focus on relevant state changes without stealing focus from controls outside the game. Roster/timer refreshes do not constantly refocus.
- Required/invalid field semantics, associated validation descriptions and first-invalid-field focus for profile, name/room and question-count inputs.
- Answer color contrast improved: yellow/teal/red backgrounds darkened; text indicators retained. Correct answers, rankings, connections and winners do not depend only on color or emoji.
- Removed generic-element ARIA naming that failed semantic checks; connection status now has visible text.
- Timer readable with `aria-live=off`; a separate atomic status announces the five-second warning/expiry instead of each second. Rules and scores unchanged.
- 320px host/header/fieldset reflow, wrap-safe content, touch-size controls and reduced-motion support. Pages also wraps at narrow widths and enlarged text.
- Footer links accessible throughout, without replacing the active game.

The first accessibility checks identified a language-control landmark gap and enlarged-text overflow on Pages; later keyboard tests identified a 320px host header overflow. All were fixed and the checks rerun. Tests do not suppress axe violations. The test-only `axe-core` package is pinned at 4.13.0 (MPL-2.0), adds no runtime analytics/service and is not imported by the production app.

## 8. Accessibility statement

The bilingual statement describes measures actually implemented and tests actually performed. It explicitly records the unresolved fixed timer, lack of per-player extension/pause/untimed mode, missing public contact, and lack of VoiceOver/NVDA/TalkBack spoken-output or independent conformance assessment. It does not claim that synchronized gameplay automatically qualifies for a timing exception, or that MiZeMi is fully compliant/certified.

## 9. GitHub Pages changes

The static presentation footer links intentionally to the authoritative Render pages, including a Hebrew privacy link. It does not maintain a second policy copy. Exact destinations, keyboard reachability, focus, accessibility and reflow are tested locally. The existing Render SPA rewrite supports direct legal routes. These routes/links are **not claimed to be deployed** by this work; verify them after a separately authorized coordinated release.

## 10. Cookies and tracking conclusion

No cookie banner, analytics, advertising pixel, tracking SDK or external runtime script was added. Source search found no common tracking/script signatures; the E2E legal-page journey asserts requests stay on the two local application origins and cookies are empty. Existing multiplayer tests also reject external requests. Dependency review confirms the runtime dependencies remain React and React DOM. These checks concern application code, not an assertion that infrastructure providers keep no logs.

## 11. Third-party disclosure

The pages describe Render frontend/backend/WebSocket processing, Neon finished-record storage and the separate GitHub/Pages project origin. They link to provider privacy pages and acknowledge network metadata, potential international processing, unverified provider retention/account arrangements and possible provider data access. No DPA/region/transfer basis or “providers cannot access data” claim was invented.

Actual account terms, processing locations, subprocessor/transfer arrangements, backups and incident procedures still require owner verification/professional advice before broader launch. No provider console/database was inspected or changed.

## 12. Dataset attribution and software notices

Existing `backend/app/data/knowledge/LICENSES.md`, source manifest and accessible game credits retain Wikidata CC0 and GeoNames CC BY 4.0 attribution/license/modification notices. No data source or license changed. README preserves the owner's source-visible portfolio preference with no general open-source license and explains GitHub platform rights and separately licensed material.

Every build now writes `dist/THIRD_PARTY_NOTICES.txt` from the installed React, React DOM and scheduler MIT license files. Terms link to it and the reference-data notices. The production build verified all three names/versions and MIT text. This addresses the old audit's missing hosted runtime notices. Contributor/branding publication authority and Git-author privacy confirmations from the earlier audit remain unconfirmed; implementing a site footer does not resolve them.

## 13. Exact verification

Environment: local macOS, Python **3.14.7**, Node **26**, Chromium/Playwright **1.63.0**, disposable local PostgreSQL on port 55439 with a UTF-8 database and unique test schemas. No production database was used. PostgreSQL table/transaction tests were enabled through `MIZEMI_TEST_POSTGRES_URL`.

Baseline before edits: frontend **350 tests / 13 files**, type-check and build passed. The initial sandboxed backend baseline was **1269 passed, 3 skipped, 1 failed** because a loopback socket bind was denied. With local-network permission and disposable PostgreSQL, the unchanged baseline was **1273 passed, 2 deprecation warnings**. This environment failure was not hidden or classified as an application defect.

| Check | Command/method | Final result |
|---|---|---|
| Full backend, including PostgreSQL | `MIZEMI_TEST_POSTGRES_URL=<local disposable DB> .venv/bin/python -m pytest backend/tests -q` | **1279 passed**, 2 deprecation warnings, 29.35s; no skip or native crash |
| Privacy/minimization, PostgreSQL, retention/lifecycle, security, semantic-oracle tests | Same DB env; pytest `test_privacy_minimization.py test_postgres.py test_database_lifecycle.py test_final_security_audit.py test_classroom_knowledge_oracle.py -q` at their integration/unit paths | **88 passed**, 2 warnings, 10.36s |
| Frontend complete tests | `npm --prefix frontend test` | **392 passed / 15 files**; includes timer warning and privacy-info failure/retry/config checks |
| Frontend types | `npm --prefix frontend run type-check` | PASS |
| Production build | In frontend: `VITE_API_BASE_URL=https://mizemi.onrender.com VITE_WS_BASE_URL=wss://mizemi.onrender.com npm run build` | PASS; 46 modules; license artifact emitted |
| Focused knowledge E2E | `npm --prefix frontend run test:e2e -- classroom.spec.ts -g knowledge-he` | **1 passed**, 15.3s after oracle update |
| Full Playwright | `npm --prefix frontend run test:e2e` | **8 passed**, 51.9s |
| Keyboard/legal/accessibility | Five `legal-accessibility.spec.ts` scenarios within full suite | PASS; EN/HE legal routes, profile error focus, ready/question/results/leaderboard/finish, popup draft/session isolation, axe WCAG A/AA + best-practice tags, mobile/reflow/reduced motion |
| Classroom concurrency | `.venv/bin/python backend/tests/smoke_classroom.py` | PASS; **1 host + 20 players, 21 TCP WebSockets, 3 rounds**, 0.21s |
| Authorization, WS Origin, hidden answers, consent derivation, XSS, SQL/rollback, safe errors | Full backend/frontend suites and existing multiplayer security assertions | PASS; existing protections retained |
| Build configuration/secrets | Independent scan of production dist for DB/private-key/token signatures and localhost/insecure backend URLs; check public HTTPS/WSS URLs | 0 matched private/config signatures; 0 insecure/local backend URLs; expected public URLs present |
| Runtime tracking | Independent source signature search, runtime dependency review, browser origin/cookie assertions | No application tracker found |
| Current-tree secrets | `.venv/bin/python scripts/check_secrets.py` including untracked/build output | 0 high-confidence findings; no real local env file in implementation worktree |
| Reachable-history secrets | `.venv/bin/python scripts/check_secrets.py --history` | 0 findings; no history rewrite |
| npm audit | `npm --prefix frontend audit --audit-level=low` | 0 vulnerabilities |
| Python audit | `.venv/bin/python -m pip_audit --progress-spinner off` | No known vulnerabilities found |
| Dependency consistency | `.venv/bin/python -m pip check` | No broken requirements found |
| Lockfile reproducibility | `npm ci --offline --ignore-scripts` | PASS; no lockfile drift |
| Whitespace | `git diff --check` and staged checks before commits | PASS |
| Updated deployed routes / remote CI | Not pushed/deployed; no new remote run | **NOT EXECUTED**; requires later owner-authorized release and remote verification |
| Physical mobile / real spoken screen reader / independent accessibility certification | No corresponding session/equipment evaluation performed | **NOT EXECUTED**; recorded limitations |

The two warnings are existing Starlette/httpx TestClient and AnyIO BlockingPortal deprecations. No test was skipped to obtain the recorded final full-suite pass. Browser keyboard input uses Tab/Enter/type-ahead; for the Hebrew native select, Chromium receives a Unicode key through CDP because Playwright's named-key map has no Hebrew layout. This dispatches browser input, not a DOM value mutation. It does not establish physical-keyboard or screen-reader compatibility on every platform.

## 14. Visual QA and Git safety

Reviewed actual screenshots from the tested production build: desktop Hebrew Privacy, 320px Hebrew Privacy, English Accessibility, Hebrew collection notice, English final leaderboard and the full mobile Pages landing. Additional EN/HE privacy/terms/accessibility and game screenshots are generated by Playwright. Branding, line length, direction, visible focus, mobile wrapping and readable form notice were reviewed. Automated overflow checks cover 320px and 200% root text sizing on legal/Pages layouts. This is text-enlargement testing, not a claim of physical-device/native browser-zoom certification.

Screenshots, E2E database and transient logs contain only synthetic test sessions and remain ignored/local. They are not staged or committed. The review uses `frontend/test-results/` artifacts generated by the exact tests, not mockups.

The original checkout remains on `codex/github-pages-landing`, preserving its README/report and unrelated lockfile modification. The protected original lockfile SHA-256 remains `5ce92a07171ded0100886b0ef3ffaacc27f51eefa6f55cea9850c8fa9e82411f`. Only the separate implementation lockfile intentionally adds axe-core; unrelated peer-metadata churn was excluded. Exact paths were staged; `git add .` was not used. No production Question Engine algorithm, scoring, consent behavior, runtime Python version or CI stage changed.

Changed files are confined to backend minimization/API/tests, frontend legal UI/accessibility/tests/test dependency/build notices, Pages HTML/CSS and the specification/deployment/readiness reports. `git diff --name-only eca8bdc..HEAD` gives the complete exact list. The two reports are the final documentation commit; no application change remains uncommitted after that commit.

## 15. Remaining legal uncertainties and next actions

**Ready locally:** bilingual legal pages, collection disclosure, precise question-use labels, minimized finished persistence/legacy cleanup, verified retention facts, consistent footer/Pages links, runtime software notices and tested accessibility improvements. The implementation is not yet live and is not a legal guarantee.

**Owner actions before broader real-user use:**

1. Supply an authorized private privacy/accessibility contact and suitable public operator identification; confirm who receives and verifies requests. Replace the explicit contact limitation only with real details. Confirm the intended audience. Do not publish home/phone or repurpose a contributor's private email.
2. Resolve provider contract/security/backup/location/transfer arrangements and proportionate incident/request procedures. Verify the actual environment's retention settings. Review what legal basis and consent evidence are appropriate; finished records intentionally do not retain the raw consent form.
3. Obtain the needed Israeli privacy/accessibility/minor-use professional assessment, especially operator-specific applicability/exemptions and the fixed 20-second timer. No universal registration/notification duty or arbitrary age threshold is introduced here.
4. Test with real assistive technology and people who need accommodations; decide whether timed play needs an accessible alternative before offering it to that audience.
5. Independently resolve the earlier contributor/logo/Git-identity publication gates before changing repository visibility. This implementation does not settle ownership.
6. Review these commits and text. When ready, the owner may push this branch and verify GitHub Actions; any deployment is a separate decision. Deploy compatible backend before frontend, then Pages; verify legal deep links, policy facts, notices, cleanup and a synthetic game on the deployed architecture.

**Current limited/demo use:** no new immediate credential exposure or authorization bypass was found. Controlled synthetic-data demonstrations can continue. Do not treat the current fallback as permission for unattended real-person data collection: pause that use until participants have appropriate operator/contact disclosure and a reachable private request channel. Do not expand to child-directed use or broad promotion while the identified gaps remain. Existing live code has not acquired these fixes automatically.

Implementation references, consulted **18 September 2026**:

- BEST PRACTICE: [W3C Understanding Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) — live status without unnecessary focus/announcements.
- BEST PRACTICE: [W3C Understanding Timing Adjustable](https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html) — fixed timing limitation; exception is not assumed.
- PROVIDER PRIVACY TERMS: [Render Privacy Policy](https://render.com/privacy), [Neon privacy link](https://neon.com/privacy-policy) (redirects to [Databricks Privacy Notice](https://www.databricks.com/legal/privacynotice)) — provider disclosure, not proof of this owner's account arrangements.
- The current-law/legal-source analysis and redistribution terms remain in `LEGAL_READINESS_REPORT.md` §27 and the checked-in knowledge `LICENSES.md`; their qualifications are preserved. This implementation does not independently determine statutory applicability or claim certification.
