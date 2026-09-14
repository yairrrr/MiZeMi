# Question Engine diagnostic — why group intelligence did not reach real games

Investigated and fixed on 2026-09-14 on branch `codex/group-intelligence` (knowledge bundle `2026-09-14.1`, 33,831 entries, unchanged).

Every number below comes from the real engines. The pre-fix numbers were produced by exporting `HEAD` (`3995e7a`) with `git archive` and running the same instrumented trace against it:

```bash
.venv/bin/python scripts/diagnose_question_engine.py --backend <exported HEAD>/backend --label before --output scripts/knowledge/diagnostic-before.json
.venv/bin/python scripts/diagnose_question_engine.py --label after --output scripts/knowledge/diagnostic-after.json
```

Full per-rule and per-room data: [diagnostic-before.json](scripts/knowledge/diagnostic-before.json), [diagnostic-after.json](scripts/knowledge/diagnostic-after.json). Diagnostic rooms live in [backend/tests/fixtures/rooms.py](backend/tests/fixtures/rooms.py): `he_rich` / `en_rich` are realistic 20-person classrooms (Hebrew titles and spellings, two skipped films, one unlisted local film, a withheld city, one "Other" music choice, a no-cuisine dish), `curated_complete` is the same shape with every answer recognized, `unknown_heavy` has only 4 of 20 films recognized, `sparse` has six players, and `audit_new_class` is the five-player room of the previous audit.

## 1. Root cause

**The semantic layer only switched on when every single player's answer was recognized.** Every production group family (`group_count`, `group_mode`, `group_unique`, `group_comparison_semantic`, `group_diversity`, `region_majority`, `region_unique`, the locality rules, `group_filtered_mode`, `group_intersection_count`, `region_hobby_diversity`) began with `SemanticView.complete(dimension)`, which requires `len(memberships) == len(players)`. One unrecognized, skipped, withheld or unclassifiable answer disabled that dimension for the whole room.

In a real classroom that condition almost never holds:

- **Unknowns are normal.** Probing realistic answers: 49/71 common film inputs, 44/55 dishes and 52/65 hobbies resolved. Film `favorite_movie` is optional, so skipped answers also break completeness.
- **Name collisions failed closed even when every contender agreed.** Remakes and homonyms had no identity: Titanic (3 films), The Lion King, Frozen, Dune, Scream — and even יוגה/Yoga, whose two reference entries carry identical facts. 655 film names and 668 song names were ambiguous; 556 and 283 of them share a classification.
- **Spelling variants were unknown.** `קרית שמונה` missed `קריית שמונה`; the town dimension died with it.
- **Recognized-but-unclassified answers counted as incomplete.** Salad, ice cream, croissant and dim sum have no cuisine; one such dish disabled every cuisine question.
- **"Other" never resolves**, so one "Other" music choice disabled every music question.

With 20 players the odds of full coverage in a dimension collapse (≈0.69²⁰ for films). The only group family that tolerated partial data was `group_scoped_count`, which lists up to six names ("מבין דנה, עומר, נועה, עמית, ליאור, יעל, כמה בחרו…") and reads like an old lookup.

The legacy fallback then dominated. `SocialLegacyRule` still produced hundreds of literal candidates, but the selector's per-rule caps limited them, so realistic rooms did not even fill the requested length: **12 of 20 questions in `he_rich`, 11 in `en_rich`, 10 of them direct.** Hebrew games also printed raw English choice values ("כמה משתתפים בחרו במוזיקה בסגנון "Pop"?").

The selector was not the primary cause: with only semantic candidates available it could still select only **2** questions in the realistic rooms, because only 2 existed that survived its caps. When data was complete (`curated_complete`), the same selector produced 10 semantic questions.

### The sixteen diagnostic questions

