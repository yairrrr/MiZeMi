# MiZeMi offline knowledge engine — completion report

Verified locally on **2026-09-11**. Dataset version **2026-09-11.1**. The application now uses **47 deterministic rules**, including **18 new semantic families**, over **2,434 offline reference entities**. No runtime AI, internet reference lookup, paid API, new dependency, deployment or push was introduced.

## 1. Recovery and preserved work

Continued the existing `feature/complete-mizemi-product` branch from `029aa8e4f732d65c4048b7c3eb2e3a06f3b4f930`. The current code was already the completed bilingual product described in ENHANCEMENT_REPORT.md, with 29 rules, 20 default questions, host/player authorization, realtime play, scoring, reconnect and persistence. That code governed this task; the older interrupted-frontend handoff was not used as a restart plan.

Read the current specification, enhancement report, engine, schema/normalization/consent boundaries, persistence, deployment files and tests before editing. Baseline: **837 backend tests passed, two optional PostgreSQL tests skipped; 277 frontend tests passed**. Initial local work was only the known lockfile metadata diff: twelve removed `peer: true` flags. It remains unchanged and unstaged. No dependency was changed.

## 2. Architecture

Development research → reviewed curation → validated local JSON → cached immutable domain facts → consent-safe semantic snapshot → existing candidate/validation/selection pipeline → server-authoritative question → ended-only explanation.

`app/infrastructure/knowledge.py` owns filesystem/schema/hash validation and cached loading. `app/domain/questions/knowledge.py` contains pure frozen facts, exact/alias resolution and mathematical distance. `semantic.py` enriches only ProfileDataset’s copied, consented fields and caches within that generation snapshot. `semantic_rules.py` reads those facts through the service. The application composition root injects the knowledge into QuestionGenerator; pure legacy callers can still use the original rules alone. Rules never read JSON, query SQL, fetch a URL or invoke an AI model.

## 3. Exact datasets and coverage

| Domain/file | Entities | Additional stored aliases | Normalized lookup keys | Raw file bytes |
|---|---:|---:|---:|---:|
| movies | 467 | 422 | 1,335 | 71,980 |
| music | 66 | 46 | 173 | 6,352 |
| artists | 282 | 38 | 581 | 30,029 |
| foods | 182 | 18 | 381 | 17,306 |
| hobbies | 212 | 51 | 475 | 18,714 |
| localities | 1,225 | 627 | 2,811 | 108,425 |

Canonical English/Hebrew names are counted separately from additional aliases. Some stored spellings normalize to the same key. Ambiguous keys are excluded. There are **1,202 additional alias strings** and **5,756 usable normalized lookup keys** across domains.

Hebrew labels exist for 466/467 films, 277/282 artists, all 66 music styles, all 182 foods, all 212 hobbies and 1,167/1,225 places. Missing Hebrew labels display the English canonical title. Coverage includes popular international and Israeli works/artists, common Israeli foods and activities, cities, towns, villages and kibbutzim. It is a curated practical sample, not a measured claim about all Israeli users’ answers.

## 4. Taxonomies

**93 bilingual labels:** 17 movie.genre, 24 music.genre, 18 food.cuisine, 14 food.format, 14 hobby.family, 6 place.district.

Films include horror, thriller, mystery, action, adventure, comedy, drama, romance, science fiction, fantasy, musical, family, crime, war, western, biography and superhero. Music includes Mizrahi, Mediterranean, pop, rock, hip-hop, electronic, house, techno, trance, indie, jazz, classical, metal, R&B, reggae, folk, country and others. Artist associations come from actual genre statements and approved parent mappings.

Foods have broad cuisine associations and formats such as rice, pasta/noodles, bread, sandwiches/wraps, dumplings, soups, stews, salads, desserts, baked goods/pastries, potatoes, legumes, eggs and dips. These overlap deliberately. No disputed exclusive origin, allergy, vegetarian or vegan guarantee is stored. Hobbies use reviewed activity families: physical sport, fitness, water, creative work, making music, digital activity, tabletop games, nature, learning, cooking, collecting, wellbeing, community and travel. Being creative/social is never inferred as a personality trait.

