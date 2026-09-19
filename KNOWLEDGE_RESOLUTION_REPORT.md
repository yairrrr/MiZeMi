# MiZeMi knowledge resolution

Measured on 2026-09-19 against the unchanged local catalog of **33,831 entities**. Baseline: commit `8fbd0dd`. This change adds local deterministic matching and improves final-question selection; it changes no reference facts, dependencies, public payloads, scoring, persistence, deployment settings, or frontend behavior.

**Result:** 64 previously missed imperfect inputs recovered, zero incorrect identities in the fixed 215-case evaluation, and knowledge-derived questions increased from **50.9% to 75.0%** of the final quizzes across the three realistic imperfect-input rooms. Those rooms now select **zero raw person lookups**. An unknown-only control retains one fallback question instead of padding the game.

## 1. Root cause

The resolver supported normalized full names, explicit aliases, and a narrow Hebrew full/defective spelling fold. It had no partial-title or edit-distance search. A typo therefore removed the participant's contribution from semantic analysis, often reducing coverage below a rule's eligibility threshold. The engine could not select a semantic question that was never generated.

Separately, the selector's direct-question share and per-rule allowances let raw identity lookups compete with useful group discoveries. Improving resolution alone would not address that selection behavior.

Some reported examples already worked: exact `רמת גן`, `קרית שמונה` / `קריית שמונה`, common hyphens, case differences, and existing Tel Aviv aliases. These are regression controls, not claimed new capabilities.

## 2. Baseline behavior and fixed evaluation

[`resolution-evaluation.json`](scripts/knowledge/resolution-evaluation.json) was frozen before changing the resolver. It contains 215 inputs: 41 canonical names, 106 imperfect variants, three short exact-name controls, and 65 inputs that must not resolve to an identity. Expected identities were verified against full names in the original local catalog. Inputs cover all seven domains, Hebrew and English, punctuation, aliases, missing/extra/swapped letters, partial names, near collisions, and deliberately unknown strings.

The same fixture also contains consented synthetic Israeli participant rooms of 10, 20, and 30 players, plus an unknown-only control. Before and after outputs use the same fixture, languages, seeds, and requested question count.

Fixture SHA-256:

```text
e31586ff17c0f5acdbf8a55223567ebea7c26395915a2c972a4e12a774dfccb5
```

Full evidence: [before](scripts/knowledge/resolution-before.json), [after](scripts/knowledge/resolution-after.json). The baseline was also replayed from an exported `8fbd0dd` backend to measure both versions with the same script, without changing the working checkout.

## 3. Resolver stages

`KnowledgeBase` remains the domain-facing API. New [`name_matching.py`](backend/app/domain/questions/name_matching.py) owns pure, bounded name search. The existing infrastructure loader still validates and loads the local assets.

1. Reject unsupported domains, non-text input, oversized input, and non-whitespace control characters.
2. Apply Unicode NFKC, case folding, whitespace collapse, punctuation/hyphen spacing, Hebrew mark removal, and quote normalization.
3. Look up full canonical names and explicit aliases; reject normalized name collisions.
4. Try conservative Hebrew spelling equivalence: internal doubled yod/vav and final-letter forms at word endings. Reject collisions.
5. For movies, songs, and artists, try a unique omitted English leading article or a strong whole-token partial name.
6. Narrow fuzzy candidates by domain, script, length, shared bigrams, and character-presence masks before computing bounded edit distance.
7. Accept only a sufficiently long, one-edit match above the similarity threshold and clearly separated from other entity identities. Otherwise return ambiguous or unknown.

Full names have a 200-character limit; approximate queries have a 64-character limit. Original player text is retained. No uncontrolled transliteration, embedding, LLM, external service, or runtime network call is added.

## 4. Confidence and fact policy

| Internal status | Meaning | Supplies an entity for scoring? |
|---|---|---|
| `EXACT` | Literal canonical title/name | Yes |
| `ALIAS` | Literal stored alias | Yes |
| `NORMALIZED` | Unique full name after safe normalization/spelling equivalence | Yes |
| `PARTIAL_HIGH_CONFIDENCE` | Unique sufficiently complete token partial | Yes |
| `FUZZY_HIGH_CONFIDENCE` | One edit, threshold and competitor margin satisfied | Yes |
| `AMBIGUOUS` | Multiple plausible identities or search budget exceeded | No |
| `UNKNOWN` | Unsupported, weak, too short, or insufficiently similar | No |

Results include a reason, candidate count, and fuzzy best/runner-up scores where applicable. Scores are deterministic comparison scores, **not probabilities**. These details stay internal and are not added to question text or public game payloads.

