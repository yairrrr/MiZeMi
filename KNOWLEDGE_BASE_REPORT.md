# MiZeMi group intelligence — verification report

Verified locally on **2026-09-14**, bundle **2026-09-14.1**. The production engine has **27 group-first rule families** over **33,831 offline reference entities**. It discovers patterns in consented participant choices. No runtime AI, reference-provider request, paid API, new dependency, deployment, push, Render change or Neon change was introduced.

> **Update (category-first revision).** The question selection described below was diagnosed as not reaching realistic rooms: its group families required every player's answer to be recognized. Production now uses the category-first engine documented in [QUESTION_ENGINE_DIAGNOSTIC.md](QUESTION_ENGINE_DIAGNOSTIC.md) and MASTER_SPEC.md §12.3, with the current audit in [QUESTION_STYLE_AUDIT.md](QUESTION_STYLE_AUDIT.md). The knowledge bundle, sources and licenses in this report are unchanged; the rule catalog, selection targets, audit counts and measurements below describe the previous revision (current measurements are in the diagnostic's Performance section; `benchmark-results.json` now holds them).

**Resolution follow-up (2026-09-19):** [KNOWLEDGE_RESOLUTION_REPORT.md](KNOWLEDGE_RESOLUTION_REPORT.md) supersedes the historical exact/alias-only resolution and resource measurements below. It records conservative normalized/partial/fuzzy resolution, confidence and ambiguity rejection, the frozen before/after corpus, final quiz impact and a hard one-question limit for raw person lookups. Reference entities, facts, source files and licenses are unchanged.

## Recovery and preserved architecture

**Media follow-up:** [MEDIA_QUESTIONS_REPORT.md](MEDIA_QUESTIONS_REPORT.md) and MASTER_SPEC.md §12.4 document the focused movie/song/artist generation and selection improvements after the category-first revision. Reference assets, licenses and resolution behavior remain unchanged. Current media samples and regression results are in that follow-up report.

Started from deployed `main` at `a3d4570` and created local branch `codex/group-intelligence`. The repository already contained the working multiplayer product, 29 historical profile rules and the 18-rule v4 knowledge extension. It did not match the much older interrupted-frontend handoff, so completed product work was preserved. Baseline: 1,038 backend tests passed, two optional PostgreSQL tests skipped; the only local modification was twelve removed `peer: true` metadata flags in `frontend/package-lock.json`. That diff remains untouched and unstaged.

FastAPI/native WebSockets, pure Python domain logic, React/TypeScript/Vite, SQLAlchemy, authoritative timing/scoring, host credentials, reconnect, consent and finished-game persistence remain intact. Default length remains 20 questions, with the existing 20-second timeout and existing scoring/tie policy. No schema migration or new environment variable is required. The nine-field profile envelope extends the previous seven fields with independently consented optional favorite artist and song answers; old submissions remain valid.

## Architecture and factual policy

Development research → compact factual cache → reviewed offline compiler → schema/hash-validated versioned assets → one cached immutable knowledge index → consent-only semantic snapshot → group analysis → candidate validation/selection → question → ended-only explanation.

`app/infrastructure/knowledge.py` validates files and owns loading. `app/domain/questions/knowledge.py` supplies frozen structured facts and exact/alias lookup. `semantic.py` enriches only the copied consented dataset. `group_rules.py` contains production group reasoning. Rules never open JSON, query SQL or fetch a source. The browser receives the public question and, after it ends, its answer/explanation; it receives neither the reference catalog nor other players’ raw profiles.

Scored reasoning uses submitted consented choices, supported local classifications and deterministic mathematics. An artist’s genres do not prove a participant’s playlist. A song uses its own genre statements, never its performer’s usual style. Countries and release/series details support compact reference provenance and disambiguation; no production rule asks entity trivia about them. There are no stereotypes, personality predictions, demographic guesses or probabilistic scored questions.

Every derived fact inherits its source field’s consent. Whole-group questions require recognized, positively classified input for every relevant participant/dimension. Unknown entities or missing dimensions are not treated as negative membership. Limited questions explicitly name 3–6 known participants. A hidden answer can be changed arbitrarily without changing generated questions; regressions cover all seven knowledge-bearing profile fields. Legacy literal rules also reject fields containing different known aliases of the same entity, so `Saw` and `המסור` cannot falsely become different favorites.

