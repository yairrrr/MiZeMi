# Question variety — design

Written before implementation, on branch `codex/knowledge-resolution`. It records what the engine
does today, why the games feel repetitive, thirty candidate question families, and which of them are
worth building. Numbers come from 20 generated games (400 questions) over the twenty synthetic rooms
in [backend/tests/fixtures/variety_rooms.py](backend/tests/fixtures/variety_rooms.py).

## 1. Measured behaviour before the change

| Domain | Questions (of 400) | | Profile field | Questions |
|---|---:|---|---|---:|
| place (city) | 85 (21%) | | `city` | 85 |
| hobby | 84 (21%) | | `hobby` | 84 |
| movie | 82 (20%) | | `favorite_movie` | 82 |
| music + artist + song | **143 (36%)** | | `favorite_music` | 60 |
| food | 59 (15%) | | `favorite_artist` | 55 |
| age | 11 (3%) | | `favorite_song` | 28 |
| personal fact | **0** | | `age` | 11 |
| | | | `personal_fact` | **0** |

Reasoning operations: count 107, majority 100, comparison 82 — **72% of every game is one of three
patterns**. Diversity 21, unique 31, extreme 22, outlier 8, distribution 5, minority 1.

Per game: 11–16 families, but only 5–9 distinct reasoning operations; 2–11 repeated
operation/domain styles; direct lookups 15–30% (`quiet_optional_he`: 5 of 20).

A real example (`quiet_optional_he`) shows all three problems at once:

| # | Question | Problem |
|---|---|---|
| 13 | רק אדם אחד בקבוצה בחר מוזיקה קלאסית. מי זה? | near-duplicate of 14 |
| 14 | רק אדם אחד בקבוצה בחר מוזיקת רוק. מי זה? | same family, same dimension |
| 16 | כמה אנשים בחרו גם סרט הרפתקאות וגם תחביב ספורטיבי? | same anchor as 17 |
| 17 | כמה אנשים בחרו גם סרט הרפתקאות וגם מאכל איטלקי? | same operation, same anchor |
| 5, 11, 15, 17, 18, 19 | six questions whose answer is "Italian food" or built on it | one fact, six questions |

## 2. Root causes

1. **One domain is counted as three.** `selection_domain` splits `movie`/`artist`/`song`, and
   `music.genre` is a fourth. Each gets its own 25% domain cap, so "what music do you like" can take
   up to a third of a game. A recent media-coverage rule *forces* a genre discovery from each media
   field, which pushes artist and song questions in even when the group barely filled those fields.
2. **Reasoning pattern is not a balanced quantity.** The selector balances *family* and *domain*.
   `SEMANTIC_MAJORITY`, `GEO_REGION_MAJORITY`, `DIRECT_MAJORITY` and `CROSS_SUBGROUP_MAJORITY` are
   four different families that all ask "which is most common?", so a game can hold five majorities
   without violating any cap.
3. **Duplicate detection is per fact, not per idea.** Dedupe keys are the fact key, normalized text
   and membership signatures. "Only one chose classical music" and "only one chose rock" are
   different facts, so both pass. Nothing knows they are the same *question*.
4. **Direct lookups have a reserved 25% share** of every game.
5. **Two profile fields have no path into a question.** `age` reaches only "who is oldest"
   (`DIRECT_AGE`). `personal_fact` is filtered to the legacy `unique_value` rule, which then drops it
   because a guard requires *every* player to have answered the field — an optional free-text field
   never satisfies that, so the best bonding question in the product never appears.
6. **Unused knowledge.** The bundle carries `food.format` (14 categories: soups, desserts,
   sandwiches, pastries…), `hobby.music` (making music), song→performer links and film series ids.
   None are used.

## 3. Thirty candidate families

Value = group-bonding value. Ambiguity = risk of an unclear or contestable answer.