The existing full-name homonym rule is preserved: when *every* catalog entity with an exact typed name shares a positive classification, that shared fact can be used without resolving an identity. It never selects a particular homonym. Ambiguous partial and fuzzy matches do **not** use that exception and supply no inferred categories.

## 5. Thresholds and ambiguity protection

Minimum lengths count non-space characters and apply to both query and reference:

| Domain | Latin minimum | Hebrew minimum | Partial names |
|---|---:|---:|---|
| Movies | 7 | 5 | Enabled |
| Songs | 7 | 6 | Enabled |
| Artists | 7 | 5 | Enabled |
| Music styles | 6 | 5 | Disabled |
| Foods | 5 | 5 | Disabled |
| Hobbies | 6 | 5 | Disabled |
| Israeli localities | 6 | 5 | Disabled |

All domains require similarity **≥ 0.82** and a best-versus-second-entity gap **≥ 0.08**. Only one insertion, deletion, substitution, or adjacent transposition is accepted. Banded optimal-string-alignment distance examines two edits to detect competitors; a two-edit input is never accepted as a correction.

```text
score = 1 - edit_distance / min(max(query_length, reference_length), 20)
```

The denominator cap ensures an unexamined three-edit contender cannot invalidate the 0.08 margin for long titles. Candidate scores are combined by entity ID, so two aliases of one entity are not false competitors. Known Hebrew spelling collisions receive equal treatment; fuzzy matching cannot break a collision using orthography alone.

Fuzzy candidates must share a script. Numbers must match; movie/song Roman-number tokens must match too. This prevents correcting a sequel or year into another work. Short inputs such as `a`, `it`, and `rock` only resolve through a known full name/alias, never approximate guessing.

Partial matching requires at least seven characters. Other than dropping a stored English leading article, it needs at least two complete significant tokens in order and at least 80% significant-character coverage. All plausible token matches block guessing, including longer titles that fail that coverage threshold. Long catalog names remain indexed so they can block ambiguity. A weak partial is not promoted by a subsequent fuzzy guess.

At most 256 narrowed names receive distance comparisons. Exceeding the budget rejects the lookup; candidates are never silently truncated. A broad partial search also fails closed.

## 6. Before/after recognition

| Outcome, all 215 inputs | Before | After |
|---|---:|---:|
| Correct high-confidence identity | 83 | 147 |
| Incorrect identity | 0 | 0 |
| Ambiguous | 8 | 12 |
| Unknown | 124 | 56 |

The baseline's eight ambiguities were recognizable from its collision index but surfaced as `UNKNOWN` in the old API. The evaluator identifies them separately for comparison. The new API reports ambiguity explicitly.

| Imperfect inputs only, 106 total | Before | After |
|---|---:|---:|
| Correct | 39 (36.8%) | 103 (97.2%) |
| Ambiguous | 0 | 2 |
| Unknown | 67 | 1 |

**64 of the 67 previously missed imperfect inputs were recovered.** All 41 canonical controls and three short exact controls remained correct. These figures describe the fixed evaluation, not an estimated recognition rate for all real users.

## 7. False positives and rejected cases

There were **zero incorrect matches across 215 inputs** and **zero accepted identities among the 65 rejection cases**. Every accepted identity matched the expected entity. Tests independently cover synthetic near-collisions, insufficient score margins, alias collisions, short inputs, numeric sequels, long-title competitors, and Hebrew spelling collisions.

Deliberately unresolved positive examples:

| Input | Outcome | Reason |
|---|---|---|
| `Back to Future` | Ambiguous | Multiple matching works; no arbitrary film selection |
| `Lasgana` | Ambiguous | Competing nearby food names |
| `Mizraahhi` | Unknown | More than one edit |

`Harry Potter` and `הארי פוטר` remain ambiguous and contribute no derived categories. No unsupported franchise identity is invented.

Zero observed false positives is evidence for this corpus, not a proof against every possible user input. A misspelled name absent from the catalog can still resemble a different catalog name; conservative thresholds and rejection tests reduce that risk without eliminating it mathematically.

## 8. Representative recovered inputs

| Domain | Entered | Resolved name | Stage |
|---|---|---|---|
| Movie | `Conjuring` | The Conjuring | Partial |
| Movie | `The Conjruing` | The Conjuring | Fuzzy |
| Artist | `Omer Adma` | Omer Adam | Fuzzy |
| Song | `Blank Spce` | Blank Space | Fuzzy |
| Food | `Falafell` | Falafel | Fuzzy |
| Hobby | `Photograpy` | Photography | Fuzzy |
| Music style | `Electornic` | Electronic | Fuzzy |
| Locality | `Jeruslaem` | Jerusalem | Fuzzy |
| Locality | `רמת גנ` | רמת גן | Normalized final letter |