## Exact coverage and storage

| Domain | Entities | Hebrew names | Additional aliases | Usable normalized keys | Bytes |
|---|---:|---:|---:|---:|---:|
| movies | 11,228 | 7,457 | 25,856 | 43,081 | 2,167,757 |
| music | 66 | 66 | 46 | 173 | 6,352 |
| artists | 6,655 | 5,875 | 1,015 | 13,141 | 723,864 |
| songs | 9,700 | 5,422 | 40,737 | 51,439 | 2,274,445 |
| foods | 3,279 | 1,292 | 282 | 4,778 | 334,260 |
| hobbies | 1,679 | 1,300 | 59 | 2,756 | 242,231 |
| localities | 1,224 | 1,167 | 630 | 2,813 | 154,180 |

There are **68,625 additional alias strings**, **118,181 usable normalized lookup keys**, and **1,415 rejected collision keys**. Names themselves are counted separately from aliases. A real native title is retained if no English title exists; no translation is invented. Some stored variants normalize to the same lookup key.

Raw JSON: **5,914,597 bytes (5.91 MB)**. Gzip of the logical bundle: **1,332,588 bytes (1.33 MB)**. Compared with v4’s 262,152 raw / 76,874 gzip bytes, the reference-data repository increase is **5,652,445 raw bytes** and **1,255,714 gzip bytes**. Gzip measures compressibility, not an asserted Git pack size. Plain compact JSON is deployed; compression would add fragility without a resource need. Both curation recipes total 71,914 bytes; source caches and browser test artifacts are excluded from Git.

The pool was expanded from 2,434 to 33,831 useful entries (about 13.9×). Film/artist totals modestly exceed guideline ranges because animated works and Israeli artists materially improve coverage while using little space. Unsupported dishes/activities and works without useful genres were omitted instead of padded into quotas. The catalog remains far below the 20 MB target and 30 MB review threshold.

The four published synthetic groups recognize 24/24 cities, foods, hobbies and chosen music styles; 23/24 films (one deliberately unlisted); 5/5 artists and 5/5 songs. This is reproducible fixture recognition, **not a measured coverage claim about the Israeli population**. Entity recognition differs from dimension completeness: food format and physical-activity facts cover 21/24 sample participants, so unsupported whole-group questions are skipped. Broad region, hobby family/setting and cuisine cover 24/24. See the measured JSON for every numerator and denominator.

## Taxonomies, aliases and geography

The 103 bilingual labels cover 18 film genres/types, 24 music genres, 18 cuisine associations, 14 food formats, 14 hobby families, three conventional settings, two physical-activity classes, six districts and four broad regions. Production hobby-family comparisons use 11 comparable broad families; fitness/water contribute to sport and making music contributes to creative hobbies without becoming competing child answers.

Food associations do not declare exclusive national ownership. No dietary/allergy guarantee is inferred. Physical exercise differs from tabletop/mind games. Activity settings describe the conventional activity, not where someone actually practises it; flexible activities count on neither side of indoor-versus-outdoor comparisons. Unknown settings remain unknown. Team/individual participation and arbitrary “most multidisciplinary person” scores are intentionally not invented where coverage/definition is insufficient.

Regions group provider districts: North + Haifa → north; Central + Tel Aviv → center; Southern → south; Jerusalem remains distinct. Unmapped districts remain unknown. Locality reference points support great-circle distance, never home location or driving time. No pairwise-distance table is stored. Broad government coverage was investigated, but the imported geography is the explicitly licensed GeoNames aggregation, not an official Israeli registry.

Normalization uses Unicode NFKC, casefold, collapsed whitespace, selected punctuation/quote variants and Hebrew point removal. Only exact normalized names or known aliases resolve. No fuzzy similarity is used. Known collisions remain UNKNOWN even against a canonical name: remakes/song titles often need a year or performer qualifier. Qualified activity names stay qualified unless a synonym is reviewed; a narrower track-running record does not mask general `ריצה`. Examples include `ת״א` / `Tel-Aviv`, `היפהופ` / `hip hop`, `פיצה` / `Pizza`, and `המסור` / `Saw`.

## Sources, licenses and reproducibility

