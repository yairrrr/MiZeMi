# E2E semantic assertion report

Date: 2026-09-15. Branch: `codex/e2e-semantic-assertion`. Baseline: `dc2b1441a819ad204bab951a9d7046deea304ed2` (current `origin/main`). No production Question Engine, scoring, consent, public contract, deployment or dependency changes.

## 1. Exact root cause and repository state

The original checkout is `codex/github-pages-landing` at `8fbd0dd0fb242b05820199d67d157d832fd7896e`. It still contains the obsolete assertions at lines 212–213. They require one explanation containing both movie titles “המסור” and “לזמן את הרוע”, and another containing both “ספורט” and “אימה”. These combinations are not guaranteed product contracts; valid group-first selection chooses other supported facts.

**Both “המסור” and “לזמן את הרוע” are `favorite_movie` values. Neither is an artist or song in this fixture.** The optional artist and song fields were traced separately.

The initial replacement was already merged into main through PR #50, commit `31aefaa58bb44557a67d1eaa72347e4a158e8aba`. It was preserved rather than duplicated. PR #51's merge retained it. Current-main [Verify classroom game run 34937974561](https://github.com/yairrrr/MiZeMi/actions/runs/34937974561) passed backend/PostgreSQL, lifecycle, frontend, Browser game, concurrency and security/dependency stages. The older branch's [push run 34937939941](https://github.com/yairrrr/MiZeMi/actions/runs/34937939941) failed at the obsolete line 212.

A detached checkout of `8fbd0dd` reproduced that exact failure locally **before edits**: `npm run test:e2e -- --grep knowledge-he` completed the 20-round game, then failed at line 212 (`Expected: true; Received: false`); scenario duration 9.2s. No files from the original checkout's uncommitted changes were copied.

## 2. Production versus test

**Production behavior was correct; the old assertion was stale.** The failed game's final selection contains 10 semantic, 3 direct, 4 geographic and 3 cross-domain questions. It materially derives movie, artist, song, hobby and food classifications.

The actual fixture establishes:

- Artists → Pop (`פופ`), four participants, from their submitted artist choices.
- Songs → Pop (`פופ`), four participants, independently from the submitted songs.
- Declared music style → Mizrahi (`מזרחית`), two participants. This direct preference does not substitute for artist/song derivation.
- Movies → several genres tie at two people; there is no unique Horror leader. The selected adventure-versus-crime comparison correctly answers adventure: two versus one.
- Hobbies → three physically active/sport choices and two creative choices.

No production question or explanation was changed to force a title pair into the selection.

A further **test verification gap** was reproduced on the existing merged fix: a song-leader explanation could replace the artist-leader explanation and still pass, because both said four people and a leading genre. New negative tests also showed that a wrong-genre explanation and unrelated but plausible Hebrew were accepted. Before strengthening the verifier, these three cases failed with `DID NOT RAISE AssertionError` (3 failed, 17 passed, 0.93s). This is a gap in what the test proves, not an observed incorrect production explanation.

## 3. Actual failed-fixture questions, answers and explanations

Playwright does not configure one global fixed seed. The application derives a stable seed from each game's ID. This failed game's persisted record was replayed with its exact profiles, player IDs and seed; both traces were identical, and the replay's question IDs, texts, correct options and explanations matched the played game.

Captured seed: `5245889277706481826`. Deterministic replay: **PASS**. All data below are from the synthetic classroom fixture.

### 1. SEMANTIC_MAJORITY — song

אם מסתכלים על השירים האהובים עליכם, איזה סגנון מוביל?

Options: פופ · רוק · אלקטרונית · אר אנד בי

Answer: **פופ**

Explanation: 4 אנשים בחרו שירים בסגנון פופ — יותר מכל סגנון אחר. במקום השני: רוק (2). בין הבחירות: Shake It Off, Blank Space, Yellow ועוד 1.

### 2. SEMANTIC_MAJORITY — artist

איזה ז׳אנר מוזיקה הכי נפוץ בין האמנים האהובים שבחרתם?

Options: רוק · מזרחית · ים תיכונית · פופ

Answer: **פופ**

Explanation: 4 אנשים בחרו אמנים שמזוהים עם מוזיקת פופ — יותר מכל סגנון אחר. בין הבחירות: עומר אדם, עדן בן זקן, טיילור סוויפט ועוד 1.

### 3. SEMANTIC_COUNT — hobby