| # | Question | Finding |
|---:|---|---|
| 1 | Raw candidates from old/basic rules | `he_rich`: 165 direct (group_comparison 80, value_count 44, unique_value 35, category_coverage 4, filtered_mode 2). |
| 2 | Raw candidates from semantic rules | `he_rich`: 32, all `group_scoped_count`; 0 geographic, 0 cross-domain. |
| 3–4 | Semantic candidates rejected by validation, and why | **0.** The loss happened before candidates existed — inside each rule's completeness gate. |
| 5 | How many survive | All 32 valid. |
| 6 | Scores | Coverage-only scorer: scoped counts 0.28, legacy comparisons 0.18, value counts 0.07; complete-data semantic candidates scored 1.0. |
| 7–8 | Reach / selected | 32 reached the selector; 2 selected (rule cap for `group_scoped_count`). |
| 9 | Rules dominating the final quiz | `group_comparison` 3, `unique_value` 2, `value_count` 2, `filtered_mode` 2, `group_scoped_count` 2, `category_coverage` 1 — 12 questions. |
| 10 | Present but starved by ranking? | No: semantic-only selection capacity was 2 in realistic rooms and 20 in the curated room. They were absent, not outranked. |
| 11 | Field keys failing to match domains? | No. `city/favorite_food/hobby/favorite_music/favorite_movie/favorite_artist/favorite_song` all map correctly. |
| 12 | Hebrew resolution failing? | Partly: remake collisions, full/defective spellings, and dishes/hobbies without classifications (above). |
| 13 | Deployed generator using the enriched registry? | Yes: `create_app` builds `QuestionGenerator(knowledge=get_knowledge())`. |
| 14 | Semantic rules registered? | Yes, through `group_rules(knowledge)` appended to the legacy wrappers. |
| 15 | Another path using the old rule set? | Only `StartGameService()`/`QuestionGenerator()` without knowledge, used by pure-domain tests; production does not use it. |
| 16 | Reconnect/persistence reconstructing questions? | No. Questions are generated once in `StartGameService.start`, stored on the `Game`, replayed from `game.current_question`, and persisted only when finished. |

## 2. Candidate counts before the fix

`raw → final` per kind; rejections are validation rejections; "semantic-only" is how many questions the selector could pick from non-direct candidates alone.

| Room / language | Players | Final | Direct | Semantic | Geographic | Cross-domain | Rejected | Semantic-only | ms |
|---|---:|---:|---|---|---|---|---:|---:|---:|
| he_rich / he | 20 | **12** | 165 → 10 | 32 → 2 | 0 → 0 | 0 → 0 | 0 | 2 | 11.8 |
| he_rich / en | 20 | **12** | 165 → 10 | 32 → 2 | 0 → 0 | 0 → 0 | 0 | 2 | 10.4 |
| en_rich / en | 20 | **11** | 145 → 9 | 32 → 2 | 0 → 0 | 0 → 0 | 0 | 2 | 8.3 |
| en_rich / he | 20 | **11** | 145 → 9 | 32 → 2 | 0 → 0 | 0 → 0 | 0 | 2 | 8.7 |
| curated_complete / he | 20 | 20 | 240 → 6 | 123 → 10 | 6 → 3 | 64 → 1 | 0 | 20 | 26.8 |
| curated_complete / en | 20 | 20 | 240 → 6 | 123 → 10 | 6 → 3 | 64 → 1 | 0 | 20 | 25.5 |
| unknown_heavy / he | 20 | 20 | 157 → 10 | 21 → 4 | 7 → 6 | 0 → 0 | 0 | 11 | 10.7 |
| unknown_heavy / en | 20 | 20 | 157 → 10 | 21 → 4 | 7 → 6 | 0 → 0 | 0 | 11 | 10.4 |
| sparse / he | 6 | 20 | 50 → 4 | 33 → 12 | 5 → 3 | 1 → 1 | 0 | 16 | 4.7 |
| sparse / en | 6 | 20 | 50 → 4 | 33 → 12 | 5 → 3 | 1 → 1 | 0 | 16 | 4.5 |
| audit_new_class / he | 5 | 20 | 48 → 2 | 92 → 13 | 5 → 3 | 7 → 2 | 0 | 20 | 7.9 |
| audit_new_class / en | 5 | 20 | 48 → 2 | 92 → 13 | 5 → 3 | 7 → 2 | 0 | 20 | 7.0 |

The previous audit looked healthy because its rooms had five to eight hand-picked players — exactly the case where the completeness gate passes.

## 3. Candidate counts after the fix

