# MiZeMi legal, privacy, accessibility and licensing readiness audit

**Implementation update: 18 September 2026.** Sections 1–28 below preserve the historical audit/publication evidence. Their pre-implementation storage/UI findings are superseded by §29 and `LEGAL_IMPLEMENTATION_REPORT.md`. The implementation is local and has not been deployed. Outstanding owner/professional-review gates remain.

Audit and source retrieval date: **17 September 2026**. This is an engineering readiness assessment informed by primary legal materials, not a legal opinion or accessibility certification. During the original audit, no policy, terms, age restriction, retention rule, software license, product behavior, deployment or repository visibility was changed. The subsequent authorized implementation is recorded in §29.

## 1. Executive summary

**Public GitHub: YES, AFTER FIXING LISTED BLOCKERS.** The remaining publication gates are evidence of permission to publish the logo and other contributors’ work, and an intentional review of the personal author metadata that publication exposes. These are unresolved evidence questions, not findings that the work is stolen or that ordinary author attribution is unlawful. A missing general LICENSE file is **not**, by itself, a publication blocker. The shipped knowledge sources appear suitable for redistribution with the existing notices.

**Public service: NOT YET READY.** The existing Render demo already processes identifiable participant information. In particular, the question-use checkbox does not control storage: unselected fields still enter finished-game database snapshots. Collection disclosures, operator/contact information, rights handling, cloud-transfer arrangements and accessibility applicability need attention now; broad promotion should wait for the service checklist below.

No live credential or public player-data exposure was discovered. Automated scans are not proof that every possible secret or real-person fixture can be recognized. The operator, revenue, intended age group and contributor agreements remain unconfirmed. The publication follow-up in §28 found embedded OpenAI provenance claims in the logo, but account/input rights still need owner confirmation. The owner has now selected source-visible portfolio publication without a general open-source license.

| ID | Finding / evidence | Legal classification | Publication/service priority | Severity |
|---|---|---|---|---|
| L1 | One logo copied to three paths; embedded OpenAI provenance claim, account/input rights unconfirmed. Three non-owner human contributors; publication permission not established | REQUIRED: authority to publish; NEEDS PROFESSIONAL LEGAL REVIEW if ownership disputed | BLOCKER BEFORE PUBLIC GITHUB until authority is confirmed | MEDIUM |
| L2 | Four personal email addresses and one local-machine address in commit authorship metadata | RECOMMENDED intentional disclosure review; permission/lawful disclosure REQUIRED for genuinely private third-party material | SHOULD FIX; BLOCKER BEFORE PUBLIC GITHUB if any disclosure is unintended and unresolved | MEDIUM |
| P1 | Collection screen lacks controller/contact, retention/recipient/rights disclosure; checkbox wording can imply more privacy than storage implements | LIKELY REQUIRED for current demo; REQUIRED for an in-scope public-service database | BLOCKER BEFORE PUBLIC SERVICE LAUNCH; address before further real-user demo collection | HIGH |
| P2 | Full profiles, including opted-out values, persisted at finish; connected rooms have no absolute lifetime; cleanup is operational, not a seven-day guarantee | REQUIRED purpose/minimization assessment where law applies; RECOMMENDED shorter collection/storage design | SHOULD FIX now; resolve purpose and truthful retention before promotion | MEDIUM |
| P3 | Actual operator, provider regions, account contracts, backup/log retention and transfer basis unverified | LIKELY REQUIRED / NEEDS PROFESSIONAL LEGAL REVIEW | BLOCKER BEFORE PUBLIC SERVICE LAUNCH | MEDIUM |
| P4 | No user-facing access/correction/deletion contact or procedure; consent cannot be changed after profile submission | REQUIRED applicable rights handling; RECOMMENDED usable withdrawal/removal path | BLOCKER BEFORE PUBLIC SERVICE LAUNCH | MEDIUM |
| A1 | Measured answer-text contrast failures; invalid connection-status ARIA; focus/error-association gaps | REQUIRED if covered and non-exempt; otherwise RECOMMENDED | SHOULD FIX; BLOCKER BEFORE PUBLIC SERVICE LAUNCH if accessibility duties apply | MEDIUM |
| A2 | Applicability/exemption and timed-game accommodation not established; no accessibility statement | NEEDS PROFESSIONAL LEGAL REVIEW / accessibility professional assessment | BLOCKER BEFORE PUBLIC SERVICE LAUNCH until determined | MEDIUM |
| C1 | Built frontend contains React/React DOM/scheduler but no full MIT notice or notice artifact | REQUIRED license compliance for distributed copies | SHOULD FIX current hosted distribution; BLOCKER BEFORE PUBLIC SERVICE LAUNCH | MEDIUM |
| M1 | Optional age accepts 5–120; no actual age eligibility or child-use policy | NEEDS PROFESSIONAL LEGAL REVIEW before child-targeted use | BLOCKER BEFORE PUBLIC SERVICE LAUNCH **if minors are intended** | MEDIUM |
| K1 | Wikidata CC0 / GeoNames CC BY 4.0; attribution, transformations and hashes recorded | REQUIRED retain applicable notices | NO ISSUE identified for these imports | INFORMATIONAL |
| T1 | No Terms of Use; no abuse/reporting contact | OPTIONAL for controlled demo; STRONGLY RECOMMENDED for public service | SHOULD FIX before promotion | LOW |
| B1 | No tracking cookies, analytics, advertising scripts or pixels found | NOT CURRENTLY APPLICABLE: tracking consent manager/banner | NO ISSUE | INFORMATIONAL |

The bases for these classifications and their qualifications are in the numbered sections below. “Blocker” is an audit release gate, not a claim that a statute expressly requires this report or a particular document title.

## 2. Current project status

- Audited committed source: **`eca8bdca8ec2444e0ed38a7a05d04093290a82cc`**, current fetched `origin/main`, merge of PR #52.
- Isolated inspection branch/worktree: `codex/legal-readiness`, `/private/tmp/mizemi-legal-readiness`.
- Original checkout: `/Users/yairbendavid/PycharmProjects/MiZeMi`, branch `codex/github-pages-landing`, original HEAD `8fbd0dd`. Its unrelated `frontend/package-lock.json` change was preserved and not used as the dependency baseline.
- React/Vite static frontend: <https://mizemi-frontend.onrender.com/>. FastAPI/WebSocket backend: <https://mizemi.onrender.com/>. PostgreSQL hosted on Neon according to the supplied architecture; no Neon console/database or Render account settings were accessed.
- GitHub Pages landing page: <https://yairrrr.github.io/MiZeMi/>. Static HTML/CSS with local logo, no client script or collection form.
- Repository deployment blueprint specifies a single free backend instance, Python 3.14.7, static frontend and seven-day database retention. The exact deployed revision and private environment overrides are **not verified**.
- Assumption for legal triage: privately operated, small, no advertising/data brokerage, no revenue or school/public-body ownership demonstrated. These are not confirmed facts. Educational-institution operation would materially change several conclusions.

The audit follows the latest legal-readiness request. It does not certify the earlier full security/CI release checklist or a new remote GitHub Actions run.

## 3. Data inventory

Evidence comes from actual schemas, mappers and lifecycle code: `backend/app/application/profile_rules.py`, `backend/app/domain/game/profile.py`, `backend/app/api/schemas.py`, `backend/app/realtime/{envelope,game_events,hub,transport}.py`, `backend/app/infrastructure/database/{models,base}.py`, `backend/app/infrastructure/repositories/game_repository.py`, `backend/app/main.py`, `frontend/src/features/player/ProfileForm.tsx`, `frontend/src/features/player/profileSchema.ts`, `frontend/src/state/session.ts`, `frontend/src/i18n/I18n.tsx` and `frontend/src/realtime/gameSocket.ts`.

**Retention/location key used in every table:**

- **M**: backend process memory. Rooms with no live sockets and no activity expire after the configured idle interval (default 120 minutes), checked every 300 seconds. Connected rooms are not subject to that absolute age limit. Restart loses this state.
- **D**: saved only when a game reaches FINISHED and the asynchronous persistence succeeds. Default deletion eligibility: game `updated_at` older than seven days; at most 100 finished games deleted per maintenance run. Provider backups/logs have unverified additional retention. Section 20 explains limitations.
- **S**: `sessionStorage['mizemi.session']`, current tab/session, until explicit leave/play-again or browser session termination; restoration behavior is browser-dependent.
- **L**: `localStorage['mizemi.language']`, no application expiration.
- “Neon: D” means the application’s PostgreSQL destination under the supplied production architecture, **not a claim that production rows were inspected**.
- Personal information includes pseudonymous identifiers when linkable to a participant. “Potentially special” is a content/context warning, not an assertion that every ordinary preference meets the statutory category.

### 3.1 Participant profile fields

All rows originate with the participant, go to the Render backend, stay in M, and go to Neon as D if the game is saved. None is intentionally stored in browser persistent storage; form drafts and rendered game content exist in browser memory. Every submitted value is stored even when its question-use flag is false. Values may be revealed through selected questions/options/explanations only when permitted; the raw profile object is not broadcast to classmates.

| Field / bound | Purpose | Optional? | Persisted table/location and retention | Broadcast / generation | Personal / potentially special information |
|---|---|---|---|---|---|
| `city`, text ≤40 | Locality comparisons and questions | No | `profile_fields` value/key/type/position, M+D | Consented value and derived geography may appear; no home GPS | Yes; ordinary locality not automatically special; context can reveal sensitive information |
| `favorite_food`, text ≤40 | Direct and cuisine/category questions | No | Same, M+D | Only consented generation | Yes; free text could disclose health/religion, but the engine must not infer either from cuisine |
| `hobby`, text ≤40 | Direct/activity-category questions | No | Same, M+D | Only consented generation | Yes; text could reveal health, belief or intimate matters |
| `favorite_music`, one of 20 fixed choices | Music preference and group comparisons | No | Same, M+D | Only consented generation | Yes; ordinary style is not proof of ethnicity/religion or special-category status |
| `age`, integer 5–120 | Age-based comparisons/questions | Yes | Same, stored text plus integer discriminator, M+D | Only consented generation | Yes; age alone not automatically specially sensitive; identifies possible minors |
| `favorite_movie`, text ≤60 | Title, genre, release/series/country facts where supported | Yes | Same, M+D | Only consented generation | Yes; free text/context may be sensitive |
| `favorite_artist`, text ≤60 | Artist and supported music-genre group facts | Yes | Same, M+D | Only consented generation | Yes; preference cannot establish personal nationality/religion |
| `favorite_song`, text ≤60 | Song and supported genre/group facts | Yes | Same, M+D | Only consented generation | Yes; free text/context may be sensitive |
| `personal_fact`, text ≤120 | Optional personal-fact question material | Yes | Same, M+D | Only if enabled; starts disabled | Yes; highest likelihood of health, intimate/family, religious or third-party information |
| Per-field `allow_question_usage` | Gate literal and derived question use | Required boolean for each submitted field | `profile_fields.allow_question_usage`, M+D | Used internally, not directly broadcast | Linked consent preference: personal; may itself reveal reluctance to disclose |

Defaults are **enabled for all fields except `personal_fact`**. Blank optional values are omitted. Four required fields cannot be omitted merely by disabling question use. The checkbox is neither a storage opt-out nor a general privacy-policy consent. Text filters reject common email/link/long-number patterns but do not reliably identify every private or offensive statement.

### 3.2 Identity, participation, game and derived records

| Field(s) | Source / purpose / optionality | Stored location / retention | Shared with other players? / question use | Render / Neon / browser | Personal/special assessment |
|---|---|---|---|---|---|
| `display_name` (1–20 after normalization) | User; mandatory room identity | `players.display_name`, M+D; player S | Room roster, questions, leaderboard; yes as question subject/option | Render yes; Neon D; S | Personal if identifiable; arbitrary text may contain private/third-party material |
| `player_id`, `game_id`, player `position` | Server UUIDs/order; mandatory linkage | `players`, FKs throughout snapshot, M+D | IDs/room context shared; linked to game facts | Render yes; Neon D; S includes IDs | Pseudonymous personal data when linked |
| `room_code` | Server-generated six-character discovery code | M, host/player S, URL query/history where shared; not DB | Host shares with invitees; not an authentication secret | Render yes; Neon no; S/URL | Indirectly linkable; a room link should not be publicly posted casually |
| `host_token`, `player_token` | Server random credentials; mandatory authenticated role | Plaintext only delivered to that client/S; SHA-256 digests in backend M; no DB token column | Never broadcast; not question input | Render handles credential; Neon no; S | Sensitive security credentials; not automatically the statutory “specially sensitive” class |
| `connected`, `is_ready`, `has_profile`, `is_host` | Server participation state | First three in `players`, M+D; `is_host=false` computed for players | Roster broadcasts; readiness controls start | Render yes; Neon first three D; browser memory | Linked behavioral data; not special by default |
| `question_count` (1–50), game `language` (`en`/`he`) | Host choices/defaults; configuration | `game_configurations`, M+D | Room configuration shared; determines quiz | Render yes; Neon D; browser memory | Contextual personal data when linked; language not proof of ethnicity |
| Game `state`, `current_question_index` | Server lifecycle | `games`, M+D | Shared current state; not independent profile input | Render yes; Neon D; browser memory | Linked activity information |
| Question ID/index/count/type/text/correct option/time limit | Deterministic server generation and sequencing | `game_questions`, M+D | Active text/options shared; answer hidden until results | Render yes; Neon D; browser memory | May contain participants’ consented attributes; sensitivity inherits underlying content |
| Option ID/position/text | Server generation | `question_options`, M+D | Options shared while active | Render yes; Neon D; browser memory | Same possible personal content |
| Difficulty, question language, `source_rule_id` | Server generation | `question_details`, M+D | Difficulty/language public; internal rule ID not wire-exposed | Render yes; Neon D; browser memory only public subset | Mostly technical; linked questions can still be personal |
| Explanation, `knowledge_version` | Server result evidence | `question_explanations`, M+D | Explanation at results; internal version not active wire data | Render yes; Neon D; browser memory explanation | Can reveal consented personal/group facts; small counts are not necessarily anonymous |
| Canonical entity IDs, aliases, genre/category classifications, locality reference coordinates, group counts/intersections/distances | Offline catalog + consented inputs + deterministic calculations | Temporary generation structures in M; selected factual text survives in D above | Selected conclusions appear in questions/results; no separate full profile broadcast | Render yes; Neon only selected stored question material; browser public text | Derived participant information; not home geolocation or unsupported identity inference |
| Submitted `question_id` / `option_id` | Player choice; optional participation per round | `answers` with game/player linkage, M+D | Individual answer returned to that player; distribution aggregated to room | Render yes; Neon D; browser memory | Personal game behavior; not normally professional/personality assessment |
| `answered_at`, server start/deadline, elapsed response time | Server clock for fairness; mandatory when relevant | `answers.answered_at` in D; start/deadline/timers M | Deadline and server timing shared; own answer outcome | Render yes; Neon answer time D; browser memory | Linked behavioral timing, not a submitted client score |
| Correctness, per-round points, total score | Server scoring | `scores.total_score` D; round calculation M and result messages | Own detailed outcome; all players’ totals/ranks/winners shared | Render yes; Neon totals D; browser memory | Personal performance; ordinary party-game score not automatically statutory personality/study assessment |
| Answer distribution, answered/player counts, leaderboard ranks and winners | Server aggregates | Derived M; constituent answers/scores D | Room-wide | Render yes; Neon underlying data D; browser memory | Group data may permit identification in small rooms |
| `created_at`, `updated_at` | Server UTC timestamps at insert/update | Every ORM table listed above, D | Not generally broadcast | Render yes; Neon D; no persistent browser copy | Linked record metadata |
| Client envelope `event`, `payload`, `timestamp`, `game_id` | Client requests; timestamp not authoritative answer time | Validated/transient M; accepted domain data saved as above | Only server-generated events broadcast | Render yes; Neon only accepted domain data; browser memory | May include the relevant personal payload |
| Server envelope timestamp, error code/message, reconnect snapshot | Server synchronization/errors | Transient M; client game reducer memory | Role-filtered state; public errors scrubbed | Render yes; Neon no separate event log; browser memory | Context/participation info; errors should not echo private content |
| UI language | User/default | L, no expiry | Not broadcast; distinct from game language | Browser-only setting; not independently sent to Neon | Preference; not identifying alone |

### 3.3 Transport, hosting and operator information

| Data | Actual processing and retention | Privacy assessment |
|---|---|---|
| IP address, URL/path/query, Origin, User-Agent and request time | Network/hosting necessarily handles connection metadata. Application HTTP abuse guard keeps IP-keyed timestamps in memory: 60-second moving window, bounded 2,048 keys; stale entries prune on later POSTs, otherwise can remain until restart. No IP column in game DB. Provider logs/retention not inspected. | Potential personal information; distinguish provider logging from app persistence. |
| WebSocket role/token headers | Credentials sent as WebSocket subprotocol pair (`mizemi.host` or `mizemi.player`, token), not an initial JSON auth message. Player UUID appears in WS query. Plaintext passes through TLS-terminating Render to backend. | Application avoids token logging; provider/header-log configuration still needs verification. |
| Browser history/cache | Shared room URL can remain in history. Static assets cache normally; API security guard uses `no-store`. No intentional persistent profile cache. | Browser storage is accessible to same-origin scripts and vulnerable to XSS; same-origin is not encryption. |
| Outbound queued events / socket registry | Bounded queues and live connection objects contain role-filtered payloads in M; discarded on closure/process termination. | Same privacy class as queued content. |
| App operational logs | Generic maintenance/persistence/HTTP error strings; production entry point disables Uvicorn access logging. No profile/token logging found. Test/dev entry points can log room-code/player-ID URLs. | Verify actual launch command and provider retention; do not promise “no logs.” |
| Database connection secret and deployment credentials | Operator-supplied backend environment / provider control plane; never a frontend `VITE_*` value. Database URL reaches backend DB driver; not a participant-table field. | Confidential credentials; actual production values were not accessed. |
| Git authorship, repository account, issues/PRs; operator hosting/billing accounts | GitHub receives source/history/author metadata; each provider separately handles its own customer account data. | Operator/contributor personal information, separate from the player database. |
| Offline artist/person names and IDs | Public reference records committed with catalog; distributed with repository/backend, not participant submissions. | Some identify public people. Public factual reference data is not equivalent to private player data; licensing does not extinguish all personal rights. |

No account email/password collection, device geolocation, microphone/camera access, uploads, advertising identifier, payment card, analytics SDK, runtime AI prompt, runtime third-party knowledge query or mailing-list subscription was found. Potentially sensitive text can nevertheless enter the fields above.