לכמה מכם יש תחביב שדורש פעילות גופנית?

Options: 4 · 3 · 1 · 2

Answer: **3**

Explanation: 3 אנשים בחרו תחביבים עם פעילות גופנית: ריצה, כדורגל, גלישה.

### 4. DIRECT_CHOICE — music

איזה סגנון מוזיקה הכי פופולרי כאן?

Options: פופ · מזרחית · ג׳אז · רוק

Answer: **מזרחית**

Explanation: 2 אנשים בחרו מוזיקה מזרחית — יותר מכל סגנון אחר.

### 5. DIRECT_AGE — age

מי המבוגר ביותר מבין המשתתפים ששיתפו את הגיל שלהם?

Options: עמית · עומר · נועה · ליאור

Answer: **ליאור**

Explanation: (Direct round; no explanation.)

### 6. DIRECT_UNIQUE — place

מי היחיד/ה שגר/ה ב"תל אביב"?

Options: דנה · עמית · עומר · ליאור

Answer: **עומר**

Explanation: (Direct round; no explanation.)

### 7. SEMANTIC_COUNT — food

כמה מהמאכלים שבחרתם הם מהמטבח המזרח תיכוני?

Options: 2 · 1 · 0 · 3

Answer: **1**

Explanation: אדם אחד בחר מאכל מזרח תיכוני: פלאפל.

### 8. GEO_REGION_MAJORITY — place

רוב הקבוצה גרה באותו אזור. באיזה?

Options: אזור ירושלים · הדרום · הצפון · המרכז

Answer: **המרכז**

Explanation: 3 אנשים גרים במרכז — יותר ממחצית הקבוצה.

### 9. SEMANTIC_COUNT — song

כמה אנשים בחרו שיר אהוב בסגנון אלקטרוני?

Options: 3 · 0 · 2 · 1

Answer: **1**

Explanation: אדם אחד בחר שיר בסגנון אלקטרוני: Blank Space.

### 10. GEO_REGION_COUNT — place

כמה מכם מגיעים מהצפון?

Options: 2 · 0 · 3 · 1

Answer: **1**

Explanation: אדם אחד גר בצפון: חיפה.

### 11. SEMANTIC_COMPARISON — movie

אם מסתכלים על בחירות הסרטים, איזה צד מנצח — הרפתקאות או פשע?

Options: הרפתקאות · פשע

Answer: **הרפתקאות**

Explanation: 2 אנשים בחרו סרטי הרפתקאות, לעומת אדם אחד שבחר סרט פשע.

### 12. SEMANTIC_UNIQUE — food

מי היחיד/ה בקבוצה שבחר/ה מאכל אסייתי?

Options: דנה · ליאור · נועה · עומר

Answer: **עומר**

Explanation: עומר: סושי.

### 13. SEMANTIC_DIVERSITY — artist

כמה סגנונות מוזיקה שונים מיוצגים באמנים שבחרתם?

Options: 5 · 4 · 6 · 3

Answer: **5**

Explanation: 5 סגנונות: פופ, רוק, מזרחית, ים תיכונית וקאנטרי. בחירה אחת יכולה להשתייך לכמה סגנונות; כל סגנון נספר פעם אחת.

### 14. SEMANTIC_UNIQUE — movie

רק אדם אחד בקבוצה בחר סרט פשע. מי זה?

Options: ליאור · דנה · נועה · עמית

Answer: **דנה**

Explanation: דנה: המסור.

### 15. GEO_CLOSEST_PAIR — place

אילו שניים מכם גרים הכי קרוב זה לזה?

Options: עומר + עמית · נועה + ליאור · דנה + עומר · נועה + עמית

Answer: **נועה + עמית**

Explanation: נועה ועמית גרים ברחובות ובראשון לציון, כ־9 ק״מ זה מזה בקו אווירי.

### 16. SEMANTIC_COMPARISON — artist

בין האמנים שבחרתם, איזה סגנון מופיע יותר — רוק או קאנטרי?

Options: רוק · קאנטרי

Answer: **רוק**

Explanation: 2 אנשים בחרו אמנים שמזוהים עם מוזיקת רוק, לעומת אדם אחד שבחר אמן שמזוהה עם מוזיקת קאנטרי.

### 17. GEO_REGION_DIVERSITY — place

מכמה אזורים בארץ מגיעים חברי הקבוצה?

Options: 3 · 4 · 2 · 1