| Room / language | Players | Final | Direct | Semantic | Geographic | Cross-domain | Rejected | Semantic-only | ms |
|---|---:|---:|---|---|---|---|---:|---:|---:|
| he_rich / he | 20 | 20 | 106 → 5 | 72 → 9 | 13 → 4 | 57 → 2 | 0 | 20 | 14.4 |
| he_rich / en | 20 | 20 | 106 → 5 | 72 → 9 | 13 → 4 | 57 → 2 | 0 | 20 | 14.1 |
| en_rich / en | 20 | 20 | 112 → 5 | 67 → 9 | 14 → 3 | 56 → 3 | 0 | 20 | 13.2 |
| en_rich / he | 20 | 20 | 112 → 5 | 67 → 9 | 14 → 3 | 56 → 3 | 0 | 20 | 13.4 |
| curated_complete / he | 20 | 20 | 162 → 5 | 73 → 9 | 14 → 3 | 65 → 3 | 0 | 20 | 15.2 |
| curated_complete / en | 20 | 20 | 162 → 5 | 73 → 9 | 14 → 3 | 65 → 3 | 0 | 20 | 15.5 |
| unknown_heavy / he | 20 | 20 | 104 → 10 | 0 → 0 | 13 → 7 | 3 → 3 | 0 | 10 | 9.8 |
| unknown_heavy / en | 20 | 20 | 104 → 10 | 0 → 0 | 13 → 7 | 3 → 3 | 0 | 10 | 9.7 |
| sparse / he | 6 | 20 | 27 → 5 | 14 → 6 | 15 → 7 | 4 → 2 | 0 | 16 | 3.4 |
| sparse / en | 6 | 20 | 27 → 5 | 14 → 6 | 15 → 7 | 4 → 2 | 0 | 16 | 3.3 |
| audit_new_class / he | 5 | 20 | 33 → 4 | 30 → 9 | 12 → 4 | 7 → 3 | 0 | 20 | 4.3 |
| audit_new_class / en | 5 | 20 | 33 → 4 | 30 → 9 | 12 → 4 | 7 → 3 | 0 | 20 | 4.2 |

Direct raw candidates still outnumber semantic ones in every realistic room, and the final quiz is nevertheless led by discoveries. The unknown-heavy room correctly gets **no** taste discoveries: its films and dishes are unrecognized and its only recognized taste data is fixed music choices, which are classified as direct. Geography and region subgroups fill the gap.

## 4. Validation rejections

Zero in every room, before and after. Rejections were never the problem. `QuestionValidator.rejection_reason` now names the failing check, and `QuestionGenerator.trace` records every rejected candidate with its reason, so a future regression is visible in the diagnostic.

During development the trace caught one real defect: an English comparison template said "calm hobbies" while its option read "Hobbies without physical effort", so the answer was named without its alternative and the candidate was rejected (`answer_named_in_question`). The template was corrected. The validator now accepts an either/or question that names every option ("horror or science fiction?") and still rejects a question naming only its answer.

## 5. Selector behavior

**Before.** One greedy loop mixed a 30/35/20/15 "mix deficit", rule caps, difficulty targets and a coverage-only score. It could not create what the gates had removed, and its per-rule caps are why realistic games ended at 11–12 questions.

**After** (`QuestionSelector(group_first=True)`, [selector.py](backend/app/domain/questions/selector.py)):