| # | Idea | Fields | Derivation | Value | Ambiguity | Verdict |
|---:|---|---|---|---|---|---|
| 1 | **Who wrote this about themselves?** quoting a consented fact | personal_fact | attribute the exact consented text to its writer | very high | none | **IMPLEMENT** |
| 2 | **Taste twins** — which two share the most categories | all semantic | max pairwise shared categories, unique winner, ≥2 shared | very high | low | **IMPLEMENT** |
| 3 | **Most typical member** — whose answers match the group's leaders most | all semantic | count majority-category memberships per player, unique max | high | low | **IMPLEMENT** |
| 4 | **The one thing you all share** (unanimity) | any dimension | a category holding every recognized answer, full coverage | very high | none | **IMPLEMENT** |
| 5 | **Everyone except one** | any dimension | exactly one recognized answer outside a category | high | none | **IMPLEMENT** |
| 6 | **Where are you most alike / most different** | ≥3 dimensions | compare top-category share across dimensions, margin ≥ 0.15 | high | medium | **IMPLEMENT** |
| 7 | **Hidden shared category** — "X wrote pasta, who else picked that cuisine?" | any dimension | exactly one other member, different raw answers | high | none | **IMPLEMENT** |
| 8 | **Who is both** — one person in a two-category intersection | 2 domains | intersection of size 1, each side ≥2 | high | none | **IMPLEMENT** |
| 9 | **Your song, their artist** | artist+song | song.performer_id == another player's artist id | very high | none | **IMPLEMENT** |
| 10 | **Same film series** | movie | two players, same series id, different films | high | none | **IMPLEMENT** |
| 11 | **Age spread** — years between youngest and oldest | age | max−min over shared ages | medium-high | none | **IMPLEMENT** |
| 12 | **Age bands** — count/majority over 13–15, 16–18, 19–24, 25–34, 35–49, 50+ | age | fixed bands, no exact age revealed | medium-high | low | **IMPLEMENT** |
| 13 | **Age-band subgroup taste** — "among the 16–18s, which music leads?" | age + any | subgroup by band, decisive leader | medium-high | low | **IMPLEMENT** |
| 14 | **Food format** — desserts, soups, sandwiches, pastries | favorite_food | unused `food.format` facet | high | low | **IMPLEMENT** (dimension) |
| 15 | **Who plays music** | hobby | unused `hobby.music` family | medium-high | low | **IMPLEMENT** (dimension) |
| 16 | Group splits evenly between two categories | any | two categories within 1 of each other | medium | medium | MAYBE |
| 17 | Which category nobody chose | any | absent category among prominent ones | low-medium | high (arbitrary absence) | REJECT |
| 18 | Most unusual member (least like the group) | all | inverse of #3 | medium | low | MAYBE — risks singling someone out negatively |
| 19 | How many wrote an answer nobody else shares | any | count of singleton answers | low | low | REJECT — statistics homework |
| 20 | Two closest in age | age | min age gap, unique pair | medium | high (ties in a class) | MAYBE |
| 21 | Which decade are your films from | movie | entity year | low | — | REJECT — general-knowledge trivia |
| 22 | Which country do your dishes come from | food | entity country | low | medium | REJECT — near-duplicate of cuisine |
| 23 | District instead of region | city | `place.district` | low | low | REJECT — more city questions, the opposite of the goal |
| 24 | Correlation: does hobby X predict music Y | 2 domains | contingency comparison | low | high | REJECT — statistics, unsupported inference |
| 25 | Who changed the group's majority (swing member) | any | leave-one-out majority flip | medium | high | REJECT — needs explaining the algorithm |
| 26 | Longest chain of shared categories | all | graph path | low | high | REJECT — cannot be understood in 20 seconds |
| 27 | Which two categories never co-occur | 2 domains | empty intersection | low | high | REJECT |
| 28 | Rarest category still chosen by someone | any | min non-zero category | medium | low | MAYBE — overlaps existing minority |
| 29 | How many of you share a hometown with someone | city | duplicate-city count | medium | low | MAYBE — another city question |
| 30 | Same answer twins — two identical raw answers | any | duplicate raw value | medium | medium | MAYBE — often several pairs |

**Implementing 15 of 30**: ideas 1–15. The MAYBEs are recorded for later; the REJECTs are recorded
with their reason so they are not proposed again.

## 4. Why the rejected ideas are rejected

- **Trivia** (21, 22): the answer lives in the reference data, not in the group. The product rule is
  that only participants' own choices decide an answer.
- **Statistics homework** (19, 24, 26, 27): correct, deterministic and boring; a player cannot
  answer in 20 seconds without being shown a table.
- **Needs the algorithm explained** (25): if the question has to describe its own derivation, it is
  not a game question.
- **Arbitrary** (17): infinitely many categories are absent; picking four of them is a lottery.
- **More of what already dominates** (23, 29): city questions are the problem, not the fix.
- **Risk to a person** (18): "who is least like everyone" can land badly in a classroom.