Regression examples include fullwidth `ＰＩＺＺＡ`, `קריית-שמונה`, `ת״א`, extra whitespace, curly apostrophes, Hebrew quotes, and English case changes. Existing explicit bilingual aliases remain authoritative.

## 9. Effect on final selected quizzes

Each room was evaluated in Hebrew and English with seeds 1, 11, and 37: six complete quizzes per room, 20 questions requested. Counts below were identical across those six runs. These are **final selected questions**, not candidate counts.

“Semantic” here means knowledge-derived questions, including geography and cross-domain analysis. “Basic” includes useful literal group counts, majority/comparison questions, and raw identity lookups. “Raw lookups” means the `unique_value` person-lookup rule specifically. “Unclassified” counts shared profile values that supply no supported category.

| Room | Total before → after | Semantic | Basic | Raw lookups | Unclassified values |
|---|---|---|---|---|---|
| 10 imperfect players | 17 → 20 | 7 → 15 | 10 → 5 | 2 → 0 | 40 → 2 |
| 20 imperfect players | 20 → 20 | 11 → 15 | 9 → 5 | 0 → 0 | 80 → 4 |
| 30 imperfect players | 20 → 20 | 11 → 15 | 9 → 5 | 0 → 0 | 120 → 6 |
| 10 unknown-only players | 2 → 1 | 0 → 0 | 2 → 1 | 2 → 1 | 60 → 60 |

Pooled across the three realistic rooms, semantic share rises from **29/57 = 50.9%** to **45/60 = 75.0%**. Across all 18 language/seed runs, that is **174/342 → 270/360**. The ten-player room improves from 41.2%; the other two improve from 55.0%.

Selected non-lookup questions rise from 55 to 60 across one game per realistic room, a useful quality proxy rather than a claim that every question has an objective quality score. The unknown-only room demonstrates that the engine neither fabricates classifications nor fills a requested 20-question game with repetitions.

## 10. Direct-question reduction and sample output

Raw person lookups now wait until all eligible non-lookup facts have been considered, including relaxed selection caps. They have a **hard maximum of one per quiz**, which is never relaxed. Existing ambiguity, settled-fact, variety, person, and source-field constraints remain. Useful simple group questions are preserved; there is no blanket ban on basic questions.

Actual final Hebrew questions from `imperfect_10`, seed 11:

| Question | Correct answer |
|---|---|
| אם מסתכלים על השירים האהובים עליכם, איזה סגנון מוביל? | פופ |
| איזה ז׳אנר מוזיקה הכי נפוץ בין האמנים האהובים שבחרתם? | מזרחית |
| איזה ז׳אנר חוזר הכי הרבה בסרטים שבחרתם? | אימה |
| באיזה אזור בארץ גרים הכי הרבה מכם? | המרכז |
| מבין מי שגרים במרכז, איזה סוג תחביב הכי נפוץ? | ספורט |
| מבין מי שבחרו סרטי אימה, איזה סגנון מופיע יותר בשירים שבחרו — רוק או אלקטרונית? | רוק |

The stored before/after outputs contain every selected question and answer in both languages for inspection. The remaining five basic questions in each realistic after-game are group counts/majorities/comparisons; none is a raw “who entered X?” question. Unknown-only data keeps one such fallback.

## 11. Consent and determinism

Resolution consumes only the existing consent-filtered `ProfileDataset`. Classifications are reused within that snapshot to avoid repeatedly resolving the same favorite across related dimensions. The cache is tied to both the snapshot and the knowledge instance; there is no global player-input cache or cross-room reuse.

Seven field-specific regression tests spy on the resolver and verify that a private sentinel never enters resolution. Changing a hidden value leaves the complete selected questions unchanged, including options, categories, counts, and explanations. Fuzzy resolution does not infer a hidden field from another field.

Candidate ordering, entity deduplication, and tie rejection are deterministic. Same profiles, catalog, language, and seed reproduce the same final quiz. Original profile text remains available to existing rules and explanations; no raw profile persistence format changes.

## 12. Performance and resource cost

Measured locally on Python 3.14; timings are not Render latency promises. Load timing is uninstrumented. Memory uses `tracemalloc` retained allocations for a freshly loaded knowledge layer after garbage collection, not total application RSS. The transient peak is reported separately.