1. **One entry per fact.** Candidates collapse by language-independent fact key before planning, so a rule that emits 80 comparisons competes as a handful of facts, not 80 lottery tickets.
2. **Supply-limited quotas.** Preferred shares are 45% semantic, 25% direct, 15% geographic and 15% cross-domain, capped by the number of distinct facts each kind actually supports. Unused share flows to kinds with more supply. No kind is padded with weak questions.
3. **Caps.** Per game of N questions: a family at most ⌈N/5⌉ times; a domain at most ⌈N/4⌉ (a cross-domain question counts for both domains); one question per domain/family pair per 12 questions; supporting families (diversity, minority, distribution, region counts/unique/outlier) once per 20; person answers ⌊N/4⌋; literal lookups two per rule; age once. Membership signatures stop the same people being asked about twice ("only one chose X" / "how many chose X?" = 1 / "which is most popular" + its winner's count).
4. **Ranking inside a kind.** Least-used family (supporting families count as already used once), then domain, then domain/family, then no back-to-back domain, then difficulty spread, then information value, then participant spread, then the fact key.
5. **No question answered by an earlier one.** Counts, rankings, subgroup facts and the raw-answer counts, majorities and comparisons declare what they disclose (`reveals`: a category's count, that it has one member, or that it outranks the rest — within a dimension, a subgroup scope or a raw answer field) and what would already settle them (`needs`). Games are shown easy to hard, so the check is order-aware: "which hobby type is most common?" (easy) rules out a later "sport or reading?" (medium) and a runner-up "of these, which is most common?"; an easy count may still precede a medium comparison that only repeats that count afterwards. When two facts conflict, the one that settles the other is preferred if it reasons at least as deeply, so a majority beats the comparison it implies but a plain count never pushes out a majority. Mirror subgroup facts ("among pop fans, which hobby?" / "among sport fans, which music?" / "how many chose both?") share one membership signature. A settled question is never admitted: if the requested length cannot be reached without one, the game is shorter. A second pass without the preference runs only when the first comes up short, and the longer of the two unsettled selections is kept.
6. **Fill order.** Kinds under quota within caps; any kind within caps; only then relaxed family/domain caps, choosing the most varied remaining fact. Games reach the configured length whenever enough unsettled facts exist; otherwise they end early — `total_questions` is the actual count and the host sees “Only N of M questions could be made from the shared profiles.”
7. **Presentation.** EASY → MEDIUM → HARD, avoiding consecutive questions from one domain.

**Answer leaks, measured.** `answered_by_earlier_questions` in the test suite replays each final game in presentation order and, from the facts and the room's counts alone (independently of the selector's bookkeeping), lists every question an earlier question or its explanation settles. With the check disabled the same engine leaks in 12 of the 12 fixture games (38 questions — for example "באיזה אזור בארץ גרים הכי הרבה מכם?" followed by "מאיפה מגיעים יותר מכם — מהמרכז או מהדרום?"); with it, 0. Over 300 randomized rooms of 5–30 players built from the fixture answers: 290 rooms with the check disabled (754 settled questions) → **0 of 300** with it. Quality comes before length: 293 games have the requested 20 questions and 7 are shorter — five 5-player rooms (15, 18, 18, 19, 19 questions), a 7-player room (13) and a 16-player room with only 20 valid candidates (14). Every short game's `total_questions` and indices match its actual length. An earlier revision filled those seven games to 20 by admitting 19 settled questions; that fallback is removed. The fixture rooms were never affected: all 12 fixture rooms in both languages (24 games) still have 20 questions, and the audit and diagnostic final questions are identical. Only the capacity from non-direct facts alone in `unknown_heavy` (10) and `sparse` (16) is lower, because it no longer counts settled facts.

**Information value** ([scorer.py](backend/app/domain/questions/scorer.py) `DiscoveryValueScorer`, deterministic, 0–1): 0.40 × reasoning depth (a direct lookup is one hop; resolve + classify is two; + aggregate/compare is three; inside a subgroup of another domain is four) + 0.30 × share of the group involved + 0.20 × how informative the result is (a count that splits the group, a close but decided race, a leader with a real share — weighted by how clearly the members' choices sit in the category, so two horror films filed as horror/crime outrank two animated films filed under four genres) + 0.10 × recognition coverage. In `he_rich`, the best majority scores 0.85 and the best literal lookup 0.36; no giant bonus is used — the quotas and caps do the balancing.

## 6. Rule/family distribution in final games

Realistic `he_rich` game — before: `group_comparison` 3, `group_scoped_count` 2, `unique_value` 2, `value_count` 2, `filtered_mode` 2, `category_coverage` 1 (12 questions). After, per family:

| Family | Raw facts | Selected |
|---|---:|---:|
| SEMANTIC_COUNT | 37 | 3 |
| SEMANTIC_COMPARISON | 18 | 2 |
| SEMANTIC_MAJORITY | 2 | 1 |
| SEMANTIC_UNIQUE | 11 | 2 |
| SEMANTIC_DIVERSITY | 1 | 1 |
| SEMANTIC_DISTRIBUTION / SEMANTIC_MINORITY | 2 / 1 | 0 / 0 |
| GEO_REGION_MAJORITY / GEO_EXTREME / GEO_REGION_COMPARISON / GEO_REGION_DIVERSITY / GEO_OUTLIER / GEO_REGION_COUNT | 1 / 2 / 4 / 1 / 1 / 4 | 1 / 1 / 1 / 1 / 0 / 0 |
| CROSS_SUBGROUP_MAJORITY / CROSS_INTERSECTION_COUNT / CROSS_SUBGROUP_COMPARISON | 16 / 24 / 17 | 1 / 1 / 0 |
| DIRECT_UNIQUE / DIRECT_COUNT / DIRECT_COMPARISON / DIRECT_CHOICE | 32 / 4 / 64 / 6 | 2 / 1 / 1 / 1 |

The runner-up distribution ("of these hobby types, which is most common?") is no longer selected here: the hobby majority's explanation already names that runner-up.

Across all twelve diagnostic games (240 questions): semantic 84, direct 68, geographic 56, cross-domain 32 — versus semantic 86, direct 82, geographic 30, cross-domain 8 before, where the "semantic" total came almost entirely from the small and curated rooms.

## 7. Domain distribution

`he_rich`, both languages: food 5, hobbies 5, music 5, places 5, films 2; `en_rich`: food 5, hobbies 5, places 5, films 4, music 4 (a cross-domain question counts for both of its domains). Films are limited by the data, not the selector: two of 17 film answers are unrecognized, so a film majority or a narrow film comparison could be overturned and is correctly withheld (§8). Totals across all diagnostic games: places 82, hobbies 62, music 56, food 44, films 26, age 2.

## 8. Semantic coverage behavior

The category-first stage ([group_summary.py](backend/app/domain/questions/group_summary.py)) accounts for every shared answer per dimension as **classified**, **neutral** (recognized but in none of the compared categories: a hobby done anywhere, the "Other" music choice) or **unknown**. Withheld answers do not exist there at all. Policy (`CoveragePolicy`):

| Claim | Requirement |
|---|---|
| Any group question about a dimension | ≥ 3 shared and recognized answers |
| Count ("how many chose a horror movie?") | coverage ≥ 75%; the explanation states the recognition rate when below 100% ("זוהו 15 מתוך 17 סרטים"); wrong options skip counts unknowns could make true |
| Comparison ("horror or science fiction?") | coverage ≥ 70%; the lead must exceed the number of unknown answers; the smaller side needs two people once eight or more answered; ties rejected |
| Majority / "most popular in the group" / minority / distribution | coverage ≥ 80%, ≥ 5 recognized, ≥ half the room shared the answer, leader holds ≥ 20% of recognized answers, lead > unknown answers |
| Naming a runner-up ("במקום השני: …") | only when it leads third place by more than the unknown answers; a tied second is not named (it was in 6 of 26 such explanations before this rule) |
| Comparison of two categories | not asked when one side has more than three times the other ("11 or 2?" answers itself) |
| "Most of the group" (רוב) | more than half of the visible room — room size is public, no withheld value is read |
| Exclusive claims ("only one person…", "how many different…", "who lives furthest north") | every shared answer recognized; coordinate questions also need every town uniquely identified |
| Cross-domain subgroup | proper subgroup of ≥ max(3, 20% of the room); target dimension ≥ 80% recognized inside it; decisive lead |

Examples from the diagnostic rooms: `he_rich` films are 15/17 recognized (88%) — counts and decisive comparisons are allowed, but the adventure (7) vs comedy (6) majority is withheld because the two unknown films could change it. `unknown_heavy` films are 4/20 recognized — no film claim of any kind is generated. The horror-majority test with 18/20 recognized films and 10 horror picks is allowed and explains "18 of the 20 movies chosen were recognized".

Recognition itself improved without adding data: names shared by several reference entities now expose the categories **every** contender shares (every Titanic is a drama; both Yoga entries are sport), identity stays unknown, and a Hebrew doubled-vav/yod fold (`קרית`/`קריית`, `תקוה`/`תקווה`) is used only after the exact name misses, failing closed on collisions. Categories are compared at one level per dimension: broad hobby families (running's "fitness" label folds into sport), cuisine families (Japanese, Chinese, Thai, Korean and Indian dishes are Asian food; the reference tag that also files hummus as "Asian" is not used), music families (trance is electronic).

## 9. Old versus new final quiz — the same realistic Hebrew room

Twenty participants ([`HE_RICH`](backend/tests/fixtures/rooms.py)): sports, creative, digital, reading, cooking and outdoor/indoor hobbies; Italian, Asian, Middle Eastern, American, Mexican and North African dishes plus schnitzel, salad and ice cream; towns in the north, center, south and Jerusalem area (one withheld, one written קרית שמונה); pop, Israeli pop, Mizrahi, rock, hip-hop, electronic, trance and "Other"; seventeen films, two of them unlisted or ambiguous.

**Before — 12 questions (seed 1000):**

| # | Difficulty | rule_id | Kind | Question |
|---:|---|---|---|---|
| 1 | EASY | `group_comparison` | direct | איזה משני סגנונות המוזיקה האלה נפוץ יותר בקבוצה? |
| 2 | EASY | `group_comparison` | direct | איזה משני המאכלים האלה נבחר יותר בקבוצה? |
| 3 | EASY | `group_comparison` | direct | איזה משני התחביבים האלה נפוץ יותר בקבוצה? |
| 4 | EASY | `group_scoped_count` | semantic | מבין דנה, עומר, נועה, עמית, ליאור, יעל, כמה בחרו סרטים בז׳אנר אימה? |
| 5 | EASY | `unique_value` | direct | מי היחיד/ה שבחר/ה "קוסקוס" כאוכל אהוב? |
| 6 | EASY | `value_count` | direct | כמה משתתפים בחרו "כדורגל" כתחביב? |
| 7 | EASY | `group_scoped_count` | semantic | מבין עומר, עמית, מאיה, כמה בחרו אמנים שמזוהים עם היפ הופ? |
| 8 | EASY | `unique_value` | direct | מי היחיד/ה שבחר/ה "ראמן" כאוכל אהוב? |
| 9 | EASY | `value_count` | direct | כמה משתתפים בחרו במוזיקה בסגנון "Pop"? |
| 10 | HARD | `category_coverage` | direct | אצל בעלי איזה תחביב יש בקבוצה את המגוון הכי רחב של סגנונות מוזיקה? |
| 11 | HARD | `filtered_mode` | direct | מבין המשתתפים שבחרו "Pop" לגבי סגנון מוזיקה, מה הכי נפוץ אצלם לגבי תחביב? |
| 12 | HARD | `filtered_mode` | direct | מבין המשתתפים שבחרו "Mizrahi" לגבי סגנון מוזיקה, מה הכי נפוץ אצלם לגבי אוכל אהוב? |

**After — the representative 20-question game (seed 1000):**

| # | Difficulty | rule_id | Family | Domain | Kind | Question | Answer |
|---:|---|---|---|---|---|---|---|
| 1 | EASY | `group_mode` | SEMANTIC_MAJORITY | hobby | semantic | איזה סוג תחביב יש להכי הרבה אנשים כאן? | ספורט |
| 2 | EASY | `group_count` | SEMANTIC_COUNT | food | semantic | כמה מהמאכלים שבחרתם הם מהמטבח האיטלקי? | 6 |
| 3 | EASY | `group_count` | SEMANTIC_COUNT | hobby | semantic | לכמה מכם יש תחביב שעושים בחוץ? | 4 |
| 4 | EASY | `group_count` | DIRECT_CHOICE | music | direct | כמה מכם בחרו מוזיקת רוק כסגנון האהוב? | 3 |
| 5 | EASY | `unique_value` | DIRECT_UNIQUE | hobby | direct | מי היחיד/ה שהתחביב שלו/ה הוא "קריאה"? | תמר |
| 6 | EASY | `group_comparison` | DIRECT_COMPARISON | food | direct | איזה משני המאכלים האלה נבחר יותר בקבוצה? | פיצה |
| 7 | EASY | `region_majority` | GEO_REGION_MAJORITY | place | geographic | באיזה אזור בארץ גרים הכי הרבה מכם? | המרכז |
| 8 | EASY | `value_count` | DIRECT_COUNT | food | direct | כמה משתתפים בחרו "סושי" כאוכל האהוב עליהם? | 2 |
| 9 | EASY | `group_count` | SEMANTIC_COUNT | movie | semantic | כמה סרטי הרפתקאות יש בין הסרטים שבחרתם? | 7 |
| 10 | EASY | `unique_value` | DIRECT_UNIQUE | food | direct | מי היחיד/ה שבחר/ה "שקשוקה" כאוכל אהוב? | דניאל |
| 11 | EASY | `locality_extreme` | GEO_EXTREME | place | geographic | מי מכם גר/ה ביישוב הכי דרומי? | יונתן |
| 12 | MEDIUM | `group_comparison_semantic` | SEMANTIC_COMPARISON | movie | semantic | אם מסתכלים על בחירות הסרטים, איזה צד מנצח — הרפתקאות או פשע? | הרפתקאות |
| 13 | MEDIUM | `group_unique` | SEMANTIC_UNIQUE | music | semantic | רק אדם אחד בחר אמן שמזוהה עם מוזיקת רוק. מי זה? | מאיה |
| 14 | MEDIUM | `group_comparison_semantic` | SEMANTIC_COMPARISON | food | semantic | לפי המאכלים שבחרתם, מה מוביל — אוכל איטלקי או אמריקאי? | איטלקי |
| 15 | MEDIUM | `group_diversity` | SEMANTIC_DIVERSITY | music | semantic | כמה סגנונות מוזיקה שונים מיוצגים כאן? | 5 |
| 16 | MEDIUM | `region_comparison` | GEO_REGION_COMPARISON | place | geographic | מאיפה מגיעים יותר מכם — מהצפון או מאזור ירושלים? | הצפון |
| 17 | MEDIUM | `group_unique` | SEMANTIC_UNIQUE | hobby | semantic | רק אדם אחד בקבוצה בחר תחביב של הרפיה. מי זה? | נדב |
| 18 | MEDIUM | `region_diversity` | GEO_REGION_DIVERSITY | place | geographic | מכמה אזורים בארץ מגיעים חברי הקבוצה? | 4 |
| 19 | HARD | `group_filtered_mode` | CROSS_SUBGROUP_MAJORITY | place + music | cross_domain | מבין מי שגרים במרכז, איזה סגנון מוזיקה הכי נפוץ? | פופ |
| 20 | HARD | `group_intersection_count` | CROSS_INTERSECTION_COUNT | music + hobby | cross_domain | כמה אנשים בחרו גם מוזיקה אלקטרונית וגם תחביב ספורטיבי? | 2 |

9 semantic, 4 geographic, 2 cross-domain, 5 direct. Nobody typed "sport", "Italian", "adventure", "the center" or "pop" as a category. Explanations appear after each question, for example: "11 אנשים בחרו תחביבי ספורט — יותר מכל סוג תחביב אחר. במקום השני: אמנות ויצירה (3)." and "6 אנשים בחרו אוכל איטלקי: פיצה, פסטה, לזניה ועוד 2. זוהו 17 מתוך 20 מאכלים." Question 7's explanation reads "9 אנשים גרים במרכז — יותר מכל אזור אחר." without a runner-up, because the north and the south tie at 4; an earlier revision of this game named "הצפון (4)" and then asked "center or south?", both now prevented.

The same seed in English asks the same facts with the same answers ("Which type of hobby do the most people here have?" → Sport); `test_scenario_12` proves this for all ten audit rooms.

## 10. Files changed

Engine (backend):
- `backend/app/domain/questions/group_summary.py` — **new** category-first stage: semantic dimensions, comparable levels, answer accounting and `CoveragePolicy`.
- `backend/app/domain/questions/discovery_rules.py` — **new** 18 production families (7 semantic, 8 geographic, 3 cross-domain) and the production registry.
- `backend/app/domain/questions/discovery_language.py` — **new** bilingual lexicon, wording variants and explanation nouns.
- `backend/app/domain/questions/knowledge.py` — consensus classification (`classify`), Hebrew spelling fold, single-pass indexes.
- `backend/app/domain/questions/selector.py` — group-first planner with the order-aware disclosure check (legacy mode unchanged).
- `backend/app/domain/questions/scorer.py` — `DiscoveryValueScorer` (the coverage scorer is unchanged).
- `backend/app/domain/questions/validator.py` — `rejection_reason`, either/or option naming.
- `backend/app/domain/questions/generator.py` — production wiring and `trace()`.
- `backend/app/domain/questions/group_rules.py` — the direct-question wrapper: selection metadata including what raw counts, majorities and comparisons disclose, no raw music choices, no count-of-one lookups, natural personal-fact wording. The previous group families remain as a tested catalog.

Tests and fixtures:
- `backend/tests/integration/test_game_configuration.py` — the configured-game test follows the actual total; a new test plays a three-player 20-question request that yields 17 questions through FINISHED, with the actual total in `game.started`, every `question.started`, host and player reconnect snapshots, the finished snapshot and persistence.
- `frontend/src/features/host/HostGame.test.tsx` — a shorter game shows “Question 2 of 2”, the “Only 2 of 20” notice, “After question 2 of 2” and “Show final results”; `frontend/e2e/classroom.spec.ts` reads the actual total from `game.started` and requires the full 20 in the knowledge room.
- `backend/tests/unit/test_category_first_questions.py` — **new**, 67 tests covering all twelve required scenarios plus overlap, granularity, literal music, consensus classification, validator, quotas, scoring, determinism, trivia, performance, runner-up ties, lopsided races, singular verbs, an independent replay proving no final question in twelve rooms is answered by an earlier one, and a limited pool that returns fewer questions instead of a settled one.
- `backend/tests/fixtures/rooms.py` — **new** realistic rooms shared by tests, diagnostics, audit and benchmark.

Scripts, data and documents:
- `scripts/diagnose_question_engine.py` — **new** stage-by-stage trace; `scripts/knowledge/diagnostic-before.json`, `diagnostic-after.json` — **new** evidence.
- `scripts/audit_group_questions.py` (ten audit rooms), `scripts/knowledge/group-games.json` (regenerated), `scripts/benchmark_knowledge.py` (no longer depends on the old audit constants; adds a realistic-room timing), `scripts/knowledge/benchmark-results.json`, `scripts/knowledge/demo-results.json` (regenerated).
- `QUESTION_ENGINE_DIAGNOSTIC.md` (this file), `QUESTION_STYLE_AUDIT.md`, `MASTER_SPEC.md` §12.3, `README.md`, `KNOWLEDGE_BASE_REPORT.md` (superseded-catalog note).

No frontend source, WebSocket contract, schema, persistence, scoring, deployment, Render or Neon file changed; shorter games use the existing variable-length support. The knowledge bundle is byte-identical.

## Performance

Measured with `.venv/bin/python scripts/benchmark_knowledge.py` on the same machine as the committed pre-fix results:

| Metric | Before | After | Target |
|---|---:|---:|---:|
| Knowledge assets | 5.91 MB | 5.91 MB | free-tier budget |
| Knowledge load (median, uninstrumented) | 591 ms | 583 ms | ≤ 2 s |
| Retained knowledge memory | 39.5 MB | 40.8 MB | < 80 MB |
| Peak knowledge memory | 49.8 MB | 51.4 MB | — |
| Cold `app.main` import | 808 ms | 779 ms | — |
| 30 players / 20 questions (median of 20) | 16.9 ms | 12.2 ms (max 18.1) | ≤ 500 ms |
| Realistic 20-player room / 20 questions (median of 20) | — | 13.2 ms (max 14.5) | ≤ 500 ms |
| 25 rooms × 30 players × 20 questions | 424 ms | 306 ms | — |

The 25-room figure is one sequential run; repeating that loop seven times gives a median of 318 ms (312–321 ms). The disclosure check and its occasional second selection pass cost about 2 ms per game over the revision without them (270 ms for the same 25 rooms).

## Remaining limitations

- Recognition is bounded by the existing bundle: very common dishes (schnitzel, steak, curry), several hobbies (dancing, cycling as "אופניים", singing) and many Hebrew film titles are still unknown. They stay usable in literal questions and correctly suppress group claims; no data was added in this revision.
- Reference classifications are multi-label and occasionally surprising (animated comedies are also adventures; "Blank Space" is filed as electronic). Questions count what the reference data states and explanations list the works counted.
- Claims about "the group" are made over the answers that were shared; withheld answers are treated as absent by design, and "most of the group" is only said of more than half of everyone in the room.
- Rooms with little recognized data (the sparse and unknown-heavy audit rooms) still produce complete games, but with more literal and geographic questions, counts of one and some repeated families. The hobby-heavy audit room reaches 6 semantic questions (30%), below the rich-room target, because its hobby discoveries share one domain cap.
- Rooms without enough unsettled facts get shorter games instead of repeated answers: 7 of 300 randomized rooms (13–19 questions), all with 5–7 players or about 20 valid candidates. The check covers counts, rankings, subgroups and raw-answer counts/majorities/comparisons; inferences that need several earlier questions combined (e.g. adding up four counts) are not modeled.