## 5. Semantic signature

Every candidate carries a signature describing what it *asks*, independent of wording:

```
signature = (operation, topic, categories, subgroup, answer_type)
```

- `operation` — the reasoning pattern: COUNT, MAJORITY, COMPARISON, UNIQUE, DIVERSITY, MINORITY,
  DISTRIBUTION, EXTREME, PAIR, OUTLIER, UNANIMITY, EXCEPTION, TWINS, TYPICAL, CONCENTRATION,
  ATTRIBUTION, LINK, INTERSECTION, SPREAD, BAND.
- `topic` — the semantic dimension (`movie.genre`, `food.format`, `age.band`…), a raw field for
  literal questions, or `multi` for whole-profile reasoning.
- `categories` — the category ids the question is about.
- `subgroup` — the filter for cross-domain questions.
- `answer_type` — person / pair / number / category.

Three levels of sameness are then computable:

| Level | Test | Policy |
|---|---|---|
| identical | same signature | never twice |
| near-duplicate | same `(operation, topic)` | never twice |
| same style | same `(operation, domain group)` | at most once in pass 1; allowed in pass 2 only in a different domain group |

## 6. Domain groups

`music.genre`, `artist.genre` and `song.genre` become one **music** group — a player experiences
them as one subject. Groups: `film`, `music`, `food`, `hobby`, `place`, `age`, `personal`. A
cross-domain question belongs to both of its groups. Cap: no group above 30% of a game.

## 7. Selection passes

1. **Pass 1** — every reasoning operation at most once, every domain group under its cap, no
   near-duplicates. Ordering prefers an unused operation, then an unused domain group, then an
   unused profile field, then information value.
2. **Pass 2** — an operation may repeat only in a different domain group and a different dimension.
3. **Pass 3** — relax the operation rule (never the duplicate or disclosure rules) rather than end
   a game far short.

Quality still beats length: a settled or duplicated question is never admitted to reach 20.

## 8. Direct lookups

The reserved direct share drops from 25% to 10%, and literal identity lookups stay a last resort.

## 9. What must not regress

Consent filtering, ambiguity and tie rejection, coverage policy, answer-leak prevention,
determinism, bilingual equivalence, variable-length games, scoring, reconnect, persistence. No
runtime AI, no network, no new dependency.

## 10. Implementation status

All fifteen IMPLEMENT ideas shipped. Results are in
[QUESTION_VARIETY_REPORT.md](QUESTION_VARIETY_REPORT.md).

| Idea | Family / dimension | Status in the twenty-room sample |
|---|---|---|
| 1 Who wrote this about themselves | `SOCIAL_ATTRIBUTION` | 16 questions |
| 2 Taste twins | `SOCIAL_TWINS` | 14 |
| 3 Most typical member | `SOCIAL_TYPICAL` | 2 |
| 4 The one thing you all share | `SEMANTIC_UNANIMITY` | 4 |
| 5 Everyone except one | `SEMANTIC_EXCEPTION` | 0 here; 31 of 300 randomised rooms |
| 6 Most alike / most different | `SOCIAL_AGREEMENT` | 13 |
| 7 Hidden shared category | `SEMANTIC_PARTNER` | 9 |
| 8 Who is both | `CROSS_INTERSECTION_PERSON` | 7 |
| 9 Your song, their artist | `CROSS_MEDIA_LINK` | 7 |
| 10 Same film series | `SEMANTIC_LINK` | 0 here — see the caveat below |
| 11 Age spread | `SEMANTIC_SPREAD` | 0 here; 4 of 300 randomised rooms |
| 12 Age bands | `age.band` dimension | 19 age questions, no exact age revealed |
| 13 Age-band subgroup taste | `age.band` in cross-domain families | included in the above |
| 14 Food format | `food.format` dimension | folded into the food subject |
| 15 Who plays music | `hobby.making_music` dimension | folded into the hobby subject |

**Caveat on idea 10.** The reference data's film "series" values include studio catalogues (Pixar
films, Walt Disney Animation films) and critics' lists, which would have claimed *Toy Story* and
*Finding Nemo*, or *Finding Nemo* and *The Dark Knight*, are one series. Two films must now also
share a distinctive title word in one of the game languages before the engine calls them a series.
Genuine links it cannot confirm that way (*The Lord of the Rings* ↔ *The Hobbit*) are dropped
rather than asserted: a wrong claim costs more than a missing question.