| Metric | Before | After |
|---|---:|---:|
| Catalog load/index build | 593.421 ms | 1,554.793 ms |
| Mixed-corpus lookup mean, 2,150 lookups | 3.450 µs | 110.162 µs |
| 20 players / 20 requested, median of 20 rooms | 8.774 ms | 21.561 ms |
| 20 players / 20 requested, maximum | 9.976 ms | 26.241 ms |
| 30 players / 20 requested, median of 20 rooms | 10.392 ms | 23.247 ms |
| 30 players / 20 requested, maximum | 14.266 ms | 28.318 ms |
| 20 successive 30-player rooms, total | 212.351 ms | 467.662 ms |
| Knowledge retained allocations | 40,837,458 bytes | 58,771,367 bytes |
| Transient knowledge load allocation peak | 51,355,624 bytes | 75,429,331 bytes |

The new indexes add cost. Retained memory stays below the 60 MB target; load exceeds the 1-second target but stays within the 2-second acceptable budget. Generation stays well below 200 ms. No local reference assets or runtime dependencies were added or enlarged.

The realistic 30-player fixture repeats ten preference archetypes. To ensure caching does not conceal expensive unique-input behavior, a separate deterministic stress sample uses **210 distinct misspelled inputs**: 30 different choices in each of seven domains. It correctly resolves 209, rejects one, and incorrectly resolves zero. Ten fresh 30-player rooms each select 20 questions: **90.704 ms median, 93.663 ms maximum**. See [the distinct-input results](scripts/knowledge/resolution-distinct.json). This is a supplementary catalog-derived stress sample, not part of the 215-case before/after metric.

Indexes share normalized names and bigram strings, pack posting IDs into read-only integer buffers, and narrow by script/length before bounded comparisons. Full-name lookup remains approximately O(1). There is no full-catalog edit-distance pass, JSON parsing per question, database lookup per resolution, or network I/O.

## 13. Tests and reproduction

Full backend regression on the final runtime implementation:

```text
.venv/bin/python -m pytest backend/tests -q
1502 passed, 2 skipped, 1 warning in 39.13s
```

The skips are the existing optional live PostgreSQL checks without a disposable database. The warning is the existing Starlette/httpx deprecation. Frontend tests and browser E2E were not rerun for this backend-only task; frontend behavior and dependencies were untouched.

The repository secrets scanner checked 243 source/config files with zero high-confidence findings and zero local real-env files. `git diff --check` passed. The pre-existing README, legal report, and frontend lockfile changes were verified byte-for-byte unchanged.

Coverage includes all matching stages/domains, Hebrew/English aliases, normalization, false-positive controls, partial/fuzzy ambiguity, short names, protected sequel tokens, long-title collisions, bounded candidate comparison counts, one/two-edit behavior, consent, offline execution, deterministic replay, final selected quizzes, and performance/memory limits. Banded edit distance is checked against an independent full-matrix reference. Existing question/scoring/realtime/persistence tests remain green.

Reproduce current evaluation without overwriting the recorded evidence:

```sh
.venv/bin/python scripts/evaluate_knowledge_resolution.py --label current --output /tmp/mizemi-resolution-current.json --memory
.venv/bin/python scripts/benchmark_resolution_distinct.py --output /tmp/mizemi-resolution-distinct.json
.venv/bin/python -m pytest backend/tests/unit/test_knowledge_resolution.py -q
.venv/bin/python scripts/check_secrets.py
git diff --check
```

Reproduce baseline against the same current fixture/script:

```sh
baseline_dir=$(mktemp -d)
git archive 8fbd0dd backend | tar -x -C "$baseline_dir"
.venv/bin/python scripts/evaluate_knowledge_resolution.py --backend "$baseline_dir/backend" --label before-8fbd0dd --output /tmp/mizemi-resolution-baseline.json --memory
```

No API keys, account setup, dataset download, or runtime internet access is required.

## 14. Remaining limitations

- Conservative matching intentionally leaves some recoverable-looking inputs unresolved, especially short names, two-edit mistakes, ambiguous franchises, and dense clusters of similar titles.
- Partial matching applies only to media titles/names; arbitrary city, food, hobby, and music-style substrings are not accepted.
- No general Hebrew/English transliteration system is introduced. Recognition still depends on explicit catalog aliases.
- Correct resolution cannot repair an incorrect source classification. The existing dataset provenance and limitations still apply.
- Benchmark groups are synthetic and the fixed corpus is finite. Future real-world examples should add both positive and near-collision rejection cases before any threshold is relaxed.
- Startup is slower and retained allocations are close to the 60 MB knowledge-layer target. Whole-process production memory was not measured here; no deployment was performed.
- The final count can be lower than requested when insufficient varied, supported facts remain. This is intentional.

No push, deployment, Render/Neon change, or unrelated frontend lockfile change was performed.