Places contain only names, aliases, coordinates and a district when supported. The 22 entries without a supported district can still be used for coordinate comparisons. No home coordinates, demographic attributes or pairwise distance matrix is stored.

## 5. Sources, research and licenses

The complete source/field/transformation manifest is [manifest.json](backend/app/data/knowledge/manifest.json); methodology and rejected sources are in [the build guide](scripts/knowledge/README.md).

- [Wikidata](https://www.wikidata.org/wiki/Wikidata:Licensing): CC0 structured IDs, revisions, short names/sitelinks and classifications. No article prose, biographies, plots, images or bulk aliases. Q IDs plus source revisions provide record-level traceability without repeating URLs in every row.
- [GeoNames](https://download.geonames.org/export/dump/readme.txt): CC BY 4.0 country extract and district-code labels. **Contains information from GeoNames, available under CC BY 4.0; MiZeMi filtered, normalized and adapted the data.** Source/attribution/license links ship in the application and [LICENSES.md](backend/app/data/knowledge/LICENSES.md).
- Official Israeli CBS listings were investigated, but reliable retrieval/redistribution terms for the locality spreadsheets were not established. No unclear-license bulk data was imported. GeoNames is a documented aggregation, not an official Israeli administrative register.
- MusicBrainz was investigated; core and supplementary/tag licenses differ, so no MusicBrainz genre tags were imported. No IMDb/TMDB or paid/keyed bulk source was used. BBFC independently corroborated The Conjuring’s horror classification without copying its prose.

All retrieval dates are 2026-09-11. Initial research investigated 502 film titles, 316 artist names, 239 foods, 237 activities and 101 genre/concept titles. Small batches and explicit curation were chosen over millions of records. After redirects/missing entries and classification validation, uncertain records were omitted. The last gains in coverage came mainly from Hebrew titles and common aliases, rather than storing more long-tail descriptions.

## 6. Provenance and build pipeline

`curation.json` records selections, approved roots, positive activity memberships, food additions and reviewed aliases. Each Wikidata-derived runtime record stores its revision. The manifest records source licenses, used fields, transformations, the curation hash and per-file SHA-256/byte counts. Local “Israeli pop” is explicitly documented as a lexical subtype of pop; no artist nationality/listener inference is attached to it.

The rebuild script defaults to offline validation. `--refresh` is an explicit development-only operation against fixed public endpoints; it writes a bounded resumable cache outside the repository. Use a new empty cache for updates, review changes, compile a draft, validate and bump the version. Production never refreshes or runs a scraper. The same reviewed cache, curation, builder, version and date compile reproducibly; a later upstream refresh may legitimately differ. See the build guide for exact commands.

## 7. Normalization and confidence

Names use trim, NFKC, casefold, repeated-space collapse, Hebrew point removal, quote-variant normalization and selected punctuation normalization. Canonical display/user text is retained. Results are **EXACT**, **ALIAS** or **UNKNOWN**. No edit-distance, probabilistic or aggressive fuzzy matching is used. Collisions fail closed, even between a canonical name and another record’s alias: 10 movie keys, 2 artist keys and 22 locality keys are currently rejected.

Examples: Saw/המסור; Tel-Aviv/תל אביב/ת״א; hip-hop/היפ הופ/היפהופ; pizza/פיצה. The discovery found vandalized aliases on Saw and a bad label on Jachnun. Those were not imported: sitelink titles and reviewed aliases are used. Historical GeoNames names such as Zion/Jebus and unrelated alternate settlements are not blindly accepted.

## 8. All 18 semantic rules

Each question has one proven correct displayed option. Repeated/multilabel memberships count each participant once. Distinct-choice rules deduplicate canonical entities, so two spellings of Saw are not two films. Global comparisons require full consented/resolved coverage for the dimensions involved. Scoped rules explicitly name participants or limit comparison to displayed pairs. Ties are rejected, rather than arbitrarily scored.

| Rule ID | Difficulty | Derivation and uniqueness gate |
|---|---|---|
| `semantic_count` | EASY | Resolve choices → classify → count participants. Whole dimension must be resolved and consented. |
| `semantic_subset_count` | MEDIUM | With incomplete knowledge, count only a named subset of 3–6 participants; unknown/private participants are outside the question. |
| `semantic_scoped_pair` | MEDIUM | Among explicitly displayed pairs, one pair chose different known entities sharing the named family. Other truthful pairs are excluded from distractors. |
| `semantic_mode` | MEDIUM | Unique repeated largest participant membership across a fully known dimension. |
| `semantic_rare` | MEDIUM | Unique smallest positive membership; only represented categories are options. |
| `semantic_diversity` | HARD | Classify → deduplicate canonical choices → count different works per family → strict maximum. |
| `semantic_different_pair` | MEDIUM | Exactly two holders of the named family chose different canonical entities; other real pairs are distractors. |
| `semantic_intersection` | HARD | Two independently ambiguous positive classifications have one intersection across domains. Incomplete rooms explicitly name their comparison subset. |
| `semantic_filtered_mode` | HARD | Classify a proper subgroup of at least three → classify their other choices → find a unique repeated mode. |
| `semantic_outlier` | MEDIUM | Four shown players: three foods have one cuisine association; the fourth has the other named association. No exclusive national origin claim. |
| `music_artist_bridge` | MEDIUM | Find the group’s unique dominant style → find an artist classified in that style. Exactly one displayed artist has that recorded membership; no listening inference. |
| `locality_extreme` | EASY | Resolve towns → compare latitudes → unique northernmost/southernmost reference point; margin at least 0.01°. |
| `locality_distance_pair` | HARD | Resolve towns → Haversine distances → unique nearest/farthest pair, with at least 1 km separation from the runner-up. |
| `locality_nearest_to` | MEDIUM | Anchor a participant’s town → calculate distances → unique closest other town, with the same distance margin. |
| `locality_middle` | HARD | Resolve an odd-sized group → sort latitude → select the middle. Reject tied/near latitudes. |
| `locality_distinct` | EASY | Resolve aliases → deduplicate places → count towns; only emitted when repeated towns exist. |
| `semantic_nearby_pair` | HARD | Shared family + different choices + different towns → distance ranking of eligible pairs → unique nearest pair. |
| `district_activity_diversity` | HARD | Resolve districts → resolve hobbies → union activity families per district → unique greatest diversity. |

The 29 existing families remain. The selector retains its difficulty progression and diversity controls; within those controls, actual semantic reasoning depth is preferred over direct lookup. Player scoring itself is unchanged. In 60 synthetic room/language runs over the demonstration group, each selected 20-question game contained 13 semantic questions and two different cross-domain families. The candidate catalog demonstrates four distinct cross-domain families.

## 9. Distractors and question quality

Options use real participants/pairs, nearby bounded counts and actual category/artist labels. Editorial neighbor lists make genre/cuisine distractors plausible (for horror, thriller/mystery/crime rather than arbitrary far-away labels). These neighbor lists never determine truth. Artist distractors prefer neighboring styles while excluding other artists with the winning stored membership. Scoped pair rules exclude every additional truthful pair from their displayed distractors.

Candidates have at most four distinct options, 600-character questions, 160-character options and 1,200-character explanations. Families emit at most 60 candidates; pair tables are bounded by classroom size and clue products are capped. Original rules retain their existing caps. No technical field/value/category-ID terminology appears in Hebrew question templates.

## 10. Hebrew demonstration

These are actual outputs from the deterministic synthetic fixtures, not staged frontend state. The main group is Dana/Omer/Noa/Amit/Lior with Haifa/Tel Aviv/Rehovot/Rishon LeZion/Beersheba, different films, foods and activities. The full input/output artifact includes the specialized unknown/alias fixtures.

**semantic_different_pair**

> איזה זוג בחרו סרטים בז׳אנר אימה, אבל כל אחד בחר משהו אחר?

תשובה: **דנה + עומר**

“המסור”, “לזמן את הרוע”: החיבור הוא אימה. מספר המשתתפים שבחרו בהם: 2.

**semantic_count**

> כמה משתתפים בחרו תחביבים בתחום ספורט?

תשובה: **3**

“ריצה”, “כדורגל”, “גלישת גלים”: החיבור הוא ספורט. מספר המשתתפים שבחרו בהם: 3.

**semantic_diversity**

> סופרים מאכלים שונים, בלי לספור שוב את אותה בחירה: מה מבין מטבחים הבאים מחבר בין הכי הרבה מהם?

תשובה: **המטבח האיטלקי**

“פיצה”, “ספגטי”, “לזניה”: החיבור הוא המטבח האיטלקי. מספר המשתתפים שבחרו בהם: 3. יחד יש כאן 3 בחירות שונות במשפחה הזאת.

**locality_distance_pair**

> איזה זוג בחרו את היישובים הקרובים ביותר זה מזה בקו אווירי?

תשובה: **נועה + עמית**

בין רחובות לראשון לציון יש כ־9 ק״מ בקו אווירי, לפי נקודות הייחוס של היישובים ולא לפי כתובות מגורים או כבישים.

**music_artist_bridge**

> איזה אמן מהרשימה משויך במשחק לסגנון המוזיקה שחוזר הכי הרבה בבחירות של הקבוצה?

תשובה: **עומר אדם**

מזרחית מחבר בין הבחירות של 2 משתתפים. עומר אדם מזוהה עם הסגנון הזה. זה החיבור המוזיקלי ביניהם.

**semantic_filtered_mode**

> מבין מי שבחרו תחביבים בתחום ספורט, איזה ז׳אנר קולנוע חוזר בבחירות של הכי הרבה משתתפים?

תשובה: **אימה**

“ריצה”, “כדורגל”, “גלישת גלים”: החיבור הוא ספורט. מספר המשתתפים שבחרו בהם: 3. “המסור”, “לזמן את הרוע”: החיבור הוא אימה. מספר המשתתפים שבחרו בהם: 2.

**semantic_intersection**

> מי מחבר/ת בין שני הרמזים: סרטים בז׳אנר מתח, וגם תחביבים בתחום ספורט?

תשובה: **עומר**

עומר מחבר/ת ביניהם: “לזמן את הרוע” → מתח; “כדורגל” → ספורט.

**semantic_nearby_pair**

> מבין הזוגות עם תחביבים שונים שמזוהים עם ספורט ועם יישובים שונים, של מי היישובים הכי קרובים בקו אווירי?

תשובה: **עומר + נועה**

“כדורגל”, “גלישת גלים”: החיבור הוא ספורט. מספר המשתתפים שבחרו בהם: 2. בין תל אביב יפו לרחובות יש כ־21 ק״מ בקו אווירי, לפי נקודות הייחוס של היישובים ולא לפי כתובות מגורים או כבישים.

**district_activity_diversity**

> איזה מחוז מביא לקבוצה את המגוון הגדול ביותר של משפחות תחביבים, לפי הבחירות של המשתתפים שגרים בו?

תשובה: **מחוז המרכז**

המשתתפים ממחוז המרכז בחרו תחביבים שכוללים אמנות ויצירה, נגינה ושירה, ספורט, פעילות במים.

**semantic_subset_count**

> מבין דנה, עומר, נועה, כמה בחרו סרטים בז׳אנר אימה?

תשובה: **2**

“המסור”, “לזמן את הרוע”: החיבור הוא אימה. מספר המשתתפים שבחרו בהם: 2.

## 11. English demonstration

**semantic_different_pair**

> Which pair picked movies in Horror, choosing different works or activities?

Answer: **Dana + Omer**

“Saw (film)”, “The Conjuring”: Horror. Players who made these choices: 2.

**semantic_count**

> How many players chose hobbies in Sport?

Answer: **3**

“Running”, “Association football”, “Surfing”: Sport. Players who made these choices: 3.

**semantic_diversity**

> Count different foods, not repeated picks: which of these cuisines connects the most?

Answer: **Italian cuisine**

“Pizza”, “Spaghetti”, “Lasagna”: Italian cuisine. Players who made these choices: 3. That makes 3 different choices in this family.

**locality_distance_pair**

> Which pair chose the towns that are closest by air distance?

Answer: **Noa + Amit**

Reẖovot and Rishon LeTsiyyon are about 9 km apart by air, comparing locality reference points, not homes or roads.

**music_artist_bridge**

> Which artist below is listed in the game under the music style chosen most often by this group?

Answer: **Omer Adam**

Mizrahi connects 2 players’ choices. Omer Adam is classified in that style; the connection is the musical style.

**semantic_filtered_mode**

> Among those who chose hobbies in Sport: Which of these film genres connects the most players’ movies?

Answer: **Horror**

“Running”, “Association football”, “Surfing”: Sport. Players who made these choices: 3. “Saw (film)”, “The Conjuring”: Horror. Players who made these choices: 2.

**semantic_intersection**

> Who connects both clues: movies in Thriller, and hobbies in Sport?

Answer: **Omer**

Omer connects them: “The Conjuring” → Thriller; “Association football” → Sport.

**semantic_nearby_pair**

> Among pairs with different hobbies in Sport and different towns, which pair’s towns are closest by air?

Answer: **Omer + Noa**

“Association football”, “Surfing”: Sport. Players who made these choices: 2. Tel Aviv and Reẖovot are about 21 km apart by air, comparing locality reference points, not homes or roads.

**district_activity_diversity**

> Which district brings together the widest variety of activity families through the hobbies chosen by its players?

Answer: **Central District**

Players from Central District chose hobbies spanning Arts and crafts, Making music, Sport, Water activities.

**semantic_subset_count**

> Among Dana, Omer, Noa, how many chose movies in Horror?

Answer: **2**

“Saw (film)”, “The Conjuring”: Horror. Players who made these choices: 2.

All 18 rule examples, options, correct answers, source fixtures and explanations are reproducible in [demo-results.json](scripts/knowledge/demo-results.json). The browser scenario separately exercises the real REST, native WebSockets and React screens with five mobile players.

## 12. Fact versus inference policy

Scored answers may use only consented player input, deterministic mathematics and trusted local classifications. Music style never proves a playlist; a hobby never proves personality; a city never proves demographic characteristics. Classifications are positive, potentially overlapping memberships, not exhaustive personal identities. Uncertain inputs do not acquire invented facts. Geographic comparisons use town reference points and air distances, never home addresses or road/travel predictions.

## 13. Unknown and consent behavior

Unknown inputs preserve their original profile text and remain usable by direct rules. Global semantic questions skip an incomplete dimension. Named-subset counts, displayed-pair questions and scoped intersections still work when at least three relevant participants have supported consented facts. Unknown/private participants are excluded from both the stated comparison and its options. No raw profile objects are retained in the semantic snapshot, and age/personal-fact/unknown keys are not enriched.

## 14. Results, reconnect and persistence

`question.ended` adds localized `explanation`, empty on legacy/direct questions. The frontend tolerates a missing explanation from older payloads. Active question payloads contain neither the explanation, knowledge version nor correct answer. Results reconnect repeats the full question/options/explanation plus only the recipient’s own result. Leaderboard/final reconnect retain their stage-specific protocol.

Finished questions store explanation and private knowledge version in additive cascading `question_explanations` rows. The application now has ten SQL tables. Reference entities/indexes remain local files and memory; no reference lookup makes a SQL query. Old records need no destructive migration and read with empty explanation/version. Real PostgreSQL tests verify creation, reads, upsert, rollback and retention cascades; scoring/statistics and winner behavior remain authoritative.

## 15. Raw/compressed size and repository impact

The eight runtime JSON files total **262,152 bytes** (256.0 KiB), including taxonomy and manifest. Concatenated gzip-9 size is **76,874 bytes** (75.1 KiB). Development curation is **60,281 bytes**. The data license notice and build/test/report code are additional small text files; the reference layer adds no images or dependency packages. A final repository byte-delta measurement appears in the verification addendum below.

Plain compact JSON, one entity per line, is retained for reviewability and reliable startup. Saving roughly 185 KiB with runtime compression does not justify another packaging/decompression path. Git already compresses stored text. No data are downloaded during Render build/start.

## 16. Measured startup, memory and lookups

Measured on macOS-26.5.2-arm64-arm-64bit-Mach-O, Python 3.14.0; local observations, not Render latency guarantees. Full machine-readable measurements: [benchmark-results.json](scripts/knowledge/benchmark-results.json).

| Measurement | Result |
|---|---:|
| Validated uncached bundle load, median of 10 | 25.046 ms |
| Instrumented load with tracemalloc | 186.830 ms |
| Retained Python knowledge allocations | 3,972,703 bytes |
| Peak Python allocation during load | 5,612,526 bytes |
| Complete cold application import, median of 5 fresh processes | 256.523 ms |
| Cold imported application median peak RSS | 87,949,312 bytes |
| 100,000 mixed known/unknown lookups, average | 6.243 µs |

Tracemalloc excludes native allocations; RSS includes the whole measured Python process, not just the knowledge. Lookups use in-memory hash indexes, approximately O(1) in catalog size plus O(input length) normalization. The validated bundle is cached once per process.

## 17. Generation benchmarks

| Scenario | Result |
|---|---:|
| 30 players → 20 questions, 20 runs, median | 60.085 ms |
| Same scenario, slowest measured run | 62.281 ms |
| 25 simulated rooms × 30 players × 20 questions, sequential total | 1504.301 ms |
| 30 players with one unknown movie, median of 10 | 65.613 ms |

` .venv/bin/python scripts/benchmark_knowledge.py ` regenerates measurements and demonstrations offline. Tests enforce wide sanity bounds (load <3 s, peak Python allocations <25 MB, three 30-player generations <5 s) rather than brittle microsecond thresholds. A separate real TCP smoke test exercises simultaneous classroom connections; the multi-room timing above is explicitly sequential.

## 18. Regression, E2E and concurrency verification

Final commands/results are recorded in the addendum below. Coverage includes Hebrew/English aliases; all six reference kinds; unknown and ambiguous matches; malformed/corrupt/oversized/symlinked data; schema/source integrity; each semantic family’s independently calculated answer; duplicate aliases; distinct-entity versus participant counts; positive cross-domain intersections; explicitly scoped partial knowledge; ties and geographic precision; no playlist/personality inference; consent invariance; deterministic replay across PYTHONHASHSEED values; no network/file/SQL access during generation; memory/performance; ended-only exposure; results/leaderboard/final reconnect; old-schema compatibility; PostgreSQL persistence; frontend escaping, language direction and attribution.

Browser scenarios complete English 20 rounds and Hebrew 7 rounds with three players, plus a Hebrew 20-round knowledge game with five mobile players. They exercise readiness, live answers, an authoritative timeout, scoring, statistics, progression, winner/final leaderboard and reconnects across stages. Network assertions observe no requests outside the local app/backend. The knowledge scenario requires at least ten semantic result explanations and real shared-film/cross-domain discoveries. Desktop/390px mobile screenshots were visually inspected; no horizontal overflow or browser errors were observed.

## 19. Security and deployment safety

Runtime treats the bundle as untrusted build input: schema, fixed filenames, file sizes, SHA-256, unique IDs/categories, valid dimensions, string limits, source licenses/dates, finite/bounded coordinates, entity limits and symlink rejection. No eval/exec or HTML rendering is used. Host/player result strings retain React escaping, tested with an HTML-injection-shaped explanation. Per-field consent remains the only profile boundary; no host tokens, credentials or other players’ raw profiles are broadcast. Existing authorization, malformed-frame, limits, deadline and reconnect tests remain green.

No production environment variable or dependency is added. Render remains `backend` build with `python -m pip install --upgrade pip && python -m pip install -r requirements.txt`, start `python -m app`, health `/api/v1/health`; the frontend remains `npm ci && npm run build`. Existing `DATABASE_URL`, `APP_ENV`, `FRONTEND_ORIGIN`, `HOST`, `PORT`, `VITE_API_BASE_URL` and `VITE_WS_BASE_URL` retain their meanings. The checked-in assets are under the backend root and load without a scraper or key. Neon remains application persistence only. `render.yaml`, environment examples and external services were not modified. No deployment or push occurred.

## 20. Limitations and maintenance

- The finite catalog cannot recognize every title, transliteration, recipe or locality. Unknowns and known ambiguities intentionally fall back; all-room questions become less available when consent/knowledge is sparse. This is a safety boundary, not a probabilistic guess.
- Genre and cuisine taxonomies are reference conventions and may overlap or differ between sources. Upstream data can contain errors/vandalism. The frozen release uses reviewed transformations, but it is not an expert-certified universal truth database. Future changes require review, versioning and regression tests.
- Common contextual aliases follow the documented Israeli/Hebrew/English catalog. Ambiguities outside its coverage may need new explicit names/years in a future release. No aggressive fuzzy or transliteration model is used.
- Geographic coordinates represent localities approximately; district coverage follows GeoNames and is not a boundary/sovereignty determination. Same-town and near-tie comparisons are suppressed where a unique answer is not justified.
- Artist records support reference-genre bridge questions. The profile still asks for a music style; it does not add an artist field or infer listening habits. No personalities, dietary suitability or driving times are inferred.
- Existing free-service constraints remain: one backend process, memory-only active games lost on restart, free-host cold starts and asynchronous finished-game persistence without a durable retry queue. Knowledge adds about 4 MB of retained Python data rather than an external service.

## Final verification addendum

All results below are from this knowledge-engine task and the final checked-in dataset, not the historical baseline. The two live PostgreSQL cases ran against a disposable local PostgreSQL 17 cluster, with no Neon credentials or external database involved.

| Command | Observed result |
|---|---|
| `MIZEMI_TEST_POSTGRES_URL=postgresql+psycopg://mizemi_test@127.0.0.1:55432/postgres .venv/bin/python -m pytest backend/tests -q` | **1,040 passed**, no skips, 6.20 s. One existing Starlette/httpx deprecation warning. |
| `npm --prefix frontend run type-check` | Passed. |
| `npm --prefix frontend test` | **295 passed**, 12 test files. |
| `npm --prefix frontend run build` | Passed, 38 transformed modules; JS 239.25 kB / 74.33 kB gzip and CSS 14.21 kB / 3.93 kB gzip. Existing logo asset unchanged. |
| `npm run test:e2e` (in `frontend`) | **3 passed**, 41.4 s. English 20 rounds / 3 players; Hebrew 7 rounds / 3 players; Hebrew knowledge 20 rounds / 5 players. |
| `.venv/bin/python backend/tests/smoke_classroom.py` | **Passed**, 1 host + 20 players, **21 real WebSockets**, 3 rounds, connect/answer bursts, identical broadcasts and final results; 0.20 s. |
| `.venv/bin/python scripts/build_knowledge_base.py` | Offline schema/hash validation passed. |
| `.venv/bin/python scripts/benchmark_knowledge.py` | Offline benchmarks and all 18 bilingual rule demonstrations generated successfully. Measurements in sections 15–17. |
| `.venv/bin/python scripts/check_secrets.py` | **206 source/config files**, zero high-confidence findings, zero local real-env files. A heuristic scan, not a proof that arbitrary secrets cannot exist. |
| `npm --prefix frontend audit --audit-level=low` | **0 vulnerabilities**, all severity levels. |
| `.venv/bin/python -m pip_audit --progress-spinner off` | **51 dependencies**, **0 known vulnerabilities**. |
| `.venv/bin/python -m pip check` | No broken requirements found. |
| `git diff --check` | Passed. |

The complete implementation changes/adds **58 files besides this report**, with a **472,580-byte net uncompressed source/data/documentation increase** relative to `029aa8e4f732d65c4048b7c3eb2e3a06f3b4f930`. This measurement excludes the unrelated lockfile and this self-referential report; it includes the source manifest, local data, curation, tests, benchmark/demo artifacts and edits to existing files. It measures tracked content, not machine-dependent `.git` pack size. The knowledge data itself remains 262,152 bytes.

Work stays on `feature/complete-mizemi-product`, committed in logical specification, knowledge, gameplay/persistence, frontend and verification groups. Nothing was pushed or deployed. The only unrelated worktree change remains `frontend/package-lock.json`: the same twelve removed `peer: true` metadata flags, preserved and unstaged. Render/Neon settings, credentials and services were not changed.