- [Wikidata structured facts](https://www.wikidata.org/wiki/Wikidata:Licensing): CC0. Reviewed seeds date to 2026-09-11; the expansion was retrieved over 2026-09-13–14. Stored projections use IDs, names, genres, bounded subclass/instance/cuisine relationships and optional release/country/series/performer details. Popularity/sitelink counts and Israeli-origin selection identify useful reference coverage only; they never score preferences or infer a player’s identity.
- [GeoNames country extract](https://download.geonames.org/export/dump/IL.zip), [format/license](https://download.geonames.org/export/dump/readme.txt): CC BY 4.0, refreshed 2026-09-13 from a 582,338-byte archive. **Contains information from GeoNames, available under CC BY 4.0; MiZeMi filtered, normalized and adapted the data.** Attribution ships in the app and [LICENSES.md](backend/app/data/knowledge/LICENSES.md).
- The [official Population Authority locality package](https://data.gov.il/he/datasets/population_authority/citiesandsettelments) exposed an unspecified `other-open` license via its keyless metadata API. Its bulk CSV was not imported. [MusicBrainz](https://musicbrainz.org/doc/About/Data_License) core and supplementary/tag licenses differ; its tags were not imported. No IMDb/TMDB bulk data, copyrighted prose, lyrics, images, raw API responses, paid service or key was used.

The [manifest](backend/app/data/knowledge/manifest.json) records dates, licenses, transformations, per-file hashes/row counts and cache/curation hashes. Reviewed seeds retain revisions; new WDQS projections use revision 0 with dated snapshot provenance rather than invented revisions. Source checksums establish integrity, not universal factual correctness.

The [build guide](scripts/knowledge/README.md) documents finite queries, source terms, transformations, rejected sources and exact commands. `expand_knowledge.py --fetch` is development-only, sequential and paced (now four seconds between requests); it stops on rate-limit/Retry-After responses. Requested 120-second pauses were honored. Expensive discovery queries were replaced with bounded fixed-root/focused selections. `compile_group_knowledge.py` is entirely offline. A complete rebuild from the reviewed cache was verified **byte-identical** to the committed bundle. Fresh public-source updates can change data and require review/versioning.

Factual review caught and corrected an inherited overbroad Eden Ben Zaken classification, excludes disaster-film → thriller as sufficient genre evidence by itself, and preserves general running when a narrower discipline has a qualified name. These decisions and source links are in `group-curation.json.review_notes`. Apple Music was used only to spot-check one artist association; no Apple catalog or prose was imported. Saw remains supported as horror/crime; a thriller label was not invented from the prompt.

## Previous production rule catalog (superseded)

Kept for the record; the families below remain under regression tests but are no longer the production registry.

| Rule | Difficulty | Group discovery / eligibility |
|---|---|---|
| `group_count` | EASY | Positive people count for a genre, cuisine, food family, activity family/setting or physical activity; complete dimension. |
| `group_scoped_count` | EASY | Explicitly named 3–6-person scope when whole-group knowledge is incomplete; fallback priority. |
| `group_mode` | EASY | One strict leading film/food/hobby/music/artist/song category; at least two holders. |
| `group_unique` | EASY | Exactly one person in the named supported category. |
| `group_comparison_semantic` | MEDIUM | Compare two represented categories with unequal counts; flexible settings excluded. |
| `group_diversity` | MEDIUM | Count 2–6 represented families; chosen music-style aliases count once, cuisine parent duplication is excluded. |
| `group_different_pair` | MEDIUM | Exactly two holders chose distinct canonical foods/hobbies in the stated family; used sparingly. |
| `region_majority` | EASY | One leading region; “majority” wording only when strictly over half. |
| `region_unique` | EASY | Exactly one singleton region across the group, not an arbitrary pick among outliers. |
| `geographic_outlier` | MEDIUM | Highest average distance to every other participant’s locality, separated by at least 1 km. |
| `group_filtered_mode` | HARD | Proper subgroup of at least three; one strict target-family winner with at least two holders. |
| `group_intersection_count` | HARD | Count the proper intersection of two positive cross-domain classes, each individually containing at least two people. |
| `region_hobby_diversity` | HARD | Region with uniquely most distinct broad hobby families; at least two participants/families there. |
| `locality_extreme` | EASY | Unique north/south locality; latitude separation at least 0.01°. |
| `locality_distance_pair` | MEDIUM | Unique nearest/farthest pair with at least 1 km separation from runner-up; same-town/tied winners rejected. |
| `locality_distinct` | EASY | Count canonical towns despite alternate spellings. |

Eleven preserved clear legacy families complete the 27: `unique_value`, `most_common_value`, `value_count`, `group_comparison`, `age_ranking`, `second_largest_group`, `filtered_mode`, `category_coverage`, `balanced_split`, `group_exception`, `least_common_value`. They require complete relevant consented raw input and reject known alias splits. Direct age-value identification/counts are disabled; age ranking is capped at one per game. Person-similarity/fingerprint/anchor puzzles and the old music-artist trivia bridge remain historical implementations under regression tests but are **not selected in production**.

Selection targets approximately 30% simple group, 35% semantic, 20% geographic/cross-domain and 15% clear legacy questions, redistributing unsupported shares. There is no trivia quota. Direct/scoped fallbacks have lower priority. Person-answer questions are capped at five per 20; direct lookups, repeated pairs and family repetitions have additional caps. Count/unique questions about the same membership set are not repeated through parent/child labels. EASY → MEDIUM → HARD order is preserved; actual difficulty proportions depend on available facts. Ties never acquire a winner through ID ordering. Fewer questions are returned transparently when quality/consent cannot support the requested length.

## Acceptance discoveries and question-style audit

The real-reference tests prove these without players typing the derived words:

- `המסור`, `לזמן את הרוע`, `שרק`, qualified `טיטניק` → horror is the unique leading genre in the four-person fixture. A separate fixture has exactly one horror choice: “רק אחד בקבוצה בחר סרט בז׳אנר אימה. מי זה?”
- `ריצה`, `כדורגל`, `גלישה` → sport count. “כמה אנשים בקבוצה בחרו תחביבים שקשורים לספורט?”
- `פיצה`, `פסטה`, `לזניה` → Italian cuisine leads. “לפי המאכלים שבחרתם, איזה מטבח הכי פופולרי בקבוצה?”
- `תל אביב`, `רמת גן`, `ראשון לציון` → central-region majority. “מאיזה אזור בארץ מגיע רוב הקבוצה?”
- Conventional activity classifications → “מה נפוץ יותר בקבוצה: תחביבי חוץ או תחביבים במקומות סגורים?” Flexible hobbies are counted in neither group.
- Omer Adam + Taylor Swift, and independently *Shake It Off* + *Blank Space*, supply shared pop classifications; Metallica / *Enter Sandman* provide contrasting metal facts. Artist and song consent and genres remain independent.

English examples include “Which cuisine is most popular in our group’s food choices?”, “Who lives furthest from the rest of our group, on average?”, and “Among people from Central Israel, which cuisine is most common?” Multi-hop discoveries include hobby-sport → favorite-film horror majority, central-region → favorite-food Italian majority, and favorite-food Italian → creative-hobby intersection count. These are group statistics, not personality/playlist inference.

[QUESTION_STYLE_AUDIT.md](QUESTION_STYLE_AUDIT.md) records **all eight complete 20-question sample games**, with 144 GOOD, 16 ACCEPTABLE and 0 BAD final questions. It includes rejected trivia, database wording, prior-familiarity puzzles, parent/child ambiguity and overcomplicated diversity inventories. [group-games.json](scripts/knowledge/group-games.json) contains every synthetic profile, option, answer and explanation; [demo-results.json](scripts/knowledge/demo-results.json) supplies additional rule examples. Hebrew grammar was reviewed for singular/plural, question clarity and explanations. Legacy questions may retain an empty explanation; new semantic questions explain their supporting choices after the question ends.

## Measured performance

Measured on macOS-26.5.2-arm64-arm-64bit-Mach-O, Python 3.14.0, with the published deterministic scripts and no reference/DB lookups in generation. Decimal MB below; this is a local measurement, not a claim to have tested the deployed Render host.

| Measurement | Result | Requested target |
|---|---:|---:|
| Raw reference JSON | 5.91 MB | ≤20 MB |
| Retained Python knowledge allocation | 39.52 MB | ≤60 MB |
| Peak Python allocation during load | 49.80 MB | review at 80 MB |
| Uninstrumented load, 10 runs | median 591.0 ms; max 595.4 ms | ≤1,000 ms |
| Fresh-process app import/construction, 5 runs | median 808.0 ms; RSS 155.9 MB | report separately |
| 100,000 lookups | mean 6.44 µs | near O(1) index access |
| 30 players / 20 questions, 20 runs | median 16.92 ms; max 21.77 ms | ≤200 ms |
| 25 simulated 30-player rooms | 423.6 ms total | classroom sanity |
| 30 players with one unknown film | median 15.67 ms | graceful fallback |

The 30-player benchmark includes all eight game-relevant inputs, including artist/song. `tracemalloc` slows loading to 4542 ms; that instrumented number is not the startup SLA. The benchmark process itself peaks at 262.4 MB RSS while retaining instrumentation/temporary loads; it is not the knowledge-layer footprint. [benchmark-results.json](scripts/knowledge/benchmark-results.json) records all bytes, aliases, timings and coverage dimensions.

## Final regression, classroom and security verification

| Exact command / check | Result |
|---|---|
| `MIZEMI_TEST_POSTGRES_URL=postgresql+psycopg://mizemi_test@127.0.0.1:55432/mizemi_group .venv/bin/python -m pytest backend/tests -q` | **1,071 passed**, no skips; one pre-existing Starlette/httpx deprecation warning. Includes knowledge, all historical/new engines, scoring, auth, deadlines, reconnect, persistence and PostgreSQL. |
| `npm run type-check` (frontend) | Passed. |
| `npm test` (frontend) | **299 passed**, 12 files. |
| `npm run build` (frontend) | Passed; production Vite bundle built. |
| `npm run test:e2e` (frontend) | **3 passed**: 20-round English/3 players; 7-round Hebrew/3 players; 20-round Hebrew knowledge/5 players including artist/song inputs. |
| `.venv/bin/python backend/tests/smoke_classroom.py` | **1 host + 20 players, 21 real WebSockets, 3 rounds**; connect/answer bursts, consistent broadcasts and final state passed. |
| `.venv/bin/python scripts/check_secrets.py` | No high-confidence findings or real local env files; expanded JSON assets included. |
| `npm audit --json` | **0 vulnerabilities**. |
| `.venv/bin/pip-audit --format json` | **0 known vulnerabilities**, 51 installed packages audited. |
| `.venv/bin/python -m pip check` | No broken requirements. |
| `git diff --check` | Passed. |
| Full offline compiler rebuild + byte comparison | Identical JSON artifacts. |

The temporary PostgreSQL cluster used a disposable UTF-8 database; no Neon account/credential was involved. E2E covers authoritative timeout/all-answer completion, one accepted answer, scores/statistics, host advancement, final winner, reloads in multiple states and no external browser requests. Active/reconnect frames expose neither correct answer nor explanation; ended frames restore results; final explanations/versions persist. Host/player authorization remains covered by the full suite.

The security review found no new runtime fetch/eval/exec path, HTML rendering of knowledge strings, unsafe SQL interpolation or secret exposure. Files are bounded, hash/schema validated, and immutable when indexed. Tests reject invalid years/IDs/metadata, duplicate aliases/entities/JSON keys, wrong dimensions, symlinks, nonfinite coordinates, bad provenance and oversized files. The local secrets scanner reports locations only, never matched values. No repository upload to a security scanner occurred.

## Remaining limitations and release boundary

Coverage is deliberately incomplete. Genres/cuisines can overlap and public community classifications are not exhaustive or error-free; supported positive classifications form the game’s reviewed operational taxonomy. Missing dimensions, ambiguous titles, unsupported transliterations and long-tail inputs reduce available questions. The synthetic recognition rate is not a population survey. Source corrections require a reviewed offline rebuild/version change; there is no runtime enrichment service.

GeoNames points are locality reference points, not homes or travel distances. Indoor/outdoor describes conventional settings; no participant behavior is inferred. Some artist/film counts exceed rough coverage guidelines but remain far below resource limits. The existing single-process/free-host limitations remain: active rooms do not survive a process restart; completed records follow existing retention. One old dependency deprecation warning remains without a known audited vulnerability.

Render configuration, Neon settings, database architecture, dependencies and the unrelated lockfile metadata are unchanged. The backend deploys the committed JSON with its ordinary source files; the frontend requires the matching backend for the two optional new inputs. No new environment variable, migration, paid dependency or external account setup is needed for this revision. The work is delivered as local logical commits on `codex/group-intelligence`; final commit IDs/status are supplied with delivery. **No push or deployment was performed.**