Answer: **3**

Explanation: 3 אזורים: הצפון, המרכז והדרום.

### 18. CROSS_SUBGROUP_MAJORITY — hobby,music

מבין מי שבחרו תחביב ספורטיבי, איזה סגנון מוזיקה הכי נפוץ?

Options: רוק · מזרחית · ג׳אז · פופ

Answer: **מזרחית**

Explanation: 3 אנשים בחרו תחביבי ספורט. מתוכם, 2 בחרו מוזיקה מזרחית — יותר מכל סגנון אחר.

### 19. CROSS_SUBGROUP_COMPARISON — food,hobby

מבין מי שבחרו אוכל איטלקי, מה יותר נפוץ — תחביבי ספורט או תחביבי יצירה?

Options: תחביבי ספורט · תחביבי יצירה

Answer: **תחביבי ספורט**

Explanation: 3 אנשים בחרו אוכל איטלקי. מתוכם, 2 בחרו תחביבי ספורט ו־1 בחר תחביב יצירתי.

### 20. CROSS_INTERSECTION_COUNT — movie,hobby

כמה אנשים בחרו גם סרט הרפתקאות וגם תחביב יצירתי?

Options: 3 · 0 · 2 · 1

Answer: **1**

Explanation: אדם אחד בחר גם סרט הרפתקאות וגם תחביב יצירתי: מוצאים את נמו + גיטרה.

## 4. Old assertions removed

The merged `31aefaa` fix removed both exact explanation-pair predicates and the misleading explanation-count proxy. It moved the same rich profile values into `frontend/e2e/fixtures/knowledge-room.json` and has `classroom.spec.ts` invoke a test-only, offline verifier after the game finishes. This branch contains that fix and strengthens its verifier; it does not reapply or overwrite the frontend file.

## 5. Exact assertions and protected behavior

| Assertion | What it protects |
| --- | --- |
| Exactly 20 final questions; at least 9 true semantic rounds | Substantial knowledge-derived content reaches the selected quiz, rather than merely producing candidate questions or explanations on direct questions. |
| At least 2 geographic and 2 cross-domain rounds | The rich fixture exercises additional group reasoning. |
| Semantic domains include movie, artist, song, hobby and food | Supported media and other fixture domains survive final selection. |
| Independent counts from reviewed fixture memberships match the selected answer | Correct counts, decisive ranks/comparisons, unique members, diversity and cross-domain intersections/subgroups. |
| Artist and song leaders each answer `פופ`, with their respective source field | Media-derived leaders are checked separately from the declared music preference. |
| Browser results match the finished local record and same-seed trace | The assertions verify the game actually played by host and players. |
| A second same-input/same-seed trace equals the first | Deterministic replay, including options, answers and explanations. |
| Explanations are nonempty, printable Hebrew and contain no developer/database terms | Basic player-facing explanation quality, in addition to factual checks. |
| **New:** media explanation count equals the independently counted winning group | Correct group size rather than a fixed “long enough” sentence. |
| **New:** the winning genre appears in the media explanation | An explanation stating another genre fails. |
| **New:** explanation evidence includes a supporting choice from the correct source field and winning group | A song explanation on an artist question, or unrelated plausible Hebrew, fails. Submitted or canonical wording is accepted; no specific artist/song title or pair is mandated. |

Evidence choices are derived from the consented fixture values and their reviewed winning memberships; they are not an arbitrary replacement list of strings. Media leaders already explain examples of their winning choices in the actual product. The new assertion checks that existing product behavior.

Internal rule/family/domain metadata is read only by the offline test process. No debug endpoint or public WebSocket metadata was added. Existing active-answer confidentiality, token/consent-marker exclusion, scoring and reconnect checks remain in the browser scenario.

## 6. Proof that media regressions fail

The same verifier called by Playwright now has **20 passing cases**:

- Five fixed seeds (`1`, `11`, `37`, `99`, `1024`) confirm valid fixture output and identical replay.
- Existing negative cases reject lost movie/artist/song/hobby semantics, a wrong scored answer, wrong semantic fact, empty explanations and technical explanations.
- Three new cases corrupt both the candidate and final question explanation consistently: swapped song/artist explanation, wrong genre, and unrelated plausible Hebrew. All are rejected after this change.
- Four new cases remove movie, artist, song, or all media candidates before the real production validator/scorer/final selector runs. Profiles stay unchanged. The resulting final quiz is rejected by the E2E verifier in every case.