## 4. Israeli privacy analysis

Amendment 13 is already in effect (14 August 2025). Identifiable and reasonably identifiable information falls within the revised definition; pseudonyms do not ensure anonymity. The statutory database definition excludes collections for personal use that are not for business purposes, but a public multiplayer portfolio service should **not assume** it qualifies. Even an applicable database exception does not erase the law’s broader privacy protections. Classification of this operator needs confirmation. [PPA Amendment 13 Q&A](https://www.gov.il/he/pages/tikun13_qa?chapterIndex=6)

Age, ordinary locality, ordinary media preferences and casual scores are not automatically specially sensitive information. Intimate/family/health/religious/political content can be; free `personal_fact` text is the clearest risk. Do not treat a movie genre or Mizrahi preference as evidence of the participant’s religion, origin, health or personality. The revised definitions and purpose/authorization restrictions supply the legal basis for that distinction. [Amendment 13, enacted text](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf)

| Topic | Now / future classification | MiZeMi-specific action |
|---|---|---|
| Purpose limitation | REQUIRED where applicable, including current real-user processing | Document game delivery, scoring and any justified short persistence purpose. Do not reuse profiles for marketing, model training or research without an appropriate separate basis. |
| Notice and informed choice | LIKELY REQUIRED now; REQUIRED for in-scope public service | Resolve P1; see section 6. Current question-use toggles do not disclose all processing. |
| Minimize unnecessary retention | REQUIRED assessment where regulations apply | Justify storing all completed raw profiles, especially opted-out fields, when there is no results-retrieval feature. Consider less storage; no change made by this audit. |
| Access/correction | REQUIRED for an in-scope database | Establish an authenticated request channel and operator process. A bespoke self-service UI is not invariably required. |
| Deletion | REQUIRED in applicable statutory circumstances; broader voluntary deletion RECOMMENDED | Do not claim Israeli law supplies an unconditional GDPR-style erasure right over every accurate record. Address inaccurate/incomplete/unclear/outdated data under section 14 and any additional applicable regimes. |
| Security | REQUIRED for in-scope databases | Record database definition, authorized access, applicable security tier, protection measures and incident handling; code tests alone do not satisfy governance obligations. |
| Marketing | NOT CURRENTLY APPLICABLE on observed functionality | No direct-mailing or promotional-message feature. Reassess before collecting contacts or sending campaigns. |
| DPO | NOT CURRENTLY INDICATED under assumed small private operation | Reassess institutional/public-body operation, data brokerage, or large-scale systematic monitoring/specially sensitive core processing. |

Purpose and rights recommendations above follow the regulator’s [privacy impact tool](https://mojforms.justice.gov.il/mojaemprivacyprotectionauthority/dpiaform.html), [Amendment 13 professional guide](https://www.gov.il/BlobFolder/reports/guide_tikon13_professional/he/tikun%2013%20_170825.pdf) and [data security regulations](https://www.gov.il/BlobFolder/generalpage/1files/he/IT2017.pdf). This is not a finding that ordinary quiz scoring is high-risk profiling.

Security tier remains **NEEDS PROFESSIONAL LEGAL REVIEW**: the individual-managed category has limited authorized-user and subject-count conditions and exclusions; it is not synonymous with “one free server.” If it applies, regulation 21 substantially narrows the applicable provisions, so this report does not automatically impose every medium/high-tier requirement or regulation 15 on that category. Provider personnel and player access need classification rather than simply counting all browser users as administrators. [PPA full security guide and tier table](https://www.gov.il/BlobFolder/guide/data_security_guide/he/NEW_GUIDE.pdf), [PPA security FAQ](https://www.gov.il/he/pages/data_security_fqa?chapterIndex=6)

Prepare incident triage even for a demo. Mandatory immediate reporting of a serious security incident under the regulations depends on the applicable security tier and event definition. Do not import a universal “72 hours” rule from GDPR or a vendor DPA. [PPA incident-reporting service](https://www.gov.il/he/service/report-of-data-breach)

Mere global reachability does not establish every foreign privacy law applies. Reassess EU/UK targeting, overseas schools and data imports before expansion. Israeli rules for qualifying EEA-origin information add deletion/minimization/accuracy/notice duties, with scope and exceptions requiring a separate facts-based assessment. [PPA EEA-transfer FAQ](https://www.gov.il/he/pages/europe_transfer?chapterIndex=6)

## 5. Database registration/notification analysis

**Currently appears neither registrable nor notifiable, under the private small-demo assumptions — confidence MEDIUM.** No production subject count or operator status was inspected.

Registration under the amended section 8a principally covers public-body databases (subject to the employee-only exception), and databases whose main purpose is collecting personal information for disclosure to others as a business/for consideration, including direct mailing, with **more than 10,000 people**. Notification covers a non-registered database with specially sensitive information about **more than 100,000 people**. These are not general “every database” requirements. [Enacted section 8a](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf), [registration service](https://www.gov.il/he/service/registration_in_the_database), [notification service](https://www.gov.il/he/service/notice-obligation)

Classroom quiz sharing is not shown to be data brokerage. The 33,831 reference entities are not 33,831 registered players, and many are films/foods/localities rather than people. Count data subjects and actual purposes, not JSON rows. An institution operating MiZeMi, a change to selling profile information, or substantial sensitive-data scale requires reassessment. Lack of registration does not waive applicable privacy/security duties. An already registered database also has transition rules; none was evidenced here. [PPA transition/de-registration guidance](https://www.gov.il/he/service/registered_database_deletion)

## 6. Privacy policy/notice conclusion

| State | Conclusion | Reason |
|---|---|---|
| A. Source repository only | **NOT CURRENTLY NECESSARY** to create a player privacy policy solely to publish code | GitHub source publication itself does not collect MiZeMi game profiles. Git author/privacy review remains separate. |
| B. Existing limited/demo Render application | **LIKELY REQUIRED** collection notice; a linked privacy policy is the practical implementation | Real participants submit personal information for automated processing/storage; the narrow personal-use exception is unconfirmed. |
| C. Broadly promoted service | **REQUIRED** notice for an in-scope personal-information database; publish an accurate, accessible privacy policy plus just-in-time disclosure | A page called “Privacy Policy” is not a substitute for intelligible disclosure at collection. |

Section 11 requires information at collection, including whether provision is obligatory or voluntary and consequences, purposes, recipients/purposes of disclosure, controller identity/contact, and access/correction rights. It does not prescribe one universal document title. [PPA updated notice guidance](https://www.gov.il/BlobFolder/legalinfo/duty_to_notify/he/notify13.pdf)

The actual MiZeMi disclosure should cover:

1. The real operator/controller and monitored contact channel.
2. Display name; four required profile fields; five optional fields, including age and personal fact; consent flags; IDs; answers/timestamps/scores; host settings; basic connection/security metadata.
3. Which data is required by the product, that no account is needed, and consequences of refusing required fields. Do not suggest a statutory obligation to participate.
4. Literal and derived group questions from offline facts; no runtime AI or internet lookup. Explain that a consenting movie title can support a movie-genre question, not just a verbatim title question.
5. What classmates and hosts see, including names, scores and consented factual conclusions; the possibility of re-identification from small-group aggregates.
6. The distinction between question-use permission and storage. Explicitly disclose that submitted opted-out values are currently saved at finish.
7. Render backend processing, Neon persistence and relevant cloud/subprocessor/cross-border arrangements once verified; distinguish GitHub Pages traffic from gameplay.
8. Actual memory and database retention, cleanup delays, and verified backup/log retention; no unconditional seven-day deletion promise.
9. Browser session credentials and language preference; no observed analytics/advertising cookies.
10. How to request access, correction, applicable deletion and assistance with changing sharing decisions; identity verification without collecting excessive new data.
11. Intended audience, child-use handling if relevant, prohibition on secrets/third-party personal details, and reasonable security/availability limitations.

Do not obtain a blanket checkbox waiver for unknown uses. The current opt-out defaults are not automatically unlawful, but meaningful consent requires comprehension and real choice, especially where a teacher/host creates pressure. Highlight surprising storage/derivation rather than burying it. [PPA final consent opinion, 2026](https://www.gov.il/BlobFolder/legalinfo/consent-2026/he/cpncent-2025.pdf)

No privacy policy was drafted or added.

## 7. Accessibility applicability

**CURRENT OBLIGATION: NEEDS PROFESSIONAL LEGAL REVIEW / operator clarification.** Israeli service-accessibility provisions concern covered services to the public or an indeterminate part of it, including education, leisure and entertainment, and online information about such services. This is narrower than “every Israeli website.” A free multiplayer game can still be a covered service; a portfolio label, room code or noncommercial intention does not establish an exemption. [Commission applicability guidance](https://www.gov.il/he/pages/website_accessibility?chapterIndex=3)

The Commission’s current website guidance describes an exemption for an exempt dealer or turnover below NIS 120,000, and a different three-year exemption for NIS 120,000–1,000,000 **only for sites operating before 26 October 2017**. MiZeMi is a new site, so the latter is not its route. Underlying regulation versions contain a NIS 100,000 figure and an exempt-dealer route; government pages are not fully synchronized. Confirm the applicable current threshold, entity-wide turnover calculation and eligibility with the Commission/accountant rather than treating “zero app revenue” as decisive. [Commission exemption guidance](https://www.gov.il/he/pages/website_accessibility?chapterIndex=8), [official regulations](https://www.gov.il/BlobFolder/guide/accommodating_service_providing_rules/he/sitedocs_service_acessibility_regulations.pdf)

**FUTURE PUBLIC-LAUNCH OBLIGATION: LIKELY REQUIRED unless a valid exemption remains available.** Promotion makes the public-service case stronger, but does not automatically remove an economic exemption. Reassess the operator, institution/business involvement and turnover; record any exemption instead of claiming it by default.

For covered non-exempt services, the Israeli standard is **IS 5568 Part 1 (September 2023)**, based on WCAG **2.0** with national changes/additions, at the level required by the regulations. WCAG 2.2 AA is a useful development target, not automatically the statutory Israeli version. [Official IS 5568-1 text](https://www.gov.il/BlobFolder/legalinfo/israeli_accessibility_standards_pdf/he/sitedocs_si-5568-1-september-2023.pdf), [SII catalog](https://www.sii.org.il/lobby/standardization/standard-page/?id=6751)

An accessibility statement is **REQUIRED when the applicable service rules require it**; current MiZeMi obligation is unresolved with the exemption question. A truthful accessibility/help statement is **RECOMMENDED** even if exempt. It must describe actual accommodations, known limitations/contact routes and any applicable coordinator, rather than claiming compliance based on an automated score. [Commission statement guidance](https://www.gov.il/he/pages/declaration_website_accessibility?chapterIndex=1)

GitHub hosting does not itself exempt a service. Pure source viewing differs from the Pages marketing/entry page and the interactive Render app. The Pages site links directly to playing, so assess it as service information where the service is covered.

## 8. Technical accessibility findings

This was a technical audit, separate from legal applicability. Chromium/Playwright 1.63.0 and axe-core **4.13.0** were used locally; the audit helper was external/temporary and was not added as a project dependency. Automated tags: WCAG 2 A/AA, 2.1 A/AA and best-practice. No claim of full standards conformance.

Three instrumented classroom scenarios passed (English 20 rounds, Hebrew 7 rounds, rich Hebrew knowledge 20 rounds). Axe sampled **21 states**: home, profile, host lobby, active player question, results, leaderboard, finished. Synthetic profiles only. The live homepages were separately checked without creating production rooms.

| Area | Evidence / finding | Action / severity |
|---|---|---|
| Keyboard | Native buttons/inputs/selects; live homepage and Pages Tab sequences reachable with visible outlines. Local quiz answers activated with Enter. A complete local one-round host/three-player journey also passed using Tab, keyboard typing/type-ahead and Enter, including invalid-form correction and leaving. | Preserve native controls; complete assistive-technology validation. |
| Visible focus | 3px focus outlines on homepage controls; native summary outline. Focus frequently returned to BODY after stage replacement. | Manage focus or announce meaningful game-stage transitions; MEDIUM. |
| Contrast | Knowledge Hebrew active-answer text: white on `#e59a00` **2.34:1**, on `#1f8a8a` **4.14:1**, on `#d0555d` **4.08:1** at 16px bold. | These miss 4.5:1 for normal-sized text; darken backgrounds or change text colors; MEDIUM. |
| Connection indicator | `.presence.online` is a generic span with `aria-label="Connected"`; axe `aria-prohibited-attr`. Visible connection status also relies on the dot color. | Expose actual text or an appropriate accessible status role/name; MEDIUM. |
| Headings/landmarks | Main and named regions/lists exist; homepage has h1. Game stages primarily h2; axe `page-has-heading-one` best-practice finding. | Stable page heading hierarchy; LOW. Absence of h1 alone is not automatically an AA violation. |
| Form labels/errors | Label associations and checkbox names present. Error summary uses `role=alert`. No `aria-invalid`, error-to-field `aria-describedby`, or first-error focus handling. Required fields lack a programmatic required indicator. | Associate errors/required state with relevant inputs; MEDIUM usability concern, criterion failure needs full context. |
| Color-only meaning | Correct/incorrect results have words/check feedback; selected answers use pressed state. Connection dots are the exception above. | Preserve redundant textual meaning. |
| RTL/LTR | Tested document `lang`/`dir` updates for English/Hebrew; question/explanation language/direction; `bdi` for mixed names/options. | Positive evidence; manual bilingual screen-reader validation remains needed. |
| Live content | Answer confirmation and some waiting/results text use status/live regions. New timed question text is not reliably announced/focused. | Announce a new question once, avoid reading every timer tick; MEDIUM. |
| Timers | Server-controlled 20-second rounds; no player-facing extension/pause setting. | Assess real-time/essential exception and accommodations with an accessibility professional; do not assume every quiz qualifies. |
| Leaderboard | Ordered list, names/scores, top-rank emoji and numerical ranks elsewhere. | Verify explicit rank announcements, updating order and result reading with a screen reader. |
| Responsive/mobile | No horizontal overflow in sampled 390px mobile game states or live home/Pages at 320/390/640px. Controls mostly generously sized; native labels are clickable. | Positive partial evidence; not a complete touch-target or mobile AT certification. |
| Zoom | Narrow-viewport reflow and 200% root-text enlargement of three profile forms passed without horizontal overflow at 640px. This is not the same as native browser zoom certification. | Native browser zoom to 200%/400% and mobile text settings are still not fully certified. |
| Images/fonts | Logo alt text “MiZeMi”; no content photos or remote fonts; decorative emoji generally hidden where appropriate. | Check brand/tagline information remains available as text. |
| Motion | Reduced-motion CSS exists; live emulated reduced-motion pages had no running animations. | Positive evidence; retain when adding effects. |
| Dialogs | No application modal/dialog flow found. Knowledge credits use native `details`/`summary`. | NOT CURRENTLY APPLICABLE to modal focus trapping. |
| Screen readers | DOM/ARIA inspected, not an actual VoiceOver/NVDA spoken-output session. | **NOT EXECUTED**; required before any broad accessibility-conformance claim. |

Technical criteria: [W3C contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html), [focus order](https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html), [error identification](https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html), [status messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html), [timing exceptions](https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html). These explanations are technical guidance, not Israeli legislation.

Live home and Pages scans reported zero automated violations but each had incomplete/manual checks. Local in-game failures show why a clean homepage scan is insufficient. No product accessibility changes were made.

## 9. Terms of Use conclusion

- Controlled portfolio/demo: **OPTIONAL** as a separate contract page; **RECOMMENDED** short participation rules and operator contact.
- Broad public service: **STRONGLY RECOMMENDED**, especially for user content, child use and abuse handling. No universal Israeli requirement for a page titled “Terms of Use” was established for this free, accountless demo.
- Payments/subscriptions, institution procurement or new regulated activities would need separate analysis.

Have counsel choose proportionate terms covering self-submitted content, no third-party private information, prohibited harassment/illegal material, room abuse, the permission necessary to process/display submitted text, software/data rights, availability/restarts, intended age/audience, complaints and appropriate governing-law/dispute terms. Do not promise that a disclaimer eliminates statutory rights or liability. These are risk-management recommendations, not fabricated mandatory clauses. Hosting contracts also impose acceptable-use/content obligations on the operator. [Render Terms](https://render.com/terms), [GitHub Terms](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)

## 10. Minors/age analysis

The application **does not currently implement an age restriction**. The optional numeric field accepting ages 5–120 is validation, not eligibility, and ages 16–18 appear in synthetic tests. No parental-consent or school authorization workflow exists.

Israeli majority is 18; rules about a minor’s legal acts include representative consent and qualifications/exceptions. That does not yield a universal online-consent threshold of 13 or 16 for MiZeMi. The consequences of this particular processing, the child’s understanding, guardians and the institution’s role need assessment. [Legal Capacity and Guardianship Law, official consolidated text](https://www.gov.il/BlobFolder/generalpage/guardian_080825/he/guardianlaw0725.pdf)

For adult university/classroom demos, obtain voluntary informed participation, permit pseudonyms and nonparticipation without penalty, and avoid asking for secrets. A teacher/student power imbalance can undermine genuine choice. For intended child use, **NEEDS PROFESSIONAL LEGAL REVIEW** before rollout: child-appropriate notices, minimal locality/age detail, guardian/school authority where required, safe questions and no sensitive free-text collection without a justified design. [PPA educational-app/minors report](https://www.gov.il/BlobFolder/dynamiccollectorresultitem/ppa-report18/he/Minors_report.pdf)

An honestly enforced adults-only pilot can reduce exposure to child-specific issues; 18 would refer to legal adulthood, not a discovered universal game-access mandate. A footer saying “18+” while knowingly serving children is not sufficient. Do not collect identity documents merely to make this classroom MVP appear compliant.

## 11. Cookies/tracking analysis

| Technology | Actual use | Conclusion |
|---|---|---|
| Cookies | None set by inspected MiZeMi code; none observed on fresh live frontend/Pages visits | No observed tracking-cookie use |
| `sessionStorage` | Host/player reconnect credentials and room/identity data | Functional, disclose and protect; cleared on explicit leave |
| `localStorage` | UI language only | Functional preference, no application expiry |
| Analytics/ads/pixels | None found | No current marketing consent manager need |
| Third-party scripts/iframes/fonts | None on MiZeMi Pages; app script/assets same-origin | External credit links are links, not embedded trackers |
| GitHub/Render network logging | Providers can process traffic metadata independently | Absence of cookies does not mean absence of personal information |

**Cookie banner: NOT CURRENTLY NECESSARY on the observed design — confidence HIGH for inspected code, MEDIUM for all future/provider behavior.** No freestanding cookie policy or consent manager is presently justified. Explain functional storage in the privacy notice. This is a technology-specific conclusion, not a claim that Israeli consent law never affects cookies. Reassess if analytics, advertising, embedded media, cross-site identifiers or foreign-market targeting are added. [PPA consent opinion](https://www.gov.il/BlobFolder/legalinfo/consent-2026/he/cpncent-2025.pdf), [GitHub Pages IP logging documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)

## 12. Render/Neon/third-party processing

| Party | Data actually involved | Role/evidence and action |
|---|---|---|
| Render static hosting | Frontend files and visitor connection metadata | Host; distinguish infrastructure/account telemetry from processing of player content. |
| Render backend | All participant submissions, session credentials, questions, answers and in-memory state | Render DPA §2.1 describes Render as processor for customer personal data, with exceptions. The operator remains responsible for lawful inputs/instructions. Verify actual account agreement and region. |
| Neon / Databricks | Finished-game relational snapshots, including all submitted profiles; database connection/account metadata | Current Neon terms point to Databricks MCSA/DPA, not simply the old Neon standalone terms. Verify the agreement governing the account, backups, region and subprocessors. |
| GitHub | Source/history, contributor identities, issue/PR content and owner account/usage data | Platform has independent purposes for its service data; do not describe all GitHub activity as MiZeMi’s processor. No gameplay uploads found. |
| GitHub Pages | Static landing page and visitor IP/traffic metadata | GitHub explicitly documents logging visitor IP addresses for security, even without login. |
| Wikidata / GeoNames | Developer build-time queries/downloads only | No player fields sent to them during gameplay; no runtime updating. |
| Apple Music | One curation reference URL | No embedded Apple script/player or runtime preference lookup. Visiting an external link is a separate interaction. |
| npm/PyPI/build systems | Package downloads/build artifacts | No participant-profile transmission found in build code. Do not use real profiles in future CI artifacts/issues. |

Sources: [Render DPA](https://render.com/dpa), [Render Terms](https://render.com/terms), [Neon schedule updated 5 August 2026](https://neon.com/platform-terms), [Databricks MCSA](https://www.databricks.com/legal/mcsa), [Databricks DPA](https://www.databricks.com/legal/dpa), [GitHub privacy statement](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement).

**Cross-border processing: LIKELY REQUIRED review now.** Confirm actual regions and access locations; neither the `.onrender.com` domain nor Neon branding identifies them. Choose and document a valid transfer route. The PPA’s final **13 April 2026** opinion on regulation 2(4) addresses contractual undertakings equivalent to the relevant Israeli protection obligations; a generic EU DPA/SCC link alone does not establish compliance. Regulation 3 adds written recipient safeguards and onward-transfer considerations. [PPA final regulation 2(4) opinion](https://www.gov.il/BlobFolder/legalinfo/infoabroad/he/infoabroad.pdf), [regulation 3 opinion](https://www.gov.il/BlobFolder/legalinfo/takana3/he/regulation3.pdf)

Where outsourcing regulation 15 applies, review risks, permitted use/access, deletion/return, confidentiality, subprocessors and oversight in the arrangement. The individual-managed exception discussed above must be checked before mechanically imposing that whole regulation. Disclose relevant providers/recipients in the user notice regardless of whether a bespoke negotiated DPA is practical. [PPA outsourcing guide](https://www.gov.il/BlobFolder/reports/guide_section_15/ar/guide-section%2015.pdf)

## 13. Knowledge-base source/license matrix

Verified manifest `2026-09-14.1`, schema 2: **33,831 entities**, plus 103 category records: 11,228 movies, 6,655 artists, 9,700 songs, 3,279 foods, 1,679 hobbies, 66 music styles, 1,224 localities. All eight artifact hashes matched the manifest. Evidence: `backend/app/data/knowledge/{manifest.json,LICENSES.md,*.json}`, `scripts/knowledge/{README.md,curation.json,group-curation.json}`, `scripts/expand_knowledge.py`, seed build scripts and `KNOWLEDGE_BASE_REPORT.md`.

| Source and actual use | Exact license / rights | Conditions, restrictions and public-GitHub conclusion |
|---|---|---|
| Wikidata structured seed facts, retrieved 2026-09-11 | **CC0-1.0** | Names/IDs/structured relationships; dedication/waiver covers covered copyright/database rights, with fallback license. Commercial redistribution allowed; no share-alike or mandatory attribution, but provenance retained. **Compatible.** |
| Wikidata WDQS expansion, retrieved 2026-09-13–14 | **CC0-1.0**, same structured-data scope | Bounded factual projections: genres/types/cuisines/origin/release/series/performer relationships. Wikipedia article prose and Wikidata non-structured pages are not included. **Compatible.** |
| GeoNames `IL.zip`, retrieved 2026-09-13 | **CC BY 4.0** | Name/coordinate/feature/district extract; retain attribution and license, indicate normalization/filtering/rounding, no endorsement. Commercial use allowed; no share-alike. Database rights covered to extent held/licensed. **Compatible with notices.** |
| Locally authored taxonomy, aliases, translations and curated classifications | Repository dedicates these reference adaptations to **CC0-1.0** | Valid only to extent contributors have authority; not a license for application code/logo. Confirm contribution authority under L1. |
| Apple Music “Apple Mizrahi” curator page | No open dataset license established | Only cited in `group-curation.json` as a factual spot-check for an artist classification; no prose, artwork or catalog imported. Not a bulk redistribution license. No imported-content blocker found; do not expand scraping under this assumption. |
| MusicBrainz | Core data CC0; supplementary/tag data **CC BY-NC-SA 3.0** under its source policy | **Investigated, not imported.** NC/share-alike would matter for those data if later added. No current restriction from unused data. |
| Population Authority locality package / CBS listings | `other-open` metadata was insufficient to identify exact reusable terms | **Investigated, not imported.** No government CSV copied. Must establish exact terms before any future import. |
| IMDb / TMDB / other movie/song commercial catalogs | No license relied upon | **Not imported** according to build paths, manifests and report; movie/song/artist data here comes from Wikidata, not these catalogs. |

Original-source/license authorities: [Wikidata Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing), [CC0 legal code](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en), [GeoNames format/license](https://download.geonames.org/export/dump/readme.txt), [CC BY 4.0 legal code](https://creativecommons.org/licenses/by/4.0/legalcode.en), [MusicBrainz Data License](https://musicbrainz.org/doc/About/Data_License), [Population Authority source package](https://data.gov.il/he/datasets/population_authority/citiesandsettelments), [Apple factual reference](https://music.apple.com/us/curator/apple-mizrahi/1106112453).

Existing GeoNames attribution names the source, links the license, describes changes and disclaims endorsement in `LICENSES.md`, build documentation and the app’s expandable knowledge credits. Preserve these with redistribution. **All actually imported external bulk sources appear redistributable — confidence HIGH on identified license terms, MEDIUM on completeness of human provenance.** This is not a guarantee against every upstream contributor’s error.

## 14. Copyright/database-rights analysis

Facts and expression are different. Israeli copyright law distinguishes unprotected facts/data as such from potentially original selection/arrangement in a compilation. The legal analysis therefore relies on source permissions, not on “it is factual, so the database is free.” [Copyright Act, WIPO-hosted legislative text, sections 4–5](https://www.wipo.int/wipolex/en/text/202010)

CC0 and CC BY 4.0 address covered copyright and database rights, but do not generally clear trademarks, personality/privacy rights or rights the licensor does not possess. The GeoNames attribution obligation survives transformation; adding an application MIT license would not erase it. The compiled repository can therefore have separate code, reference-data and branding terms. [CC0](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en), [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/legalcode.en)

No plot-summary, lyrics, biography, review, poster, album-art or photograph fields were found in the generated schema. Structural inspection found maximum string lengths by artifact between 26 and 102 characters, consistent with names/aliases/IDs rather than copied prose. This supports, but cannot prove, the origin of every label. Build code does not copy article bodies. Factual explanations are application templates combining reference classifications and consented inputs.

Only three image files are tracked, all MiZeMi logo copies; their separate unresolved provenance is below. No raw downloaded dataset archive, prose dump, PDF or unlicensed media collection was found in tracked files/history paths. Future imports should preserve source/license/retrieval/transformation records and be reviewed before committing, including any share-alike/database-right obligations.

Production loads strict local JSON and never automatically downloads updates or executes data. Build-time network fetches are explicitly invoked and transform data, not remote executable plugins. Unknown/ambiguous resolution fails closed. This is a positive supply-chain boundary, not proof of every factual classification.

## 15. Logo/assets/fonts/licenses

Unresolved assets:

- `logo/image.png`
- `frontend/src/assets/mizemi-logo.png`
- `docs/assets/mizemi-logo.png`

The first two were introduced in commit `8ab453d`; the Pages copy in `8fbd0dd`. All three are the same Git blob. `ENHANCEMENT_REPORT.md` records a user-supplied image. The follow-up parsed its PNG `caBX` Content Credentials chunk: it claims `OpenAI Media Service API`, `gpt-image` version `2.0`, and algorithmically generated media. These are provenance claims, not verified ownership; the signature/trust chain was not cryptographically validated. No original prompt/account/input-artwork permission record was found. See §28.2 for exact hashes and the remaining confirmation.

**L1 publication gate:** confirm the creator and authority to publish the PNGs. If commissioned, check the agreement; if generated with a tool, identify the tool/account terms and any source assets; if stock-based, preserve the exact permitted-use terms. Do not assume paying for creation necessarily transfers all copyright. Owner confirmation of original authorized creation may resolve the evidence gap without a new license. Disputed ownership requires counsel. [Copyright Act ownership provisions, sections 33–35](https://www.wipo.int/wipolex/en/text/202010)

No bundled font files or external font requests were found. CSS names `Inter` and system fallbacks; naming a font does not redistribute its binary. Decorative icons are Unicode emoji/CSS, with no external icon package detected. This does not identify the typeface rendered into the logo PNG; that remains part of the provenance check. Trademark clearance for a larger launch is **RECOMMENDED / NEEDS PROFESSIONAL LEGAL REVIEW**, not a finding of infringement or a reason to assert the name is registered.

## 16. Dependency license review

Inventory basis: audited `frontend/package-lock.json`, installed package metadata/license files after a clean `npm ci`, and the isolated Python 3.14 environment installed from `backend/requirements-dev.txt`. **164 npm package records** including optional platform binaries and **51 installed Python distributions** were reviewed. The table below records versions actually inspected; unpinned Python transitives and Linux-only packages may differ from production.

- Frontend runtime React 19.2.8, React DOM 19.2.8 and scheduler 0.27.0: MIT.
- `psycopg` / `psycopg-binary` 3.3.5: **LGPL-3.0-only**, not AGPL. Ordinary server use does not automatically require publishing proprietary application code. Binary/container redistribution has additional library notice/source/relinking obligations; examine bundled native-library licenses for such a release. Wheels are not committed here. [Psycopg license](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt)
- `certifi` 2026.7.22 and build-only `lightningcss` 1.33.0/platform variants: **MPL-2.0**, limited/file-level obligations; not a reason to label the whole app copyleft. [Mozilla MPL FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/)
- `lru-cache` BlueOak-1.0.0, `mdn-data` CC0 and MIT-0 tools are permissive, not noncommercial licenses.
- SQLAlchemy’s platform-conditional greenlet was not installed on this macOS ARM environment. Reviewed upstream greenlet 3.5.6 metadata declares MIT AND PSF-2.0; the actual Linux/production resolution was **not installed or certified** here. [Upstream release metadata](https://pypi.org/project/greenlet/3.5.6/)
- No GPL/AGPL/noncommercial software package was identified in the inspected inventory. This is not a license audit of the entire Render operating system or every native library inside a future distributed container.

**C1:** the production build created by the normal Vite command includes the runtime libraries but no full MIT permission notice or notice artifact was found in `frontend/dist`. Only declaring a dependency in `package.json` is not the same as preserving required notices in distributed copies. Add a suitable third-party notice artifact to the distributed frontend after approval; verify its output. This audit did not implement it. Publishing source/lockfiles without `node_modules` or `dist` is a separate event. [MIT license terms](https://opensource.org/license/mit)

### Complete inspected package inventory

`dev` means development/build/test; `optional` includes platform-specific lockfile entries. Standard permissive packages require normal notice compliance when copied/distributed, not a new legal blocker merely because they have notices.

Python installed distributions (includes test/audit tooling):

| Dependency | Version | Declared license | Concern / handling |
|---|---|---|---|
| annotated-doc | 0.0.5 | MIT | No unusual restriction identified; preserve applicable notices |
| annotated-types | 0.8.0 | MIT | No unusual restriction identified; preserve applicable notices |
| anyio | 4.15.1 | MIT | No unusual restriction identified; preserve applicable notices |
| boolean.py | 5.0 | BSD-2-Clause | No unusual restriction identified; preserve applicable notices |
| CacheControl | 0.14.4 | Apache-2.0 | No unusual restriction identified; preserve applicable notices |
| certifi | 2026.7.22 | MPL-2.0 | File-level obligations if distributing covered files |
| charset-normalizer | 3.5.1 | MIT | No unusual restriction identified; preserve applicable notices |
| click | 8.5.0 | BSD-3-Clause | No unusual restriction identified; preserve applicable notices |
| cyclonedx-python-lib | 11.12.0 | Apache-2.0 | No unusual restriction identified; preserve applicable notices |
| defusedxml | 0.7.1 | PSFL | No unusual restriction identified; preserve applicable notices |
| fastapi | 0.141.1 | MIT | No unusual restriction identified; preserve applicable notices |
| filelock | 4.0.0 | MIT | No unusual restriction identified; preserve applicable notices |
| h11 | 0.16.0 | MIT | No unusual restriction identified; preserve applicable notices |
| httpcore | 1.0.9 | BSD-3-Clause | No unusual restriction identified; preserve applicable notices |
| httpx | 0.28.1 | BSD-3-Clause | No unusual restriction identified; preserve applicable notices |
| idna | 3.20 | BSD-3-Clause | No unusual restriction identified; preserve applicable notices |
| iniconfig | 2.3.0 | MIT | No unusual restriction identified; preserve applicable notices |
| license-expression | 30.4.4 | Apache-2.0 | No unusual restriction identified; preserve applicable notices |
| markdown-it-py | 4.2.0 | OSI Approved :: MIT License | No unusual restriction identified; preserve applicable notices |
| mdurl | 0.1.2 | OSI Approved :: MIT License | No unusual restriction identified; preserve applicable notices |
| msgpack | 1.2.2 | Apache-2.0 | No unusual restriction identified; preserve applicable notices |
| packageurl-python | 0.17.6 | MIT | No unusual restriction identified; preserve applicable notices |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | No unusual restriction identified; preserve applicable notices |
| pip | 26.2.1 | MIT | No unusual restriction identified; preserve applicable notices |
| pip-requirements-parser | 32.0.1 | MIT | No unusual restriction identified; preserve applicable notices |
| pip_api | 0.0.35 | Apache License
                        Version 2.0, January 2004
                     https://www.apache.org/licenses/

TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

1. Definitions.

   "License" shall mean the terms and conditions for use, reproduction,
   and distribution as defined by Sections 1 through 9 of this document.

   "Licensor" shall mean the copyright owner or entity authorized by
   the copyright owner that is granting the License.

   "Legal Entity" shall mean the union of the acting entity and all
   other entities that control, are controlled by, or are under common
   control with that entity. For the purposes of this definition,
   "control" means (i) the power, direct or indirect, to cause the
   direction or management of such entity, whether by contract or
   otherwise, or (ii) ownership of fifty percent (50%) or more of the
   outstanding shares, or (iii) beneficial ownership of such entity.

   "You" (or "Your") shall mean an individual or Legal Entity
   exercising permissions granted by this License.

   "Source" form shall mean the preferred form for making modifications,
   including but not limited to software source code, documentation
   source, and configuration files.

   "Object" form shall mean any form resulting from mechanical
   transformation or translation of a Source form, including but
   not limited to compiled object code, generated documentation,
   and conversions to other media types.

   "Work" shall mean the work of authorship, whether in Source or
   Object form, made available under the License, as indicated by a
   copyright notice that is included in or attached to the work
   (an example is provided in the Appendix below).

   "Derivative Works" shall mean any work, whether in Source or Object
   form, that is based on (or derived from) the Work and for which the
   editorial revisions, annotations, elaborations, or other modifications
   represent, as a whole, an original work of authorship. For the purposes
   of this License, Derivative Works shall not include works that remain
   separable from, or merely link (or bind by name) to the interfaces of,
   the Work and Derivative Works thereof.

   "Contribution" shall mean any work of authorship, including
   the original version of the Work and any modifications or additions
   to that Work or Derivative Works thereof, that is intentionally
   submitted to Licensor for inclusion in the Work by the copyright owner
   or by an individual or Legal Entity authorized to submit on behalf of
   the copyright owner. For the purposes of this definition, "submitted"
   means any form of electronic, verbal, or written communication sent
   to the Licensor or its representatives, including but not limited to
   communication on electronic mailing lists, source code control systems,
   and issue tracking systems that are managed by, or on behalf of, the
   Licensor for the purpose of discussing and improving the Work, but
   excluding communication that is conspicuously marked or otherwise
   designated in writing by the copyright owner as "Not a Contribution."

   "Contributor" shall mean Licensor and any individual or Legal Entity
   on behalf of whom a Contribution has been received by Licensor and
   subsequently incorporated within the Work.

2. Grant of Copyright License. Subject to the terms and conditions of
   this License, each Contributor hereby grants to You a perpetual,
   worldwide, non-exclusive, no-charge, royalty-free, irrevocable
   copyright license to reproduce, prepare Derivative Works of,
   publicly display, publicly perform, sublicense, and distribute the
   Work and such Derivative Works in Source or Object form.

3. Grant of Patent License. Subject to the terms and conditions of
   this License, each Contributor hereby grants to You a perpetual,
   worldwide, non-exclusive, no-charge, royalty-free, irrevocable
   (except as stated in this section) patent license to make, have made,
   use, offer to sell, sell, import, and otherwise transfer the Work,
   where such license applies only to those patent claims licensable
   by such Contributor that are necessarily infringed by their
   Contribution(s) alone or by combination of their Contribution(s)
   with the Work to which such Contribution(s) was submitted. If You
   institute patent litigation against any entity (including a
   cross-claim or counterclaim in a lawsuit) alleging that the Work
   or a Contribution incorporated within the Work constitutes direct
   or contributory patent infringement, then any patent licenses
   granted to You under this License for that Work shall terminate
   as of the date such litigation is filed.

4. Redistribution. You may reproduce and distribute copies of the
   Work or Derivative Works thereof in any medium, with or without
   modifications, and in Source or Object form, provided that You
   meet the following conditions:

   (a) You must give any other recipients of the Work or
       Derivative Works a copy of this License; and

   (b) You must cause any modified files to carry prominent notices
       stating that You changed the files; and

   (c) You must retain, in the Source form of any Derivative Works
       that You distribute, all copyright, patent, trademark, and
       attribution notices from the Source form of the Work,
       excluding those notices that do not pertain to any part of
       the Derivative Works; and

   (d) If the Work includes a "NOTICE" text file as part of its
       distribution, then any Derivative Works that You distribute must
       include a readable copy of the attribution notices contained
       within such NOTICE file, excluding those notices that do not
       pertain to any part of the Derivative Works, in at least one
       of the following places: within a NOTICE text file distributed
       as part of the Derivative Works; within the Source form or
       documentation, if provided along with the Derivative Works; or,
       within a display generated by the Derivative Works, if and
       wherever such third-party notices normally appear. The contents
       of the NOTICE file are for informational purposes only and
       do not modify the License. You may add Your own attribution
       notices within Derivative Works that You distribute, alongside
       or as an addendum to the NOTICE text from the Work, provided
       that such additional attribution notices cannot be construed
       as modifying the License.

   You may add Your own copyright statement to Your modifications and
   may provide additional or different license terms and conditions
   for use, reproduction, or distribution of Your modifications, or
   for any such Derivative Works as a whole, provided Your use,
   reproduction, and distribution of the Work otherwise complies with
   the conditions stated in this License.

5. Submission of Contributions. Unless You explicitly state otherwise,
   any Contribution intentionally submitted for inclusion in the Work
   by You to the Licensor shall be under the terms and conditions of
   this License, without any additional terms or conditions.
   Notwithstanding the above, nothing herein shall supersede or modify
   the terms of any separate license agreement you may have executed
   with Licensor regarding such Contributions.

6. Trademarks. This License does not grant permission to use the trade
   names, trademarks, service marks, or product names of the Licensor,
   except as required for reasonable and customary use in describing the
   origin of the Work and reproducing the content of the NOTICE file.

7. Disclaimer of Warranty. Unless required by applicable law or
   agreed to in writing, Licensor provides the Work (and each
   Contributor provides its Contributions) on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
   implied, including, without limitation, any warranties or conditions
   of TITLE, NON-INFRINGEMENT, MERCHANTABILITY, or FITNESS FOR A
   PARTICULAR PURPOSE. You are solely responsible for determining the
   appropriateness of using or redistributing the Work and assume any
   risks associated with Your exercise of permissions under this License.

8. Limitation of Liability. In no event and under no legal theory,
   whether in tort (including negligence), contract, or otherwise,
   unless required by applicable law (such as deliberate and grossly
   negligent acts) or agreed to in writing, shall any Contributor be
   liable to You for damages, including any direct, indirect, special,
   incidental, or consequential damages of any character arising as a
   result of this License or out of the use or inability to use the
   Work (including but not limited to damages for loss of goodwill,
   work stoppage, computer failure or malfunction, or any and all
   other commercial damages or losses), even if such Contributor
   has been advised of the possibility of such damages.

9. Accepting Warranty or Additional Liability. While redistributing
   the Work or Derivative Works thereof, You may choose to offer,
   and charge a fee for, acceptance of support, warranty, indemnity,
   or other liability obligations and/or rights consistent with this
   License. However, in accepting such obligations, You may act only
   on Your own behalf and on Your sole responsibility, not on behalf
   of any other Contributor, and only if You agree to indemnify,
   defend, and hold each Contributor harmless for any liability
   incurred by, or claims asserted against, such Contributor by reason
   of your accepting any such warranty or additional liability.
 | No unusual restriction identified; preserve applicable notices |
| pip_audit | 2.10.1 | OSI Approved :: Apache Software License | No unusual restriction identified; preserve applicable notices |
| platformdirs | 4.11.9 | MIT | No unusual restriction identified; preserve applicable notices |
| pluggy | 1.6.0 | MIT | No unusual restriction identified; preserve applicable notices |
| psycopg | 3.3.5 | LGPL-3.0-only | LGPL library; review binary redistribution, not an AGPL network-source obligation |
| psycopg-binary | 3.3.5 | LGPL-3.0-only | LGPL library; review binary redistribution, not an AGPL network-source obligation |
| py-serializable | 2.1.0 | Apache-2.0 | No unusual restriction identified; preserve applicable notices |
| pydantic | 2.13.4 | MIT | No unusual restriction identified; preserve applicable notices |
| pydantic-settings | 2.15.0 | MIT | No unusual restriction identified; preserve applicable notices |
| pydantic_core | 2.46.4 | MIT | No unusual restriction identified; preserve applicable notices |
| Pygments | 2.21.0 | BSD-2-Clause | No unusual restriction identified; preserve applicable notices |
| pyparsing | 3.3.2 | MIT | No unusual restriction identified; preserve applicable notices |
| pytest | 9.1.1 | MIT | No unusual restriction identified; preserve applicable notices |
| python-dotenv | 1.2.3 | BSD-3-Clause | No unusual restriction identified; preserve applicable notices |
| requests | 2.34.2 | Apache-2.0 | No unusual restriction identified; preserve applicable notices |
| rich | 15.0.0 | MIT | No unusual restriction identified; preserve applicable notices |
| sortedcontainers | 2.4.0 | Apache 2.0 | No unusual restriction identified; preserve applicable notices |
| SQLAlchemy | 2.0.51 | MIT | No unusual restriction identified; preserve applicable notices |
| starlette | 1.6.0 | BSD-3-Clause | No unusual restriction identified; preserve applicable notices |
| tomli | 2.4.1 | MIT | No unusual restriction identified; preserve applicable notices |
| tomli_w | 1.2.0 | OSI Approved :: MIT License | No unusual restriction identified; preserve applicable notices |
| typing-inspection | 0.4.4 | MIT | No unusual restriction identified; preserve applicable notices |
| typing_extensions | 4.16.0 | PSF-2.0 | No unusual restriction identified; preserve applicable notices |
| urllib3 | 2.8.0 | MIT | No unusual restriction identified; preserve applicable notices |
| uvicorn | 0.52.1 | BSD-3-Clause | No unusual restriction identified; preserve applicable notices |
| websockets | 17.1 | BSD-3-Clause | No unusual restriction identified; preserve applicable notices |

Frontend lockfile packages (optional platform records included):

| Dependency | Version | Declared license | Scope / concern |
|---|---|---|---|
| @adobe/css-tools | 4.5.0 | MIT | dev/build/test |
| @asamuzakjp/css-color | 5.1.11 | MIT | dev/build/test |
| @asamuzakjp/dom-selector | 7.1.1 | MIT | dev/build/test |
| @asamuzakjp/generational-cache | 1.0.1 | MIT | dev/build/test |
| @asamuzakjp/nwsapi | 2.3.9 | MIT | dev/build/test |
| @babel/code-frame | 7.29.7 | MIT | dev/build/test |
| @babel/helper-validator-identifier | 7.29.7 | MIT | dev/build/test |
| @babel/runtime | 7.29.7 | MIT | dev/build/test |
| @bramus/specificity | 2.4.2 | MIT | dev/build/test |
| @csstools/color-helpers | 6.1.1 | MIT-0 | dev/build/test |
| @csstools/css-calc | 3.3.0 | MIT | dev/build/test |
| @csstools/css-color-parser | 4.2.1 | MIT | dev/build/test |
| @csstools/css-parser-algorithms | 4.0.0 | MIT | dev/build/test |
| @csstools/css-syntax-patches-for-csstree | 1.1.9 | MIT-0 | dev/build/test |
| @csstools/css-tokenizer | 4.0.0 | MIT | dev/build/test |
| @exodus/bytes | 1.15.1 | MIT | dev/build/test |
| @jridgewell/sourcemap-codec | 1.5.5 | MIT | dev/build/test |
| @oxc-project/types | 0.146.0 | MIT | dev/build/test |
| @playwright/test | 1.63.0 | Apache-2.0 | dev/build/test |
| @rolldown/binding-android-arm-eabi | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/binding-android-arm64 | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/binding-darwin-arm64 | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/binding-darwin-x64 | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/binding-freebsd-x64 | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/binding-linux-arm-gnueabihf | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/binding-linux-arm64-gnu | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/binding-linux-arm64-musl | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/binding-linux-ppc64-gnu | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/binding-linux-s390x-gnu | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/binding-linux-x64-gnu | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/binding-linux-x64-musl | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/binding-openharmony-arm64 | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/binding-win32-arm64-msvc | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/binding-win32-x64-msvc | 1.2.5 | MIT | dev/build/test; optional platform |
| @rolldown/pluginutils | 1.0.1 | MIT | dev/build/test |
| @standard-schema/spec | 1.1.0 | MIT | dev/build/test |
| @testing-library/dom | 10.4.1 | MIT | dev/build/test |
| @testing-library/jest-dom | 7.0.1 | MIT | dev/build/test |
| dom-accessibility-api | 0.6.3 | MIT | dev/build/test |
| @testing-library/react | 16.3.2 | MIT | dev/build/test |
| @testing-library/user-event | 14.6.6 | MIT | dev/build/test |
| @types/aria-query | 5.0.4 | MIT | dev/build/test |
| @types/chai | 5.2.3 | MIT | dev/build/test |
| @types/deep-eql | 4.0.2 | MIT | dev/build/test |
| @types/estree | 1.0.9 | MIT | dev/build/test |
| @types/node | 26.3.0 | MIT | dev/build/test |
| @types/react | 19.2.18 | MIT | dev/build/test |
| @types/react-dom | 19.2.5 | MIT | dev/build/test |
| @typescript/typescript-aix-ppc64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-darwin-arm64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-darwin-x64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-freebsd-arm64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-freebsd-x64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-linux-arm | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-linux-arm64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-linux-loong64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-linux-mips64el | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-linux-ppc64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-linux-riscv64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-linux-s390x | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-linux-x64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-netbsd-arm64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-netbsd-x64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-openbsd-arm64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-openbsd-x64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-sunos-x64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-win32-arm64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @typescript/typescript-win32-x64 | 7.0.2 | Apache-2.0 | dev/build/test; optional platform |
| @vitejs/plugin-react | 6.1.0 | MIT | dev/build/test |
| @vitest/expect | 4.1.11 | MIT | dev/build/test |
| @vitest/mocker | 4.1.11 | MIT | dev/build/test |
| @vitest/pretty-format | 4.1.11 | MIT | dev/build/test |
| @vitest/runner | 4.1.11 | MIT | dev/build/test |
| @vitest/snapshot | 4.1.11 | MIT | dev/build/test |
| @vitest/spy | 4.1.11 | MIT | dev/build/test |
| @vitest/utils | 4.1.11 | MIT | dev/build/test |
| ansi-regex | 5.0.1 | MIT | dev/build/test |
| ansi-styles | 5.2.0 | MIT | dev/build/test |
| aria-query | 5.3.0 | Apache-2.0 | dev/build/test |
| assertion-error | 2.0.1 | MIT | dev/build/test |
| bidi-js | 1.0.3 | MIT | dev/build/test |
| chai | 6.2.2 | MIT | dev/build/test |
| convert-source-map | 2.0.0 | MIT | dev/build/test |
| css-tree | 3.2.1 | MIT | dev/build/test |
| css.escape | 1.5.1 | MIT | dev/build/test |
| csstype | 3.2.3 | MIT | dev/build/test |
| data-urls | 7.0.0 | MIT | dev/build/test |
| decimal.js | 10.6.0 | MIT | dev/build/test |
| dequal | 2.0.3 | MIT | dev/build/test |
| detect-libc | 2.1.2 | Apache-2.0 | dev/build/test |
| dom-accessibility-api | 0.5.16 | MIT | dev/build/test |
| entities | 8.0.0 | BSD-2-Clause | dev/build/test |
| es-module-lexer | 2.3.2 | MIT | dev/build/test |
| estree-walker | 3.0.3 | MIT | dev/build/test |
| expect-type | 1.4.0 | Apache-2.0 | dev/build/test |
| fdir | 6.5.0 | MIT | dev/build/test |
| fsevents | 2.3.3 | MIT | dev/build/test; optional platform |
| html-encoding-sniffer | 6.0.0 | MIT | dev/build/test |
| indent-string | 4.0.0 | MIT | dev/build/test |
| is-potential-custom-element-name | 1.0.1 | MIT | dev/build/test |
| js-tokens | 4.0.0 | MIT | dev/build/test |
| jsdom | 29.1.1 | MIT | dev/build/test |
| lightningcss | 1.33.0 | MPL-2.0 | dev/build/test; file-level copyleft |
| lightningcss-android-arm64 | 1.33.0 | MPL-2.0 | dev/build/test; optional platform; file-level copyleft |
| lightningcss-darwin-arm64 | 1.33.0 | MPL-2.0 | dev/build/test; optional platform; file-level copyleft |
| lightningcss-darwin-x64 | 1.33.0 | MPL-2.0 | dev/build/test; optional platform; file-level copyleft |
| lightningcss-freebsd-x64 | 1.33.0 | MPL-2.0 | dev/build/test; optional platform; file-level copyleft |
| lightningcss-linux-arm-gnueabihf | 1.33.0 | MPL-2.0 | dev/build/test; optional platform; file-level copyleft |
| lightningcss-linux-arm64-gnu | 1.33.0 | MPL-2.0 | dev/build/test; optional platform; file-level copyleft |
| lightningcss-linux-arm64-musl | 1.33.0 | MPL-2.0 | dev/build/test; optional platform; file-level copyleft |
| lightningcss-linux-x64-gnu | 1.33.0 | MPL-2.0 | dev/build/test; optional platform; file-level copyleft |
| lightningcss-linux-x64-musl | 1.33.0 | MPL-2.0 | dev/build/test; optional platform; file-level copyleft |
| lightningcss-win32-arm64-msvc | 1.33.0 | MPL-2.0 | dev/build/test; optional platform; file-level copyleft |
| lightningcss-win32-x64-msvc | 1.33.0 | MPL-2.0 | dev/build/test; optional platform; file-level copyleft |
| lru-cache | 11.5.2 | BlueOak-1.0.0 | dev/build/test |
| lz-string | 1.5.0 | MIT | dev/build/test |
| magic-string | 0.30.21 | MIT | dev/build/test |
| mdn-data | 2.27.1 | CC0-1.0 | dev/build/test |
| min-indent | 1.0.1 | MIT | dev/build/test |
| nanoid | 3.3.18 | MIT | dev/build/test |
| obug | 2.1.4 | MIT | dev/build/test |
| parse5 | 8.0.1 | MIT | dev/build/test |
| pathe | 2.0.3 | MIT | dev/build/test |
| picocolors | 1.1.1 | ISC | dev/build/test |
| picomatch | 4.0.7 | MIT | dev/build/test |
| playwright | 1.63.0 | Apache-2.0 | dev/build/test |
| playwright-core | 1.63.0 | Apache-2.0 | dev/build/test |
| postcss | 8.5.26 | MIT | dev/build/test |
| pretty-format | 27.5.1 | MIT | dev/build/test |
| punycode | 2.3.1 | MIT | dev/build/test |
| react | 19.2.8 | MIT | runtime; include MIT notice in distribution |
| react-dom | 19.2.8 | MIT | runtime; include MIT notice in distribution |
| react-is | 17.0.2 | MIT | dev/build/test |
| redent | 3.0.0 | MIT | dev/build/test |
| require-from-string | 2.0.2 | MIT | dev/build/test |
| rolldown | 1.2.5 | MIT | dev/build/test |
| saxes | 6.0.0 | ISC | dev/build/test |
| scheduler | 0.27.0 | MIT | runtime; include MIT notice in distribution |
| siginfo | 2.0.0 | ISC | dev/build/test |
| source-map-js | 1.2.1 | BSD-3-Clause | dev/build/test |
| stackback | 0.0.2 | MIT | dev/build/test |
| std-env | 4.2.0 | MIT | dev/build/test |
| strip-indent | 3.0.0 | MIT | dev/build/test |
| symbol-tree | 3.2.4 | MIT | dev/build/test |
| tinybench | 2.9.0 | MIT | dev/build/test |
| tinyexec | 1.3.0 | MIT | dev/build/test |
| tinyglobby | 0.2.17 | MIT | dev/build/test |
| tinyrainbow | 3.1.1 | MIT | dev/build/test |
| tldts | 7.4.11 | MIT | dev/build/test |
| tldts-core | 7.4.11 | MIT | dev/build/test |
| tough-cookie | 6.0.2 | BSD-3-Clause | dev/build/test |
| tr46 | 6.0.0 | MIT | dev/build/test |
| typescript | 7.0.2 | Apache-2.0 | dev/build/test |
| undici | 7.29.0 | MIT | dev/build/test |
| undici-types | 8.3.0 | MIT | dev/build/test |
| vite | 8.2.2 | MIT | dev/build/test |
| vitest | 4.1.11 | MIT | dev/build/test |
| w3c-xmlserializer | 5.0.0 | MIT | dev/build/test |
| webidl-conversions | 8.0.1 | BSD-2-Clause | dev/build/test |
| whatwg-mimetype | 5.0.0 | MIT | dev/build/test |
| whatwg-url | 16.0.1 | MIT | dev/build/test |
| why-is-node-running | 2.3.0 | MIT | dev/build/test |
| xml-name-validator | 5.0.0 | Apache-2.0 | dev/build/test |
| xmlchars | 2.2.0 | MIT | dev/build/test |

## 17. GitHub public-repository implications

Under the GitHub Terms retrieved for this audit, you retain ownership but must have rights to post others’ work. Public visibility permits other GitHub users to view/fork and exercise specified uses through the service; forks can persist. This is not automatically an unrestricted open-source license. The current terms also expressly include GitHub/affiliate AI-development/training rights in §D.4; the §J.3 input/output opt-out does not override the public-content grants. A missing LICENSE therefore does not promise prevention of all copying or training. [GitHub Terms, current 27 April 2026 version, §§D/J](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)

Before publication, confirm rights to contributors’ code and the logo, not merely ownership of the repository account. Git history shows multiple authors and no general inbound/outbound project license establishing a broad relicensing grant. Review any school/employer/group-project agreement. No allegation of infringement is made; the repository cannot prove off-repository permissions.

## 18. Recommended repository licensing approach

The owner has now explicitly chosen **A: a public source-visible portfolio, without intentionally granting broad reuse rights**. Leaving the repository without a general software LICENSE is appropriate for that goal. No license was added; README now explains the default-copyright scope, GitHub platform rights and separate data/dependency licenses.

| Approach | Consequence | Fit |
|---|---|---|
| **A. Source-visible portfolio, normal copyright retained** | No general software LICENSE means default copyright applies, subject to GitHub terms and statutory exceptions. An explicit scope/copyright statement can reduce confusion; do not call it open source. | Closest conservative fit to the stated current portfolio-only goal until reuse permission is chosen. |
| **B. MIT** | Allows broad reuse/modification/distribution/commercial use with copyright/permission notices; contains warranty disclaimer, no express patent grant. | Simple choice if all relevant owners actively want open reuse. |
| **B. Apache-2.0** | Broad reuse plus explicit contributor patent grant/termination and additional notice/change obligations; no trademark license. | Consider if explicit patent terms matter and maintainers will manage notices. |

Sources: [GitHub licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository), [MIT text](https://opensource.org/license/mit), [Apache-2.0 text](https://www.apache.org/licenses/LICENSE-2.0.html).

**Decision recorded:** keep A and no general software LICENSE. The README rights/scope statement is implemented. Adopting MIT merely to make a public repository look complete is unnecessary. If the owner later selects B, first obtain authority for that broader grant and use a clearly scoped license. Whichever approach is chosen, exclude/identify reference datasets under their existing CC0/CC BY terms and handle logo/trademarks separately. You cannot relicense other contributors’ rights without authority or rescind GeoNames attribution. Counsel is useful for disputed joint/employment ownership, not automatically necessary to add a properly authorized standard license.

## 19. User-generated-content risks

Names and profile fields accept arbitrary short text, including potentially defamatory statements, third-party information or copyrighted expression. A length cap and XSS escaping do not make the content lawful. Private rooms reduce exposure but do not eliminate it; classmates may screenshot information. No public searchable content feed or upload feature was found.

**Scaled recommendation:** for current supervised demos, provide a short “about yourself only; no contact details, secrets, harassment or copied protected content” instruction, host supervision and an operator contact. Before public promotion, add appropriate Terms, a reporting/removal route and a documented response process. The host can remove a player before play, but cannot currently erase a finished database record through the UI. Avoid unnecessary persistence. Do not build an enterprise moderation system without evidence of need.

Privacy purpose/consent duties remain relevant to third-party information, and copyright distinguishes facts from copied expression. These recommendations do not assume a blanket safe harbor or a universal proactive moderation mandate. [PPA privacy tool](https://mojforms.justice.gov.il/mojaemprivacyprotectionauthority/dpiaform.html), [Copyright Act](https://www.wipo.int/wipolex/en/text/202010), [Render acceptable use](https://render.com/acceptable-use)

## 20. Retention/deletion analysis

Verified `main.py`, settings, repository deletion code and `GameHub` behavior:

| Event/data | Actual outcome |
|---|---|
| Profile submitted | All provided fields/flags retained in server memory, including opted-out fields. No immediate database write. |
| Answers during game | Server holds answer/score state; not individually streamed to DB as permanent events. |
| FINISHED | Best-effort executor saves the full game aggregate: profiles, players, questions/options/explanations, answers and totals. No durable retry queue was found. |
| After finish | Live room is not immediately erased; connected clients can continue seeing results. |
| All sockets gone | Idle sweep can remove room after default 120 minutes of inactivity. Sweep runs every 300 seconds. |
| Connected room remains | No absolute maximum age for its in-memory profile data. |
| Database cleanup | On startup and every 300 seconds: oldest eligible FINISHED games with `updated_at` older than configured seven days, at most 100 per run; child rows removed through ORM cascades. Active games excluded. |
| Render sleeps/stops or cleanup fails | No wall-clock deletion guarantee; later startup/runs catch up. Large backlog requires multiple batches. |
| Render restarts | Active rooms/credentials disappear; finished snapshots in Neon remain until deletion. |
| User leaves / Play again | Browser session data cleared and connection ends; does not delete stored profile/results. |
| User access/correction/deletion request | No UI/contact workflow. Internal repository delete exists, but no public delete endpoint. |
| Host deletes room/game | Not implemented as a general privacy deletion feature; pregame removal differs from finished-data erasure. |
| Provider backups / PITR / logs | Not verified. Deleting live rows does not prove all backup copies are erased immediately. |

The default seven days is a product setting, **not a statutory retention period**. Retaining opted-out profiles without a clear postgame purpose deserves review; no account/history feature was found that explains needing those complete values. Document necessity and review excess information at least as applicable under the security regulations; do not promise deletion the architecture cannot guarantee. [Data security regulations, database definition/minimization provisions](https://www.gov.il/BlobFolder/generalpage/1files/he/IT2017.pdf)

An operational rights process can initially be manual: locate the correct game/person with minimal verification, avoid disclosing classmates’ profiles, correct/remove appropriate linked records, address active-memory state and explain backup limitations. Statutory access/correction requirements and conditional deletion are distinct from a voluntary “delete everything anytime” product promise. [PPA professional guide](https://www.gov.il/BlobFolder/reports/guide_tikon13_professional/he/tikun%2013%20_170825.pdf)

## 21. Security/privacy readiness

`SECURITY_AUDIT_REPORT.md` was used as prior evidence and its relevant controls checked against current main. The merged shutdown ordering, bounded retention, connection limits, name normalization and validation changes are present; the earlier audit was not accepted solely on its title.

| Control | Present evidence / limitation |
|---|---|
| Host/player authorization | Separate unpredictable opaque credentials; memory digests/constant-time comparisons; role-bound WebSocket resolution; no DB plaintext token storage. |
| Transport | Live HTTPS pages load; backend health retry returns `200 {"status":"ok"}`. Source supports WSS and requires HTTPS production origins/DB TLS configuration. Actual Neon URL/region was not inspected. |
| Origin/access scope | Explicit HTTP/WS Origin validation and role checks present; no cookie ambient authentication. Token theft remains relevant to browser XSS; generic CSRF middleware is not automatically needed. |
| Consent derivation | Generation uses consented dataset only; opted-out movie/song/artist/music/food/hobby/city data excluded from semantic derivation. Storage remains a separate P1/P2 issue. |
| Answer confidentiality | Active public schema omits correct answer/explanation/internal metadata; instrumented classroom tests assert absence in active frames. |
| XSS/SQL/input | React text rendering; bounded/strict payloads; SQLAlchemy-bound operations; no user-controlled raw SQL or HTML sink identified in relevant app paths. |
| Errors/logging | Generic errors; production access logs disabled; no raw profiles/credentials in inspected application logging. Infrastructure logs not inspected. |
| Secrets | Current-tree/build and reachable-history scanner results below; no credential value printed. |
| Live headers | Frontend: HSTS/nosniff, but CSP/referrer/frame/permissions headers absent in this observation despite blueprint controls. API health: no-store, no-referrer, nosniff, DENY. Pages: HSTS; additional headers not observed. |
| Deployment limitation | Exact deployed SHA unknown; do not claim all current-main controls are deployed. Header drift warrants verification before promotion, not an unauthorized deployment. |

Focused backend verification: **264 passed, 3 skipped, 1006 deselected, 2 deprecation warnings**. Skips are PostgreSQL lifecycle/integration tests requiring `MIZEMI_TEST_POSTGRES_URL`; no real Neon testing was performed. No immediate active exposure was established that required halting this audit.

## 22. Public GitHub data check

| Check | Result / scope |
|---|---|
| Current-tree secrets scanner | **256 source/config files; 0 high-confidence findings; 0 real-env files** after local build; includes current/untracked source and build output. Temporary audit test helpers were present during this count. |
| Reachable-history secrets scanner | **563 reachable Git blobs; 0 findings**, including deleted content. Not a proof against arbitrary low-entropy or unrecognized secrets. |
| Independent filename/content review | No tracked or historical `.env`, SQLite/DB dump, production log, backup/export or private screenshot discovered in inspected paths. Only logo PNGs tracked. Ignored local files do exist: `backend/mizemi.db` has zero rows; `frontend/.e2e.db` has six games/22 players, with all 56 distinct profile values and eight distinct names matching the committed synthetic E2E sources/fixture. Local screenshots follow those test scenarios; their entire visual contents were not individually certified. Keep these DBs/screenshots ignored. |
| Email-like text in HEAD | Matches limited to nine validation/security test files; inspected as test literals rather than collected user contacts. Values intentionally not repeated here. |
| Git authorship | All **138 reachable commits**, including authors, committers and coauthor trailers, checked in §28. There are five potentially private human email strings, one generic GitHub committer address and one generic AI-tool address. All 138 commits have a potentially private human author address; this is an intentional-disclosure review, not a credential leak. Exact SHAs and masked identity mapping are below. |
| Fixtures/reports | Code-generated or visibly synthetic classroom examples; no evidenced real participant export. Author confirmation remains needed for ambiguous hand-authored examples. |
| Public reference people | Artist names/IDs occur intentionally in licensed reference data; these are not private participant profiles. |
| Original local changes | Protected lockfile metadata change preserved. Original checkout had no unrelated untracked files at initial inspection. |
| GitHub account surfaces | Follow-up: 52 issue/PR records, zero issue/review comments, zero releases, all 32 available workflow log archives (72 log files) inspected/scanned; no credential findings or attachment references. The only Actions artifact is an expired `github-pages` artifact, not downloadable for reinspection. Render/Neon private logs were not accessed and are not repository contents. See §28.5 for limits. |

Before publication, confirm authors are intentionally attributed with these addresses and that examples/images are authorized. Do not rewrite shared history automatically; changing a Git email preference only affects future commits. If actual private content is identified, resolve consent/removal/history implications first. The report itself deliberately omits full private author email addresses and credentials.

## 23. GitHub Pages legal requirements

The landing page is currently a static portfolio entry point: no forms, scripts, trackers or external assets; local logo and links to Render/GitHub. Actual live page returned HTTP 200, showed a skip link and keyboard focus, and reflowed at 320px without horizontal scrolling.

| Item | Now | Before broad service promotion |
|---|---|---|
| Privacy link | RECOMMENDED because it funnels visitors to a data-collecting demo; disclose provider traffic logging where appropriate. Code publication alone does not create a universal page requirement. | Link the service notice prominently and provide collection notice inside the app. |
| Terms link | OPTIONAL for pure portfolio; helpful demo rules | STRONGLY RECOMMENDED public-service Terms link |
| Accessibility statement | Conditional on service applicability/exemption; recommended honest contact route | REQUIRED where applicable; one accessible statement may cover both properties if accurate |
| Legal disclaimer | OPTIONAL factual demo/availability notice | Useful, not a substitute for statutory rights or a guarantee of immunity |
| Copyright notice | RECOMMENDED accurate ownership scope | Keep accurate, especially with multiple contributors |
| License link | RECOMMENDED to explain source-visible versus open-source status and dataset exceptions | Keep code/data/brand scopes distinct |

GitHub Pages documentation confirms visitor IP logging. GitHub’s additional product terms restrict using Pages as free hosting for a commercial business/e-commerce/SaaS site while allowing appropriate project showcases; revisit hosting terms if the portfolio becomes a commercial-service destination. The live application is already hosted separately on Render. [Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages), [GitHub additional product terms](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features)

## 24. Checklist A — before Public GitHub

These gates concern publishing source/history. Do not turn every service improvement into a repository-publication condition.

- [ ] **REQUIRED / L1:** Confirm logo generation/account authority and permission for any reference artwork or manually added stock/font/icon elements. One PNG is reused at three paths; embedded OpenAI claims do not establish the account holder. See §28.2.
- [ ] **REQUIRED / L1:** Confirm authority to publish the contributions/history of Gavriel Alafi, Elick Chitrit and Uriel Israel Mizrahi, including any employer/institution rights and any externally sourced code they supplied. No broad MIT/Apache grant is requested. See §28.1.
- [ ] **RECOMMENDED / L2; gate if unintended:** Confirm that you and the three contributors intend to expose the names and five human email variants in §28.3. All exact affected SHAs are listed. If a person objects, keep the repository private while agreeing on remediation; no history rewrite was performed.
- [x] **REQUIRED for licensed data — VERIFIED:** Knowledge `LICENSES.md`, manifest, build documentation and bilingual application credits are committed; GeoNames attribution/license/change notice and Wikidata CC0 scope are present. All eight data hashes match. Preserve these notices.
- [x] **RECOMMENDED decision — RESOLVED:** Owner selected source-visible/default copyright. README documents it and preserves separately licensed material. No general LICENSE is required or added; do not describe the application software as open source.
- [x] **RECOMMENDED final hygiene — VERIFIED for the audited revision:** Repeat working-tree/history/message scans, independent artifact/content review and read-only GitHub checks completed; results in §28.5. No new hygiene blocker found. Recheck if content changes before publication; keep local DBs/screenshots and the protected lockfile change excluded.
- [x] **Accuracy reviewed:** No anonymity, zero-storage or certified-accessibility claim found. Existing README describes a seven-day retention policy; the operational exceptions are documented in §20. Clarifying service-facing retention language remains a service-readiness recommendation, not a new source-publication blocker in this follow-up.

No cookie banner, new Terms contract, generic MIT license or completed commercial launch is a precondition merely to show source. The already-live demo still has its own obligations independently of clicking “Make public.”

## 25. Checklist B — before public service launch

- [ ] Identify the real operator/controller, intended territories, whether a school/public body is involved, revenue/turnover and adult/child audience.
- [ ] Publish accurate collection disclosure and a linked privacy notice in the languages used; explain derivation, classmate visibility, providers and the question-use/storage distinction. Address this before further real-user demos too.
- [ ] Decide and document minimal postgame storage/purpose. Resolve opted-out-field persistence and connected-room lifetime concerns; test the chosen retention and do not overpromise backups/log deletion.
- [ ] Establish authenticated access/correction/applicable deletion and sharing-withdrawal assistance, a contact and an incident procedure.
- [ ] Confirm Render/Neon account terms, regions, subprocessors, logs/backups and applicable Israeli transfer/security/outsourcing arrangements. Determine database security tier and any DPO/register/notification trigger from actual facts.
- [ ] Determine accessibility applicability/exemption; fix measured contrast/ARIA issues, validate focus/form errors, test real screen-reader and zoom journeys, and assess timed-game accommodations. Publish a truthful statement if required.
- [ ] Preserve full required third-party notices in the distributed frontend; review any future distributed wheel/container’s native-license obligations.
- [ ] If children will use it, obtain specialist school/minor privacy review and implement the resulting audience/notice/authorization design before that use. An age sentence alone is insufficient.
- [ ] Adopt proportionate participation rules/Terms and a reporting/removal contact. Do not require elaborate automated moderation for a small supervised pilot without need.
- [ ] Verify deployed revision/security configuration and header drift; rerun relevant security/dependency tests and observe remote CI after any future authorized change. Explain cold starts, room loss on restart and no multi-instance recovery.
- [ ] Recheck GitHub Pages hosting terms if marketing/commercial use changes. Reassess cookies/foreign law only if new functionality or targeting makes it relevant.

## 26. Items requiring a real lawyer; explicit answers and verification

Professional review is most valuable for: uncertain coauthor/employer/logo rights; whether this public demo falls outside the personal-use database exception; actual security tier/outsourcing/cross-border arrangements; institutional/public-body operation; children; disputed accessibility exemption/current economic thresholds; and public-service contract/disclaimer enforceability. A qualified accessibility professional should assess actual standards compliance and timing accommodations. Do not pay for a generic cookie banner or automatic database registration without checking the facts.

### Explicit owner answers

| # | Question | Answer and confidence |
|---|---|---|
| 1 | Can I make the repository public now? | **YES, AFTER FIXING LISTED BLOCKERS — MEDIUM.** Confirm logo/contribution publication authority and resolve any unintended personal disclosures. No incompatible imported bulk-data license found. |
| 2 | Do I currently need a Privacy Policy? | **LIKELY REQUIRED for the live demo; not solely for source publication — MEDIUM.** An accurate collection notice is the legal focus; operator/personal-use exception remains unconfirmed. |
| 3 | Do I currently need Terms of Use? | **OPTIONAL for the controlled demo; STRONGLY RECOMMENDED before promotion — MEDIUM.** No universal standalone-Terms mandate identified for this setup. |
| 4 | Do I currently need an Accessibility Statement? | **LEGAL REVIEW REQUIRED / conditional — LOW until operator and exemption facts are confirmed.** Required if covered/non-exempt; truthful statement/contact recommended otherwise. |
| 5 | Does MiZeMi need a cookie banner? | **No current technical basis — HIGH for inspected app.** Only functional session/language storage found; provider changes and future tracking require reassessment. |
| 6 | Registration or notification? | **Does not currently appear required — MEDIUM.** Assumes private operator, non-brokerage purpose and small participant population; public-body operation or scale could change it. |
| 7 | Are knowledge sources safe to redistribute? | **Identified imported sources: yes, with existing conditions — HIGH on terms, MEDIUM on complete provenance.** CC0 and CC BY 4.0, not MusicBrainz supplementary data or unclear government CSV. Local contributor authority still needs confirmation. |
| 8 | Is LICENSE recommended; which approach? | **Keep no general software LICENSE for the now-confirmed source-visible preference — HIGH.** README explains default copyright and platform rights; data/dependency licenses retain their separate scope. No MIT/Apache grant added. |
| 9 | Any personal information in repository? | **Yes — HIGH.** Git author names/emails and public reference-person names. No evidenced real participant export/credential; confidence MEDIUM for absence of all private fixture data. |
| 10 | Before “Make public”? | **Checklist A — HIGH on actions, MEDIUM on unresolved facts.** Only contributor publication authority, logo account/input rights and intentional Git-identity disclosure remain unresolved; dataset notices, licensing preference and repeated hygiene checks are complete in §28. |
| 11 | Before advertising to the public? | **Checklist B — HIGH on identified engineering gaps, MEDIUM on conditional legal applicability.** Notice/rights/retention/provider arrangements, accessibility, notices in build, audience rules and deployed verification. |

### Exact audit verification matrix

| Check | Command/method | Result |
|---|---|---|
| Git baseline | `git status --short`, branch/log, fetch `origin`, isolated worktree | Audited `eca8bdc`; original metadata change preserved |
| Data flow/storage | Schemas + game/profile models + ORM mapper + realtime handlers + frontend storage inspection | Inventory above verified against code |
| Focused privacy/security tests | `.venv/bin/python -m pytest backend/tests -q -k 'consent or retention or security or credentials or persistence or profile_dataset or knowledge_base' -rs` | **264 passed, 3 skipped, 1006 deselected; 2 deprecation warnings; 6.94s** |
| PostgreSQL checks | Same selection | **NOT EXECUTED:** three selected tests skipped; no disposable PostgreSQL URL configured |
| Browser game/a11y sampling | `npm run test:e2e -- legal-audit.spec.ts` temporary instrumentation of existing scenarios | **3 passed, 43.0s**; 21 axe samples; actual violations listed above |
| Keyboard-only extra journey / 200% text | Temporary `legal-keyboard.spec.ts`, native Tab/Enter/type input | **1 passed, 4.4s**: Tab-only navigation, text/type-ahead selection, Enter activation, validation, three players, one round, final results and leave. 200% root-text profiles had no overflow. Earlier temporary-helper attempts failed because dropdown selection was not committed / a button label was wrong; helpers corrected, product unchanged. |
| Build | Normal `npm run build` through Playwright webServer setup | Passed; no product edits; third-party notice omission found |
| Live pages | Read-only Chromium loads, Tab sequence, axe, 320/390/640px, reduced-motion emulation | Frontend/Pages 200; no cookie or external embedded script; 0 automatic homepage violations with incomplete checks |
| Live backend health | One initial browser attempt returned HTML; subsequent read-only HTTP request | Retry: 200 JSON `{"status":"ok"}`; no DB details; initial response cause not established |
| Live production game/WS | No production room creation or multiplayer probing during this audit | **NOT EXECUTED**; locally tested instead |
| Current-tree secrets | `python3 scripts/check_secrets.py` | 256 files, 0 findings, 0 local real-env files |
| History secrets | `python3 scripts/check_secrets.py --history` | 563 reachable blobs, 0 findings |
| Independent data review | File/history-path inventory, email-pattern paths only, fixture/build-script inspection | Author metadata disclosed above; no found private exports/media |
| Knowledge integrity/content | All manifest hashes + schema/field/string-length inspection | Eight hashes match; 33,831 entities; no prose/media schema |
| Dependency licenses | npm lock/package metadata and Python installed metadata/license files | 164 npm + 51 Python records; scoped exceptions above |
| Real screen-reader / native browser zoom certification | VoiceOver/NVDA and comprehensive native 200%/400% zoom | **NOT EXECUTED**; no conformance claim |
| Full backend/frontend CI, vulnerability audits | Not necessary to rerun all stages for this report-only legal audit | **NOT EXECUTED** as a new full release certification |
| Diff integrity | `git diff --check`; original lockfile SHA-256 compared | Passed on the isolated audit source and original tracked diff; protected original lockfile hash unchanged (`5ce92a07171ded0100886b0ef3ffaacc27f51eefa6f55cea9850c8fa9e82411f`). Report whitespace separately checked. |

No product fixes or commits were created. Temporary local audit test files were removed after inspection; synthetic build/test outputs remain ignored. The publication follow-up modifies only README.md and this report, both in the original workspace. The isolated audit branch remains based on the audited SHA. The unrelated frontend/package-lock.json modification is preserved.

## 27. Sources

All sources below were retrieved **2026-09-17**. Some gov.il pages/PDFs blocked direct fetching (403); the indexed official document text was available and used. This access limitation and inconsistent official accessibility-threshold pages lower confidence where noted. Drafts were not treated as enacted law; the cross-border analysis uses the final April 2026 opinion, not its 2024 consultation draft. WIPO copyright text is a legislative translation/source for the stable provisions cited, not a claim to have reviewed every later amendment.

| ID | Page/document title and URL | Classification | Retrieved | Supports |
|---|---|---|---|---|
| S01 | [Questions and answers — Amendment 13 to the Protection of Privacy Law](https://www.gov.il/he/pages/tikun13_qa?chapterIndex=6) | OFFICIAL GUIDANCE | 2026-09-17 | Scope, effective date, remaining duties |
| S02 | [Protection of Privacy Law (Amendment 13), 2024 — Official Gazette 3287](https://www.gov.il/BlobFolder/legalinfo/standards_law/he/laws_standards-law_law3287.pdf) | LAW | 2026-09-17 | Revised definitions, purpose/authorization, section 11 and registration/notification thresholds |
| S03 | [Privacy Protection Authority — digital privacy impact assessment tool](https://mojforms.justice.gov.il/mojaemprivacyprotectionauthority/dpiaform.html) | OFFICIAL GUIDANCE | 2026-09-17 | Purpose, rights and proportionate privacy risk review |
| S04 | [Professional guide — Amendment 13 to the Protection of Privacy Law](https://www.gov.il/BlobFolder/reports/guide_tikon13_professional/he/tikun%2013%20_170825.pdf) | OFFICIAL GUIDANCE | 2026-09-17 | Rights, duties and remedies after Amendment 13 |
| S05 | [Protection of Privacy Regulations (Data Security), 2017](https://www.gov.il/BlobFolder/generalpage/1files/he/IT2017.pdf) | REGULATION | 2026-09-17 | Security duties, minimization, tier-dependent requirements |
| S06 | [Full guide to implementing the Data Security Regulations](https://www.gov.il/BlobFolder/guide/data_security_guide/he/NEW_GUIDE.pdf) | OFFICIAL GUIDANCE | 2026-09-17 | Regulation 21 tier table; individual-managed category |
| S07 | [Questions and answers — Data Security Regulations](https://www.gov.il/he/pages/data_security_fqa?chapterIndex=6) | OFFICIAL GUIDANCE | 2026-09-17 | Provider/authorized-user responsibility; updated 4 March 2026 |
| S08 | [Report a serious security incident in a database](https://www.gov.il/he/service/report-of-data-breach) | OFFICIAL GUIDANCE | 2026-09-17 | Tier/event-dependent incident reporting |
| S09 | [EEA-origin information regulations — questions and answers](https://www.gov.il/he/pages/europe_transfer?chapterIndex=6) | OFFICIAL GUIDANCE | 2026-09-17 | Conditional extra deletion/accuracy/minimization/notice duties |
| S10 | [Registration in the database register](https://www.gov.il/he/service/registration_in_the_database) | OFFICIAL GUIDANCE | 2026-09-17 | Current registration service and eligibility |
| S11 | [Notification obligation for a database](https://www.gov.il/he/service/notice-obligation) | OFFICIAL GUIDANCE | 2026-09-17 | Over-100,000 specially sensitive data-subject threshold |
| S12 | [Removal of database registration](https://www.gov.il/he/service/registered_database_deletion) | OFFICIAL GUIDANCE | 2026-09-17 | Transition treatment for already registered databases |
| S13 | [Duty to notify when collecting personal information under section 11](https://www.gov.il/BlobFolder/legalinfo/duty_to_notify/he/notify13.pdf) | OFFICIAL GUIDANCE | 2026-09-17 | Collection disclosure elements |
| S14 | [Opinion on consent under privacy law — final 2026 publication](https://www.gov.il/BlobFolder/legalinfo/consent-2026/he/cpncent-2025.pdf) | OFFICIAL GUIDANCE | 2026-09-17 | Informed/free choice and highlighting unexpected processing |
| S15 | [Website accessibility — who must make their sites accessible](https://www.gov.il/he/pages/website_accessibility?chapterIndex=3) | OFFICIAL GUIDANCE | 2026-09-17 | Covered public-service scope |
| S16 | [Website accessibility — exemptions and reduced requirements](https://www.gov.il/he/pages/website_accessibility?chapterIndex=8) | OFFICIAL GUIDANCE | 2026-09-17 | Current Commission economic-exemption guidance; factual eligibility unresolved |
| S17 | [Equal Rights for Persons with Disabilities Regulations (Service Accessibility Adjustments), 2013](https://www.gov.il/BlobFolder/guide/accommodating_service_providing_rules/he/sitedocs_service_acessibility_regulations.pdf) | REGULATION | 2026-09-17 | Internet-service duties, statements and exemptions; verify current consolidated application |
| S18 | [IS 5568 Part 1, September 2023 — Web Content Accessibility Guidelines: Website Accessibility](https://www.gov.il/BlobFolder/legalinfo/israeli_accessibility_standards_pdf/he/sitedocs_si-5568-1-september-2023.pdf) | OFFICIAL STANDARD | 2026-09-17 | WCAG 2.0 basis and national modifications |
| S19 | [Standards Institution of Israel — IS 5568 Part 1 catalog](https://www.sii.org.il/lobby/standardization/standard-page/?id=6751) | OFFICIAL STANDARD CATALOG | 2026-09-17 | Identity/date of current standard |
| S20 | [Accessibility statement and information about website accessibility arrangements](https://www.gov.il/he/pages/declaration_website_accessibility?chapterIndex=1) | OFFICIAL GUIDANCE | 2026-09-17 | Statement contents and contact information |
| S21 | [Understanding SC 1.4.3 — Contrast (Minimum)](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) | BEST PRACTICE / TECHNICAL GUIDANCE | 2026-09-17 | Measured answer-text contrast interpretation |
| S22 | [Understanding SC 2.4.3 — Focus Order](https://www.w3.org/WAI/WCAG22/Understanding/focus-order.html) | BEST PRACTICE / TECHNICAL GUIDANCE | 2026-09-17 | Focus sequence and dynamic-stage review |
| S23 | [Understanding SC 3.3.1 — Error Identification](https://www.w3.org/WAI/WCAG22/Understanding/error-identification.html) | BEST PRACTICE / TECHNICAL GUIDANCE | 2026-09-17 | Error usability review |
| S24 | [Understanding SC 4.1.3 — Status Messages](https://www.w3.org/WAI/WCAG22/Understanding/status-messages.html) | BEST PRACTICE / TECHNICAL GUIDANCE | 2026-09-17 | Live game update announcements; newer-WCAG best practice |
| S25 | [Understanding SC 2.2.1 — Timing Adjustable](https://www.w3.org/WAI/WCAG22/Understanding/timing-adjustable.html) | BEST PRACTICE / TECHNICAL GUIDANCE | 2026-09-17 | Real-time/essential exceptions require assessment |
| S26 | [Render Terms of Service](https://render.com/terms) | PLATFORM TERMS | 2026-09-17 | Customer content duties and incorporated DPA |
| S27 | [GitHub Terms of Service, 27 April 2026](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) | PLATFORM TERMS | 2026-09-17 | Public forks, ownership, publication authority and current AI-related grants |
| S28 | [Legal Capacity and Guardianship Law, 1962 — official consolidated text, 2025](https://www.gov.il/BlobFolder/generalpage/guardian_080825/he/guardianlaw0725.pdf) | LAW | 2026-09-17 | Majority and minors’ legal acts |
| S29 | [Privacy Protection Authority — privacy of minors in educational applications](https://www.gov.il/BlobFolder/dynamiccollectorresultitem/ppa-report18/he/Minors_report.pdf) | OFFICIAL GUIDANCE | 2026-09-17 | Age-appropriate information and education-context risks |
| S30 | [What is GitHub Pages?](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages) | PLATFORM DOCUMENTATION | 2026-09-17 | Visitor IP logging and static-hosting context |
| S31 | [Render Data Processing Addendum](https://render.com/dpa) | PLATFORM TERMS | 2026-09-17 | Processor/controller scope and customer obligations |
| S32 | [Product Specific Schedule (Neon), updated 5 August 2026](https://neon.com/platform-terms) | PLATFORM TERMS | 2026-09-17 | Databricks agreement hierarchy and Neon-specific modifications |
| S33 | [Databricks Master Cloud Services Agreement](https://www.databricks.com/legal/mcsa) | PLATFORM TERMS | 2026-09-17 | Current referenced Neon agreement and DPA incorporation |
| S34 | [Databricks Data Processing Addendum, v3](https://www.databricks.com/legal/dpa) | PLATFORM TERMS | 2026-09-17 | Customer-content processing roles and assistance; actual account terms unverified |
| S35 | [GitHub General Privacy Statement, effective 27 April 2026](https://docs.github.com/en/site-policy/privacy-policies/github-general-privacy-statement) | PLATFORM PRIVACY TERMS | 2026-09-17 | Independent platform account/usage processing |
| S36 | [PPA opinion: interpretation of transfer regulation 2(4), 13 April 2026](https://www.gov.il/BlobFolder/legalinfo/infoabroad/he/infoabroad.pdf) | OFFICIAL GUIDANCE | 2026-09-17 | Contractual international-transfer route |
| S37 | [PPA opinion: interpretation of international-transfer regulation 3](https://www.gov.il/BlobFolder/legalinfo/takana3/he/regulation3.pdf) | OFFICIAL GUIDANCE | 2026-09-17 | Written recipient/privacy and onward-transfer safeguards |
| S38 | [PPA guide to regulation 15 — external service providers](https://www.gov.il/BlobFolder/reports/guide_section_15/ar/guide-section%2015.pdf) | OFFICIAL GUIDANCE | 2026-09-17 | Applicable outsourcing risk/contracts/oversight requirements |
| S39 | [Wikidata: Licensing](https://www.wikidata.org/wiki/Wikidata:Licensing) | LICENSE TERMS | 2026-09-17 | Structured data CC0; other content has different terms |
| S40 | [CC0 1.0 Universal — Legal Code](https://creativecommons.org/publicdomain/zero/1.0/legalcode.en) | LICENSE TERMS | 2026-09-17 | Waiver/fallback license and limitations |
| S41 | [GeoNames geographical database — dump format and license README](https://download.geonames.org/export/dump/readme.txt) | LICENSE TERMS | 2026-09-17 | Original provider CC BY 4.0 notice and distribution format |
| S42 | [Creative Commons Attribution 4.0 International — Legal Code](https://creativecommons.org/licenses/by/4.0/legalcode.en) | LICENSE TERMS | 2026-09-17 | Attribution, modifications, redistribution and database-right coverage |
| S43 | [MusicBrainz — About / Data License](https://musicbrainz.org/doc/About/Data_License) | LICENSE TERMS | 2026-09-17 | Core versus supplementary licensing; not imported |
| S44 | [Population and Immigration Authority — cities and settlements dataset](https://data.gov.il/he/datasets/population_authority/citiesandsettelments) | ORIGINAL SOURCE / LICENSE UNRESOLVED | 2026-09-17 | Investigated source only; no import; current direct retrieval failed |
| S45 | [Apple Music — Mizrahi curator page](https://music.apple.com/us/curator/apple-mizrahi/1106112453) | ORIGINAL FACTUAL SOURCE | 2026-09-17 | One curation reference, not an open-data grant |
| S46 | [Copyright Act, 2007 — WIPO Lex legislative text](https://www.wipo.int/wipolex/en/text/202010) | LAW / LEGISLATIVE TRANSLATION | 2026-09-17 | Facts versus compilation expression and ownership rules; not complete later-amendment review |
| S47 | [Psycopg — LICENSE.txt](https://github.com/psycopg/psycopg/blob/master/LICENSE.txt) | LICENSE TERMS | 2026-09-17 | LGPL library obligations; installed 3.3.5 license also inspected |
| S48 | [Mozilla — MPL 2.0 FAQ](https://www.mozilla.org/en-US/MPL/2.0/FAQ/) | LICENSE-OWNER GUIDANCE | 2026-09-17 | File-level scope and distribution distinction |
| S49 | [greenlet 3.5.6 — project release metadata](https://pypi.org/project/greenlet/3.5.6/) | ORIGINAL PACKAGE METADATA | 2026-09-17 | Platform-conditional dependency license; not installed locally |
| S50 | [The MIT License](https://opensource.org/license/mit) | LICENSE TERMS | 2026-09-17 | Permission/notice conditions and license-choice analysis |
| S51 | [GitHub Docs — Licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository) | PLATFORM DOCUMENTATION | 2026-09-17 | Default copyright versus open-source licensing |
| S52 | [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0.html) | LICENSE TERMS | 2026-09-17 | Patent grant, notices, changes and trademark limitation |
| S53 | [Render Acceptable Use Policy, modified 22 August 2025](https://render.com/acceptable-use) | PLATFORM TERMS | 2026-09-17 | Unlawful content, privacy and intellectual-property restrictions |
| S54 | [GitHub Terms for Additional Products and Features](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features) | PLATFORM TERMS | 2026-09-17 | GitHub Pages permitted-use limitations |


| S55 | [GitHub Docs — Setting your commit email address](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address) | PLATFORM DOCUMENTATION | 2026-09-17 | Noreply option; configuration changes affect future commits, not existing metadata |
| S56 | [OpenAI — Terms of Use (outside EEA/UK/Switzerland), effective 1 January 2026](https://openai.com/policies/row-terms-of-use/) | PLATFORM TERMS | 2026-09-17 | Output rights as between provider and account user; input rights and third-party limitations |
| S57 | [OpenAI Services Agreement, effective 1 January 2026](https://openai.com/policies/services-agreement/) | PLATFORM TERMS | 2026-09-17 | API/business customer output and input-rights provisions; account applicability must be confirmed |
| S58 | [OpenAI — Provenance signals in generated content](https://help.openai.com/en/articles/8912793-c2pa-in-chatgpt-images) | PROVIDER DOCUMENTATION | 2026-09-17 | Content Credentials do not establish legal ownership or identify the creator |

The code inventory and measured test results are direct audit evidence, not claims supplied by these legal pages. Decisions about exemptions, ownership and account contracts remain conditional on the missing owner facts.

## 28. Final public-repository publication check — 17 September 2026

**Result: BLOCKED only on unconfirmed publication authority and intentional Git-identity disclosure.** This follow-up resolves the licensing decision and repeats attribution/hygiene checks. Service-only privacy, accessibility and deployment work is outside its scope. No application behavior was changed. No push, deployment, history rewrite, merge or visibility change occurred. No response to the three owner-confirmation questions had been received when this result was recorded.

### 28.1 Every reachable contributor and non-owner production contribution

Basis: fresh read-only `git fetch origin`; full (not shallow) `git log --all` with raw author/committer fields and coauthor/signoff/review trailers; 138 unique commits across 50 local/remote refs. All 138 are ancestors of the audited `origin/main` SHA `eca8bdca8ec2444e0ed38a7a05d04093290a82cc`. There are no tag refs. GitHub contributor/account API data was cross-checked; the repository is still private and its general license is null. Identity grouping below is an inference from matching emails, names and linked GitHub commits, not government-ID verification. Git attribution is evidence of contribution, not conclusive copyright ownership.

| Apparent contributor | Exact human author spellings | GitHub account | Authored / committed | Publication confirmation |
|---|---|---|---|---|
| Repository owner | `yair shilo ben david`; `Yair ben david` | `yairrrr` | 104 / 63 | Owner must have authority for own work and supplied assets, including any institutional/employment rights |
| Gavriel Alafi | `gavrielalafi`; `gavrielalafi-boop` | `gavrielalafi-boop` | 13 / 8 | Permission to publish code, tests/docs and reachable history, including GitHub platform uses |
| Elick Chitrit | `Elick Chitrit`; `elick-chitrit` | `elick-chitrit` for six merge commits; seven local-identity commits additionally found in Git | 13 / 7 | Same; confirm both identity variants refer to this contributor |
| Uriel Israel Mizrahi | `אוריאל ישראל מזרחי`; `urielmizrahi91-svg` | `urielmizrahi91-svg` | 8 / 7 | Same |

Non-human metadata: `GitHub` is committer on 53 commits. `Claude Opus 5`, `Claude Sonnet 5` and `Claude Fable 5` appear only as AI-tool coauthor labels on 7, 7 and 6 commits respectively, using one generic vendor noreply address. These labels are not additional identified human rights holders, and do not by themselves prove the tools used or clear third-party rights. No other author, committer or coauthor/signoff/review identity was found.

Current production source paths touched by non-owner commits are listed below. The line counts are current `git blame --line-porcelain HEAD` attribution to that contributor, not a percentage-of-ownership calculation. Rewritten/deleted portions remain in history and are covered by the same publication-authority review. All 12 non-owner merge commits have empty combined diffs; no separate conflict-resolution contribution was detected.

**Gavriel Alafi — production source**

| Current path | Retained attributed lines |
|---|---|
| `backend/app/api/rooms.py` | 11 |
| `backend/app/api/schemas.py` | 9 |
| `backend/app/application/join_player.py` | 10 |
| `frontend/src/api/roomApi.ts` | 53 |
| `frontend/src/components/App.tsx` | 15 |
| `frontend/src/features/host/HostRoomEntry.tsx` | 24 |
| `frontend/src/features/player/PlayerRoomEntry.tsx` | 84 |
| `frontend/src/main.tsx` | 17 |
| `frontend/src/realtime/playerWebSocketUrl.ts` | 13 |
| `frontend/src/styles.css` | 258 |
| `frontend/src/types/contracts.ts` | 110 |
| `frontend/src/types/index.ts` | 2 |
| `frontend/src/types/realtime.ts` | 33 |
| `frontend/src/vite-env.d.ts` | 1 |

Also contributed these retained build/configuration files: `frontend/index.html`, `frontend/package-lock.json`, `frontend/package.json`, `frontend/tsconfig.app.json`, `frontend/tsconfig.json`, `frontend/tsconfig.node.json`, `frontend/vite.config.ts`.

Non-merge contribution commits: `cbd40d681ea6e10b652bfd700ccfe59fb4850619`, `d1fc5a7436997cce929fbdd0e31ef25c9b5f42d7`, `ca10e73f2344f5ac32cfd04ceebcaeaba11a933e`, `c12f45414519f746c489b0647863425a23823658`, `1802ca33462500f60f5b6beef27dab4d70d01068`, `0d72804670162e37f254a7bc08975dd483b1e3cb`, `0be5c6f7412f9ef974591f032663649d939aad07`, `747c5b33f202acb0452da70b9c421ba2649c9903`.

Tests, fixtures, empty scaffolding and MASTER_SPEC.md changes are also part of the corresponding contributor’s history; permission should cover the complete contribution, not just the production paths above.

**Elick Chitrit — production source**

| Current path | Retained attributed lines |
|---|---|
| `backend/app/application/repositories.py` | 90 |
| `backend/app/domain/statistics/__init__.py` | 13 |
| `backend/app/domain/statistics/question_statistics.py` | 96 |
| `backend/app/infrastructure/database/__init__.py` | 23 |
| `backend/app/infrastructure/database/base.py` | 68 |
| `backend/app/infrastructure/database/engine.py` | 51 |
| `backend/app/infrastructure/database/models.py` | 109 |
| `backend/app/infrastructure/repositories/__init__.py` | 5 |
| `backend/app/infrastructure/repositories/game_repository.py` | 170 |
| `backend/app/infrastructure/settings.py` | 78 |

Also contributed these retained build/configuration files: `backend/.env.example`.

Non-merge contribution commits: `12a728a17afb90b1b04eb5b3779db306cc5ce190`, `3da6be3f4d08a3cb4ca435bf61ffcca7b3f118a6`, `289ce5e16929c2dd2431fba8dbffeac212dd073d`, `2ca4741fcddaf2f8346aa23408c88f0672a2616b`, `64a1d4fea7e86c95af2caa172da983afff64237e`, `d4f7d0d487fa5fe5c12f6257c561afb85f5853a6`, `e10f6b2e62a07419a6ed4aa709090005ee919a7d`.

Tests, fixtures, empty scaffolding and MASTER_SPEC.md changes are also part of the corresponding contributor’s history; permission should cover the complete contribution, not just the production paths above.

**Uriel Israel Mizrahi — production source**

| Current path | Retained attributed lines |
|---|---|
| `backend/app/domain/questions/__init__.py` | 19 |
| `backend/app/domain/questions/candidate.py` | 22 |
| `backend/app/domain/questions/dataset.py` | 66 |
| `backend/app/domain/questions/question.py` | 48 |
| `backend/app/domain/questions/rule.py` | 24 |
| `backend/app/domain/questions/scorer.py` | 25 |
| `backend/app/domain/questions/selector.py` | 7 |
| `backend/app/domain/questions/validator.py` | 35 |

Non-merge contribution commits: `d27836fd5f167e7c982f4f8dd1a9f158b87fcafa`, `484d2ea36228a83242c7d556348af76c155f89a5`, `a8d3f5a7905657070878773b80cbc80a1d301101`, `58310bc7ce64c484341cd01bc14e5cf705b2e89b`, `77c9e1b4b65d1e159c33f370d743b2ccd81f355d`, `dc661aafc59191aad79f68476b8bddedea872c52`, `2f36432adbac2d2aa9a4abdaf825f5293a199156`.

Tests, fixtures, empty scaffolding and MASTER_SPEC.md changes are also part of the corresponding contributor’s history; permission should cover the complete contribution, not just the production paths above.

No non-owner commit introduced the logo PNG. No vendored third-party code tree, font binary, poster, photograph, biography, plot summary, lyric collection or other visual asset with a newly identified missing license was found. This does not establish that every contributor authored every line independently: confirm any externally sourced material as part of their publication permission. Existing package licenses were reviewed in §16; package declarations/lockfiles do not relicense dependencies.

**Exactly what requires confirmation:** authority from these three contributors (and any actual employer/institution rights holder) to publish their complete contributions/history on public GitHub under the current source-visible model; authority for the owner’s supplied work; no undisclosed incompatible third-party material. An ownership transfer, broad open-source license or blanket legal waiver is not required merely to resolve this evidence gap. If an existing project agreement already covers this scope, confirming that agreement is sufficient evidence for this audit.

### 28.2 Logo provenance and remaining input/account rights

| Evidence | Result |
|---|---|
| Identical paths | `logo/image.png`, `frontend/src/assets/mizemi-logo.png`, `docs/assets/mizemi-logo.png` |
| Git blob | `bcd06e5fb5a959dda40a2c322fb27a6c594bd2d4` |
| File SHA-256 | `ef1e8f1a5a4eb3528eb702798b58ea9ee65096c36a09b0e045eb63c08fe45341` |
| Format | 1,426,677-byte, 1254 × 1254 PNG; one 23,617-byte `caBX` Content Credentials chunk |
| Introduction | Original/frontend copy: `8ab453d8831855b7113a27d92867354b5cbe850b`; Pages copy: `8fbd0dd0fb242b05820199d67d157d832fd7896e`; both owner-attributed |
| Repository explanation | ENHANCEMENT_REPORT.md describes it as user-supplied and copied unchanged; GITHUB_PAGES.md records reuse |
| Embedded claims | Claim generator “OpenAI Media Service API”; software `gpt-image`, version `2.0`; creation claim dated 2026-09-11; `trainedAlgorithmicMedia` source type |
| Verification limit | Parsed metadata, no external upload; no cryptographic signature/trust-chain validation. Neither the prompt nor account holder nor rights in input images can be established from this claim. |

**Required owner confirmation:** identify whether this was generated through your authorized ChatGPT/API account (or who supplied it and authorized redistribution); confirm whether any reference image, stock icon, externally supplied design or manually added font/artwork was used and that its terms allow this publication. If it was generated solely from your original text prompt with no external artwork, say so; do not invent a stock/font license for generated lettering. Keep the creation/permission evidence privately rather than publishing account details.

OpenAI’s current consumer terms and business/API agreement assign its output rights, if any, to the relevant user/customer, subject to applicable law and input/third-party rights. This supports a path to permitted publication; it is not proof that this repository owner is that customer or that the output has exclusive copyright. The provider itself states that provenance verification does not establish legal ownership or identify the creator. [OpenAI consumer terms, Content](https://openai.com/policies/row-terms-of-use/), [Services Agreement §4](https://openai.com/policies/services-agreement/), [provenance limitations](https://help.openai.com/en/articles/8912793-c2pa-in-chatgpt-images) (retrieved 2026-09-17).

### 28.3 Git author/committer privacy: classifications and exact affected commits

No human email was classified as intentionally public merely because it appears in private Git history. The following labels avoid publishing full private addresses. Five potentially private human strings account for all human authors/committers. GitHub and AI-service generic noreply strings are separate and do not expose an individual mailbox.

| ID | Identity / masked email | Classification | Author commits | Committer commits |
|---|---|---|---|---|
| M1 | Owner’s two name variants; `y***@gmail.com` | **potentially private** | 104 | 63 |
| M2 | Gavriel’s two name variants; `g***@gmail.com` | **potentially private** | 13 | 8 |
| M3 | `elick-chitrit`; `e***@gmail.com` | **potentially private** | 6 | 0 |
| M4 | `Elick Chitrit`; `e***@[local-machine]` | **potentially private**; exposes machine-derived identity even if undeliverable | 7 | 7 |
| M5 | Uriel’s two name variants; `u***@gmail.com` | **potentially private** | 8 | 7 |
| N1 | `GitHub`; generic `noreply@github.com` | **GitHub noreply**; platform committer | 0 | 53 |
| N2 | Three Claude coauthor labels; generic vendor noreply | **intentionally public**, non-personal tool attribution (classification of its role, not proof of output rights) | 0; 20 coauthor trailers | 0 |

**Exactly which commits need attention:** every one of the 138 SHAs below carries one of M1–M5 as its author. The listed committers are either the same human address or generic GitHub N1. Thus there are no additional committer-only private identities to resolve. These are metadata-review items, not findings that 138 commits must be changed or that ordinary attribution is unlawful. If all four people intentionally approve this disclosure, no history change is indicated by the evidence.

**M1 — owner (104 commits)**

| Exact commit SHA | Committer class |
|---|---|
| `eca8bdca8ec2444e0ed38a7a05d04093290a82cc` | N1 — GitHub noreply |
| `e1ee26c5ed66f2c83884432d6e4c0da34d5cf8f1` | M1 |
| `b4fffe9ae9ffb06ad8ffb9c0dee6b0b7e25e3970` | M1 |
| `dc2b1441a819ad204bab951a9d7046deea304ed2` | N1 — GitHub noreply |
| `8fbd0dd0fb242b05820199d67d157d832fd7896e` | M1 |
| `19b115b2a18f9eb51a8a1f2bc25941abc905ab70` | N1 — GitHub noreply |
| `5b29fe84bd412d4ddad382c12ae313a4f05ef7f4` | M1 |
| `31aefaa58bb44557a67d1eaa72347e4a158e8aba` | M1 |
| `fadeda094bc3cde1391ed418ff108fd718177d6b` | M1 |
| `a89379309e0384a3e0d576ee625e3ef1d7db032b` | N1 — GitHub noreply |
| `8b6079747e41e92854fe8b6bee046b52fd5a8e70` | M1 |
| `d2c5b9f4b0ed2ce97702310a833b978b3afb364b` | N1 — GitHub noreply |
| `0eeec2f1595018da431e4a5b2b826bda6db82be6` | M1 |
| `2ed96df68a667b7a808ad3bd9d203486c03b31f3` | M1 |
| `2ea764f113a43099af4b0901738120be356449e0` | M1 |
| `95b92cbcf398cab340882627c1c7da0a01f99bbf` | N1 — GitHub noreply |
| `4de891dd6b1201c715a68ce35b83183b7766a6f4` | M1 |
| `e8c965bc22e9286764c6720343ef54e01b977712` | M1 |
| `b22e40e98d4043a9b189d4a780c58010f1db65aa` | M1 |
| `935ed29055cf02aa5078365d9394ceb06fad662f` | M1 |
| `1eee2de6ef81f983410bb60e8bcdc650ef66a8ce` | N1 — GitHub noreply |
| `3995e7a461cd4347cc3f7200d67edbbf7078a89d` | M1 |
| `b0bbdb54e810a3d66f213aa19d411c5ccb2e5f8d` | M1 |
| `27be0f2d730aa4051f28caa11cf9512fc4eb13d1` | M1 |
| `a3d4570a384e8700c8f6245987f6bd2426105853` | N1 — GitHub noreply |
| `679c2d5e722c63168d7b9d052a674152a80b016a` | M1 |
| `1c303fb96c03de9d02d7bf6dca7511f3ce771d78` | M1 |
| `5a21324b716b69ce689da11a43bb3c1ec9a16e92` | M1 |
| `533e88c5b10736ee56ddce48ed06fd4fb81ddc4f` | M1 |
| `56a14052aaae137a96cfa790be4f968fd46c72ce` | M1 |
| `e918cb306fb4f586d40277ea481f598011e7bd54` | N1 — GitHub noreply |
| `029aa8e4f732d65c4048b7c3eb2e3a06f3b4f930` | M1 |
| `d6f2b9d9cc04997138da9f774c3d01d626ca0a65` | M1 |
| `8ab453d8831855b7113a27d92867354b5cbe850b` | M1 |
| `4e1e4a914ebbc114f3147e58f1481ec8f4694aed` | M1 |
| `4235ca9e22f04b4425e6c3e0c3cca06b46a5b871` | M1 |
| `4882b480a6e0d6943caaf286ca7f2a33fee73db8` | N1 — GitHub noreply |
| `5bbb7f79bfe3435c68fbcc08f572a25599c1f957` | M1 |
| `afdaafd16a8bd95cbc76de3be7cacd31ba6e99f0` | M1 |
| `289083abe945186b4cca40efbcec9a3b3d51cbd5` | M1 |
| `bb4bf3117a327d1d10d1dfd9c7134ae5e000607f` | M1 |
| `d1fbae2962ff1bb6ac14dc285c30378113d65979` | M1 |
| `558d066274ab133c37db0ae2ac83a213e84d1628` | M1 |
| `6f70f6ced22508ecd42559fb754ca43a827b5e84` | M1 |
| `24b22bd6851da62c95e10915f1cadf4b43a3b9d5` | M1 |
| `abcbc094ab45c3abe13b97e5356b58cf3740f9ec` | M1 |
| `40294f9d24d6ae5170b506c3ecec15efec086f06` | N1 — GitHub noreply |
| `7fed432c7da030a0ea6bb73e728aaf1602160b95` | N1 — GitHub noreply |
| `ae162c86173d29fe255e870d26348937f54afbb0` | M1 |
| `416b98fa9a53bb020e5c9806caa6eaf997278de6` | M1 |
| `53d9caaff8d859b7454baec58d5a02c5e5c9d2e6` | M1 |
| `cb8be93ab9650c660738e6f6d246fb12d5642336` | M1 |
| `b38c80662e8fff8bcbb2dfe8f37657afbaed221a` | M1 |
| `ca7663aa2a7e401e7261a72116d38740308965c3` | M1 |
| `2467fbecc87c597c12fc7b289b44361cf3251691` | N1 — GitHub noreply |
| `a56cdc4c056a8f326834bb9d3cdf7605506f3214` | M1 |
| `6b892ad9cc1090938f681baf7deea5c31b51e1fa` | N1 — GitHub noreply |
| `cbe75e9e6a454cb985f979687d4695b8f37b5fd0` | M1 |
| `cc1c8a330918745d47d7902f2140476038c4d55d` | N1 — GitHub noreply |
| `a39c22bd0ce75f76e47a5e567c2628341a6a6b77` | M1 |
| `44d8f1458a4407645fe6f19740ef66a7241f1b77` | N1 — GitHub noreply |
| `a27f457eb4081ce8d93d90db810c217184e4517f` | M1 |
| `205943d26a96c079eba369f323c5cb9ac368cd10` | N1 — GitHub noreply |
| `64c32d3c6ddd9b7e802d25787ebb9d0ca5fd028d` | M1 |
| `3031ae7df407f094b13d000b1cd5775fa42d39fd` | N1 — GitHub noreply |
| `ade977d906b3fcbebcdd1c95caacecbf42ff2a5c` | M1 |
| `815c0053f56b186c29be1839b976b7e7f8d15254` | N1 — GitHub noreply |
| `cb747425ecabea82e449e6545f5e5095a33fe245` | M1 |
| `4195e076a5fe47f86efa3f69a2fbd5fd546e51bf` | N1 — GitHub noreply |
| `a2251338c2762d2bc4d0a16771bba6ab9f8fbc0f` | M1 |
| `818fa3595c667d4ad44b4a69b92b6d3d5dc6a825` | N1 — GitHub noreply |
| `6269ae0f3b5fca140995f34e58ef9a63b2395822` | M1 |
| `743ee4b80536f68c4fa3c02341bd4e0def869ea2` | N1 — GitHub noreply |
| `61c9d0588d1fcd3fc9639ed04f91dd61a11591de` | M1 |
| `2dc8748048962c101f5d38a0854a06e675aa8b06` | N1 — GitHub noreply |
| `b485ada7ab91329d13c5aa2727ef692ac8d6f2b9` | M1 |
| `e2657d786967e9fd9b8136b02e85e27618300bfb` | N1 — GitHub noreply |
| `038b5b3b95d10b0c7407a5c8ca37235ac4f7d535` | N1 — GitHub noreply |
| `c4838f411ca4951555111a0aa54c9bd9313d4ee8` | M1 |
| `dda4870e62cc2c502224fe05896c47d95cc0213f` | N1 — GitHub noreply |
| `cb0056a2bff9cad45353cf3c3309b17b165b84a3` | N1 — GitHub noreply |
| `544676f473a12d5f81b2ccda13d4664dd6e8a40c` | N1 — GitHub noreply |
| `efec2218c5fdb758ef1236197e24470c0e90621a` | N1 — GitHub noreply |
| `b6e62ad065f47d9c17f9b477d3501dd9b362884f` | N1 — GitHub noreply |
| `782a331b5315511047780d0777ef2f83733e0dcc` | N1 — GitHub noreply |
| `bb0f7b6382ff22d4d63903e19b9863fcbb87922d` | N1 — GitHub noreply |
| `b1520c77199c22127282fd437b6d174ae6bc03a0` | N1 — GitHub noreply |
| `4c4398faf5e8114f1c8d4d3b34b743c55671bdfb` | N1 — GitHub noreply |
| `3f969071f1061f85baf910f3cb7ac77580cd9f0d` | M1 |
| `416eb0aad01ce7faf30b1ce777ba8c3978ed0118` | N1 — GitHub noreply |
| `5daa100b6d6e014acc083dbb87345e4f6e072507` | M1 |
| `6a4b2dd7dc98ca3330a4dedb9235c2f10a6c8669` | N1 — GitHub noreply |
| `0f90dc36482e3dc9664334fa6aea587728f069bf` | M1 |
| `7d7c4792f76d407a206ed580241e5be2127f095a` | N1 — GitHub noreply |
| `f69f059fcb3d01aa119f70fc5387fc95998c6eef` | M1 |
| `0c0aaba7dc8bdfbd918b03981f8a6a181e84af83` | N1 — GitHub noreply |
| `6666ad550ba4b036f608d57dbdb16929b9d87d7d` | M1 |
| `baad6bbebdc45612b543c587afa1e11d9e0c1e9d` | N1 — GitHub noreply |
| `5d2c4c03c366b4674d0d4a3a842c222d569d7e31` | M1 |
| `aaea9ce11890ae2b04dbd22e4a48203e6aefb0bb` | N1 — GitHub noreply |
| `83f11f72c5ed5de956ecb7046d6f74fac3e0dd3a` | M1 |
| `dd999fc5380f65f642c8606faf0a42f104fa81a5` | N1 — GitHub noreply |
| `a4c7b8ec57ff92eff8484356a4ad20a24ec88aad` | M1 |
| `a256fd10bb4407c7959a0422590e740b9d91ba34` | M1 |

**M2 — Gavriel (13 commits)**

| Exact commit SHA | Committer class |
|---|---|
| `f8983931f5030089ed6531901576eb06cd4742de` | N1 — GitHub noreply |
| `cbd40d681ea6e10b652bfd700ccfe59fb4850619` | M2 |
| `d1fc5a7436997cce929fbdd0e31ef25c9b5f42d7` | M2 |
| `aea79f7b766204f75f282c7d2d6ef22645a38d12` | N1 — GitHub noreply |
| `ca10e73f2344f5ac32cfd04ceebcaeaba11a933e` | M2 |
| `ae8bbc28af998c9383b971a0c3d1f77a6a211890` | N1 — GitHub noreply |
| `c12f45414519f746c489b0647863425a23823658` | M2 |
| `b9aebd4efe36e3c469bb7c4e7968412a8ec1c755` | N1 — GitHub noreply |
| `1802ca33462500f60f5b6beef27dab4d70d01068` | M2 |
| `e8602a5bca58fa0cebd9d121e7bf8cf72e8f79cf` | N1 — GitHub noreply |
| `0d72804670162e37f254a7bc08975dd483b1e3cb` | M2 |
| `0be5c6f7412f9ef974591f032663649d939aad07` | M2 |
| `747c5b33f202acb0452da70b9c421ba2649c9903` | M2 |

**M3 — Elick GitHub identity (6 commits)**

| Exact commit SHA | Committer class |
|---|---|
| `82ea8e58fac2c5cbec898b8d8adf67327d5f9d0f` | N1 — GitHub noreply |
| `aa2fa37a0b9ca26cb6351cffb3b14e960aeb6c3a` | N1 — GitHub noreply |
| `e32edf44920161497f583f183d7dd4b38c260851` | N1 — GitHub noreply |
| `3a22ab09c226e1aec0039c1b22341aa04c663019` | N1 — GitHub noreply |
| `158a09e1b358cc28dc583c2e141aae25c562fd5d` | N1 — GitHub noreply |
| `7f5ea4803c8bcd06e76b3f857f7e6d247508acf7` | N1 — GitHub noreply |

**M4 — Elick local-machine identity (7 commits)**

| Exact commit SHA | Committer class |
|---|---|
| `12a728a17afb90b1b04eb5b3779db306cc5ce190` | M4 |
| `3da6be3f4d08a3cb4ca435bf61ffcca7b3f118a6` | M4 |
| `289ce5e16929c2dd2431fba8dbffeac212dd073d` | M4 |
| `2ca4741fcddaf2f8346aa23408c88f0672a2616b` | M4 |
| `64a1d4fea7e86c95af2caa172da983afff64237e` | M4 |
| `d4f7d0d487fa5fe5c12f6257c561afb85f5853a6` | M4 |
| `e10f6b2e62a07419a6ed4aa709090005ee919a7d` | M4 |

**M5 — Uriel (8 commits)**

| Exact commit SHA | Committer class |
|---|---|
| `f1b93b17e1123728ca369e392efc89de4559a895` | N1 — GitHub noreply |
| `d27836fd5f167e7c982f4f8dd1a9f158b87fcafa` | M5 |
| `484d2ea36228a83242c7d556348af76c155f89a5` | M5 |
| `a8d3f5a7905657070878773b80cbc80a1d301101` | M5 |
| `58310bc7ce64c484341cd01bc14e5cf705b2e89b` | M5 |
| `77c9e1b4b65d1e159c33f370d743b2ccd81f355d` | M5 |
| `dc661aafc59191aad79f68476b8bddedea872c52` | M5 |
| `2f36432adbac2d2aa9a4abdaf825f5293a199156` | M5 |

**Owner action:** confirm intentional public attribution with the three contributors and choose whether your own current metadata should be public. If any address/name should remain private, keep visibility private and request a separate agreed remediation plan; this task does not authorize rewriting history. A future-only GitHub noreply setting or `.mailmap` does not remove existing raw commit metadata. [GitHub commit email documentation](https://docs.github.com/en/account-and-profile/how-tos/email-preferences/setting-your-commit-email-address) (retrieved 2026-09-17).

### 28.4 Dataset notices and source-visible decision — resolved

| Committed location | Actual verified notice |
|---|---|
| `backend/app/data/knowledge/LICENSES.md` | Wikidata structured/factual data and identified local reference adaptations: CC0, linked; application software explicitly outside that dedication. GeoNames identified/linked; CC BY 4.0 linked; filtering/name normalization/district mapping/coordinate changes disclosed; no endorsement. |
| `backend/app/data/knowledge/manifest.json` | Source URLs, retrieval dates, exact CC0/CC BY identifiers/links, transformations, GeoNames attribution and artifact hashes. All eight artifact hashes reverified against committed HEAD. |
| `scripts/knowledge/README.md` | Source/license URLs and attribution; changes, restricted projection, no imported prose/media, excluded sources documented. |
| `frontend/src/components/KnowledgeCredits.tsx` / `frontend/src/i18n/messages.ts` | English/Hebrew source credit, GeoNames adaptation notice, source and CC license links. App.tsx actually renders the component. |
| `README.md` — new documentation | Explicit source-visible software scope; links data license/manifest and repeats attribution; preserves existing dependency/data rights. |

No required source attribution was missing, so the existing notices were preserved. Wikidata’s CC0 structured-data terms and the original GeoNames dump README were freshly checked. Neither a general code license nor deletion of the data is needed to fix attribution. [Wikidata licensing](https://www.wikidata.org/wiki/Wikidata:Licensing), [GeoNames original license/readme](https://download.geonames.org/export/dump/readme.txt) (retrieved 2026-09-17).

**Licensing choice settled:** no general software LICENSE is appropriate for the stated portfolio goal. README explains that default copyright remains with the respective rights holders and that platform viewing/forking permissions and legal exceptions still apply; it does not promise that public copying or GitHub’s applicable platform uses can be prevented. This is source-visible, not an open-source license. The separately licensed reference data retain their reuse permissions. No permission on behalf of the three contributors is assumed. [GitHub licensing guidance](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository), [GitHub Terms §§D/J](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service) (retrieved 2026-09-17).

### 28.5 Repeated publication hygiene — no additional blocker found

| Check / actual method | Result |
|---|---|
| Current-main tree: `python3 scripts/check_secrets.py` | 253 files; 0 high-confidence findings; 0 real-env files before final documentation edits. |
| Original working tree including ignored build/test artifacts: same current-main scanner imported with ROOT pointed at original checkout | 304 files; 0 high-confidence findings; 0 real-env files before final documentation edits. Protected lockfile and untracked report included. |
| All reachable history: `python3 scripts/check_secrets.py --history` | 564 unique blobs; 0 findings. Full clone; includes deleted content and all 138 commits. |
| Commit-message scan | All 138 bodies checked with scanner patterns; 0 credential findings. Human metadata separately inventoried above. |
| Independent full-history patterns and file types | Broader credential-assignment/URL/JWT/Slack/private-key patterns over all 564 blobs. Seven candidate blob versions, all fixture PostgreSQL URLs in validation/security tests, with placeholder passwords. No real credential identified. |
| Every historical path | 253 unique paths; only `.env.example` files and the three identical logo PNG paths matched sensitive/binary-artifact categories. No committed/history DB, dump, backup, private log, screenshot export, archive, font or personal document discovered. |
| Original ignored database contents, read-only | backend/mizemi.db: all seven tables empty. frontend/.e2e.db: six games/22 players/94 questions/360 answers/174 profile fields; all 8 distinct names and 56 distinct profile values match current committed synthetic E2E sources. These DBs remain ignored, not publication content. |
| Ignored local screenshots/logs/cache | Synthetic E2E screenshots, error-context.md, generated dist and local OS/test cache files present and excluded by .gitignore. No nonignored personal file besides the intended audit report; images were not individually recertified. Do not include ignored artifacts in a manual source archive. |
| Copyrighted entity prose/media | Prior schema/source review confirmed only facts/names/IDs/classifications; no new source changes since that audit. Unique historical PNG is the logo; no lyrics/plots/biographies/posters/photo collection found. Contributor and logo-input permission remain the specific unresolved provenance items, not an identified infringing dataset. |
| GitHub read-only issue/PR/release API | 52 issue/PR entries; 0 issue comments; 0 PR review comments; 0 releases; no detected credentials, email-like text or attachment references in the inspected bodies. |
| GitHub Actions read-only log API | All 32 existing runs available; 72 log files scanned in memory; no detected credentials. Email-like hits in two Pages runs are generic GitHub SSH URL rewrite targets, not contributor mailboxes. No log archive added to the repository. |
| GitHub artifact metadata | One expired github-pages artifact; no active/downloadable artifact to inspect. Source Pages assets already inspected. Cannot retroactively certify expired/deleted artifact contents. |
| Third-party assets/dependencies | No new incompatible source dependency or vendored visual/code asset found. The §16 missing notice in deployed frontend builds remains a service-distribution issue; dist/node_modules are not tracked or part of source publication. |
| Unrelated change preserved | frontend/package-lock.json SHA-256 remains `5ce92a07171ded0100886b0ef3ffaacc27f51eefa6f55cea9850c8fa9e82411f`; never edited/staged/restored. |
| Final documentation verification | After README/report edits: original-tree scanner still 304 files / 0 findings / 0 real-env files; `git diff --check` passed. Separate report whitespace, exact 138-SHA coverage, full-private-email suppression, README local links and protected-lock hash assertions all passed. No application regression suite was rerun for these documentation-only changes. |
| Final Git state | Original branch `codex/github-pages-landing`, HEAD `8fbd0dd`: README.md modified, LEGAL_READINESS_REPORT.md untracked, pre-existing frontend/package-lock.json modification preserved. Nothing staged or committed. Isolated `codex/legal-readiness` worktree remains clean at `eca8bdc`. |

Counts vary from the initial audit because temporary audit files were removed and a refreshed reachable-object inventory was used. Scans do not prove absence of all arbitrary secrets or undisclosed provenance; no positive evidence requiring a further owner hygiene task was found. No live player records or Render/Neon logs/database were accessed.

### 28.6 Only remaining owner decisions/actions

1. **Contributor publication authority:** confirm Gavriel Alafi, Elick Chitrit and Uriel Israel Mizrahi authorize publication of the complete contributions/history listed above, and resolve any employer/institution or externally sourced-code rights. Existing applicable permission is sufficient; no forced copyright transfer or open-source relicensing is requested.
2. **Logo:** confirm the authorized account/creator behind the embedded OpenAI generation claim and permission for any supplied reference artwork or added third-party elements. If solely your original text-to-image creation with authorized use, confirm that fact.
3. **Git identity privacy:** confirm that you and those three contributors intend to publish the listed names and five human email variants. If anyone objects, keep the repository private pending separately authorized remediation; do not assume changing future Git settings removes the 138 existing metadata records.

No further license selection, dataset attribution repair, cookie banner, service deployment or application change is needed to resolve these public-source gates. The README/report edits are local documentation changes, not yet committed or pushed. Source publication can be reassessed as READY once these confirmations are recorded and no contrary restriction is identified. Until then the exact blocker is missing evidence of publication authority/intent, not a detected credential or an incompatible imported-data license.

PUBLIC GITHUB LEGAL READINESS: BLOCKED

PUBLIC SERVICE LEGAL READINESS: NOT YET READY

MIZEMI PUBLICATION READINESS CHECK COMPLETE


## 29. Authorized implementation — 18 September 2026

Implementation branch `codex/legal-readiness-implementation` starts at the audited `eca8bdc` baseline. Commits `9414918125eb9a8a861b8473e8a86f8ff85aa469` and `aeff9b9a16969cb2b90139f2b9a8e09452f19603` implement and verify the changes below. The accompanying `LEGAL_IMPLEMENTATION_REPORT.md` contains exact behavior, tests, remaining gaps and release order. No push/deploy/visibility change, Render modification or direct Neon operation occurred.

| Earlier finding | Current implementation status |
|---|---|
| P1 collection notice/ambiguous consent | Bilingual visible pre-submit notice, precise question-use labels, public Privacy page and current backend retention facts implemented. **Operator identification/private contact still missing**; this part remains a real-user promotion gate |
| P2 excessive finished profile storage | **Addressed locally.** New snapshots omit all raw profiles; FINISHED clears live profile fields; bounded cleanup removes legacy finished profiles without touching active games or extending timestamps. Names, generated questions/explanations, answers and scores remain under the existing seven-day default. Outages/backups/connected room limits are disclosed |
| P3 provider/account/transfer details | Accurate Render/Neon/GitHub disclosure added. Actual account agreements, region/backup/log retention and transfer basis still need owner/legal review |
| P4 rights/request route | Honest contact limitation and arranged-demo private organizer route explained; no fabricated address or unauthenticated delete endpoint. A public verified private channel and request-handling responsibility remain unresolved |
| A1 technical barriers | Contrast, landmarks, focus, validation association, connection/rank text, timer announcements, RTL/LTR, mobile/reflow and Pages fixes implemented. Automated checks and both-language keyboard journeys pass |
| A2 applicability/timing/statement | Bilingual truthful statement added. Fixed 20-second timer, real AT evaluation, statutory applicability/exemptions and possible accommodations remain open; no certification or exception asserted |
| C1 runtime MIT notices | **Addressed locally.** Each build emits installed React/React DOM/scheduler notices and Terms links to them |
| T1 Terms | Bilingual proportionate Terms added; no absolute liability exclusion or invented governing-law/age clause |
| M1 minors | Classroom/group/portfolio positioning disclosed; no arbitrary age gate. Child-directed use not reviewed. Audience and required safeguards remain owner/professional decisions |
| K1 dataset attribution | Existing Wikidata CC0/GeoNames CC BY notices, transformations and game credits verified and preserved |
| B1 tracking | No tracker found or added; no cookie banner. Functional browser storage disclosed |
| L1/L2 publication rights and Git identity privacy | **Unchanged unresolved owner confirmations** from §28. This implementation does not establish publication authority |

### 29.1 Current data-inventory correction

The §3/§20 raw-profile persistence description is historical. New raw profile values and per-field flags remain in active server memory and are removed from live player profiles at finish; they are not written to new database snapshots. The old profile table remains readable only for compatibility/cleanup. New finished records still contain identifying names/IDs and consented facts embedded in quiz content, so they are not anonymous. Active reconnect continues from live memory. Default expiry remains seven days from the last save, with startup/five-minute bounded maintenance. No immediate universal backup-deletion promise is made.

`/api/v1/privacy-info` is a PUBLIC, no-store allowlisted endpoint for policy version, retention days, idle minutes, maintenance seconds and the no-raw-profile capability. The updated frontend blocks profile submission until it obtains compatible facts. This needs a coordinated backend-first release; it is not a live infrastructure change.

### 29.2 Verification and readiness

Final local results: **1279 backend tests** including PostgreSQL; **88 focused privacy/security/PostgreSQL/lifecycle/oracle tests**; **392 frontend tests**, types and production build; **8 Playwright scenarios** including rich Hebrew semantics, both-language keyboard journeys, legal navigation, axe checks and Pages; **21-WebSocket classroom smoke**; current/history secret scans clear; npm audit/pip-audit clear; pip check/diff check pass. Real screen-reader spoken output, physical devices, remote CI and the updated deployed application were **not** verified. Full evidence/commands and earlier failures resolved are in `LEGAL_IMPLEMENTATION_REPORT.md`.

No immediate new security exposure was found. Controlled synthetic-data demos can continue. Unattended real-person collection should wait for operator/contact disclosure and a reachable private request channel. Broad launch also needs provider arrangements, audience/minor-use decisions, applicable privacy/accessibility review and a timing/accommodation decision. These are not erased by publishing legal pages.

The original checkout and its protected unrelated lockfile modification remain unchanged. README keeps the source-visible preference; no general software license was added. The historical statement in §28 that README/report edits were uncommitted described that audit date; the implementation documentation is now committed on the dedicated branch.

PUBLIC GITHUB LEGAL READINESS: BLOCKED

The exact public-source gates remain contributor publication authority, logo account/input rights, and intentional Git-author identity/email disclosure, as listed in §28.6; no owner confirmations were supplied in this implementation turn.

PUBLIC SERVICE LEGAL READINESS: NOT YET READY

The immediate owner next action is to provide an authorized private contact method and suitable public operator identification, review the bilingual copy and decide the intended audience. Then review the provider/legal/accessibility gaps before a separately authorized release or promotion.