Thus the test cannot pass merely because explanations or Hebrew text exist. These fault injections are test-only; production rules remain untouched.

## 7. Regression results

All commands below were executed in `/private/tmp/mizemi-e2e-semantic-assertion`, except the initial reproduction in the isolated older checkout. Node 26.0.0, Python 3.14.7, Chromium through Playwright 1.63.0.

| Check | Command / method | Result |
| --- | --- | --- |
| Original `knowledge-he` failure | `frontend/ npm run test:e2e -- --grep knowledge-he` on `8fbd0dd` | Reproduced: 1 failure at line 212 after all 20 rounds; 9.2s scenario |
| New explanation negative cases before fix | `pytest backend/tests/unit/test_classroom_knowledge_oracle.py -q` | 3 expected failures, 17 passed, 0.93s |
| Verifier after fix | `.venv/bin/python -m pytest backend/tests/unit/test_classroom_knowledge_oracle.py -q` | 20 passed, 0.91s |
| Relevant backend Question/Knowledge tests | `.venv/bin/python -m pytest backend/tests/unit -q -k 'knowledge or question or group_intelligence or profile_dataset'` | 731 passed, 304 deselected, 16.18s |
| Focused knowledge E2E after fix | `frontend/ npm run test:e2e -- --grep knowledge-he` | 1 passed, 13.3s |
| Complete Playwright | `frontend/ npm run test:e2e` | 3 passed, 45.0s |
| Frontend complete unit suite | `frontend/ npm test` | 350 tests in 13 files passed, 1.49s |
| Frontend type-check | `frontend/ npm run type-check` | Exit 0 |
| Frontend production build | `frontend/ npm run build` | Exit 0; 38 modules; Vite build 53ms |
| Patch whitespace | `git diff --check` | Exit 0 |
| Current-tree/report secrets | `.venv/bin/python scripts/check_secrets.py` | 0 high-confidence findings; no local real-env files |
| Full backend suite | Not rerun in this follow-up | Production engine was not changed; the requested relevant tests ran. Current main's full CI suite passed remotely. |

The final browser game used seed `12225948270585824838`, with 10 semantic, 3 direct, 4 geographic and 3 cross-domain rounds; same-seed replay passed. Full final-game evidence is saved locally in `frontend/test-results/classroom-knowledge-he-hos-d72c7-th-reconnects-and-visual-QA/knowledge-final-quiz.json` and `knowledge-public-results.json`.

The remote success cited above is for baseline main `dc2b144`, not the new test-strengthening commit. This branch was not pushed or run remotely.

## 8. Files changed

New work in this branch:

- `backend/tests/classroom_knowledge.py`: media explanations must state the winning genre/count and cite a supporting choice from the correct field.
- `backend/tests/unit/test_classroom_knowledge_oracle.py`: three explanation fault cases and four actual candidate-generation fault cases.
- `E2E_SEMANTIC_ASSERTION_REPORT.md`: reproduction, actual quiz and regression evidence.

Already merged fix retained: `frontend/e2e/classroom.spec.ts`, the shared fixture, and the original offline verifier/tests from `31aefaa`. There is no new production code, scoring, consent, knowledge asset, networking or public contract change.

## 9. Commits

- Existing obsolete-assertion replacement: `31aefaa58bb44557a67d1eaa72347e4a158e8aba` (already merged in main).
- New verified test-strengthening commit: **`b4fffe9ae9ffb06ad8ffb9c0dee6b0b7e25e3970`** — `test(e2e): require media explanations to cite supporting choices`.
- This report is committed separately afterward so the tested implementation SHA above is exact.

## 10. Git status and safety

Dedicated branch/worktree: `codex/e2e-semantic-assertion` at `/private/tmp/mizemi-e2e-semantic-assertion`. Only the three listed files are changed; exact paths are staged. After committing this report, the dedicated worktree is clean.

The original checkout remains `codex/github-pages-landing` at `8fbd0dd`, with only its pre-existing `frontend/package-lock.json` modification. Its SHA-256 remains `5ce92a07171ded0100886b0ef3ffaacc27f51eefa6f55cea9850c8fa9e82411f`. It was not restored, edited, staged or committed. That older checkout still has the obsolete assertions; the dedicated branch includes main's merged fix and the additional verification above.

No push, merge, deployment, Render/Neon change, or public wire-contract change was performed.
