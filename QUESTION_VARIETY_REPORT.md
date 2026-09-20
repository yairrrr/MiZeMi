# MiZeMi — Question variety report

Design and candidate list: [QUESTION_VARIETY_DESIGN.md](QUESTION_VARIETY_DESIGN.md).
Question-by-question ratings: [QUESTION_STYLE_AUDIT.md](QUESTION_STYLE_AUDIT.md).

**How the numbers were produced.** Twenty synthetic but realistic rooms
([backend/tests/fixtures/variety_rooms.py](backend/tests/fixtures/variety_rooms.py) — classes, work
teams, a sports club, an art studio, a family gathering, 14–30 players, both languages, optional
fields filled at different rates) each play a 20-question game.
`.venv/bin/python scripts/analyze_question_variety.py` classifies every question by subject, profile
field, reasoning pattern, family and semantic signature and writes
[scripts/knowledge/variety-report.json](scripts/knowledge/variety-report.json). The BEFORE column is
the same twenty rooms played by the engine exported from `HEAD` (`git archive HEAD` into a separate
checkout), so both columns come from real generated games, not estimates. A second sweep plays 300
randomly parameterised rooms (4–30 players, random languages, random optional-field coverage) to
check leaks, duplicates and timing at scale.

---

## 1. Root causes of the repetition and the domain dominance

Measured on the BEFORE games, not inferred:

1. **Rules were written per dimension, not per idea.** Every rule offered itself for every dimension
   it fitted, so the supply was `rules × dimensions`. Selection could pick "how many chose a rock
   artist" and "how many chose a rock song" because they were different rules on different
   dimensions — the same idea to a player.
2. **Three reasoning shapes covered 72% of a game.** `count`, `majority` and `comparison` produced
   289 of 400 questions; one game used only five distinct patterns. Nothing in the selector
   limited how often one *way of thinking* returned — only how often a rule or domain returned.
3. **Duplicate detection worked on membership, not on meaning.** Two questions were "the same" only
   if they covered the same set of players. "Only one person chose classical music. Who?" and "only
   one person chose rock music. Who?" are different sets, so both were allowed.
4. **Music had three budgets.** Favourite music style, favourite artist and favourite song were
   three domains with three separate caps, so a group's musical taste took 36% of a game — the
   single largest source of "we keep asking the same thing".
5. **Two profile answers were almost or entirely unused.** `age` produced 2.8% of questions (and
   when it did, it asked for an exact age); `personal_fact` produced **nothing at all**.
6. **A quarter of every game was a lookup.** 96 of 400 questions (24%) were of the direct kind —
   "how many players have Painting as their hobby?" — reading back a profile answer.

The player-visible result is exactly the complaint: a game of *majority, majority, count, count,
comparison* over city, movies and music, with the same nouns coming back in different wording.

---

## 2. New question families implemented

Twelve new families, plus three new derived dimensions that give the existing families new material.
All are deterministic, offline, and derived only from answers players actually gave.

| Family | Reasoning | Question (as a player sees it) |
|---|---|---|
| `SOCIAL_ATTRIBUTION` | attribution | “Who wrote this about themselves: *‘I play five instruments’*?” |
| `SOCIAL_TWINS` | twins | “Which two of you turned out to be the most alike?” |
| `SOCIAL_TYPICAL` | typical | “Whose answers match the group’s most common choices?” |
| `SOCIAL_AGREEMENT` | agreement / variety | “Where are you the most different from each other — movies, hobbies or music?” |
| `SEMANTIC_UNANIMITY` | unanimity | “מה משותף לכולכם מבחינת מקום המגורים?” |
| `SEMANTIC_EXCEPTION` | exception | “כולם כאן גרים במרכז — חוץ מאדם אחד. מי?” |
| `SEMANTIC_PARTNER` | partner | “עומר בחר/ה את ״המסור״. מי עוד בחר/ה סרט מאותו ז׳אנר?” |
| `SEMANTIC_LINK` | link | “Amit chose *Toy Story*. Who picked another movie from the same series?” |
| `SEMANTIC_SPREAD` | spread | “כמה שנים מפרידות בין הצעיר/ה ביותר למבוגר/ת ביותר בקבוצה?” |
| `CROSS_INTERSECTION_PERSON` | both | “מי מכם בחר/ה גם מוזיקה אלקטרונית וגם סרט הרפתקאות?” |
| `CROSS_MEDIA_LINK` | link | “Lior picked Metallica. Which of you chose a song by Metallica?” |
| `GEO_REGION_COUNT` / `GEO_REGION_UNIQUE` | count / unique | “How many of you come from the south?” · “Who is the only one here from the Jerusalem area?” |

New derived dimensions (they widen what every family can ask about):

* **`age.band`** — 12 and under, 13–15, 16–18, 19–24, 25–34, 35–49, 50+. Age questions now ask about
  ranges and distributions. **No question and no explanation names an exact age**, and the
  individual evidence lines that other dimensions print are suppressed for age.
* **`food.format`** — soups, salads, sandwiches, desserts, pasta, rice dishes, dips, stews, egg
  dishes, potato dishes, dumplings: a second, independent way to look at the same food answers.
* **`hobby.making_music`** — playing or singing, which the hobby data already knew and nothing used.

Also newly used reference data that was already in the bundle: a song's performer ids (→
`CROSS_MEDIA_LINK`) and a film's series ids (→ `SEMANTIC_LINK`).

**Consent and free text.** `personal_fact` is used in exactly one way: the text the player wrote is
quoted and the question asks who wrote it. Nothing tries to interpret it, categorise it or infer
anything from it. A withheld fact never appears, and a fact whose writer withheld their name never
becomes a question. Where meaning cannot be derived, the answer stays UNKNOWN.

---

## 3. Creative ideas that were rejected

The design document lists all thirty candidates with verdicts; fifteen were implemented. The
rejections, with reasons:

* **Trivia** — "which decade are your films from", "which country do your dishes come from": the
  answer is in the reference data, not in the group.
* **Statistics homework** — "how many wrote an answer nobody else shares", "does hobby X predict
  music Y", "longest chain of shared categories", "which two categories never co-occur": correct,
  deterministic and unanswerable in 20 seconds without a table.
* **Needs its own algorithm explained** — "who changed the group's majority": if the question has to
  describe how it was computed, it is not a game question.
* **Arbitrary** — "which category did nobody choose": infinitely many categories are absent.
* **More of what already dominates** — district instead of region, "who shares a hometown": city
  questions are the problem, not the fix.
* **Risk to a person** — "who is least like everyone here" can land badly in a classroom.

Five ideas are recorded as MAYBE (even split, closest ages, rarest chosen category, same-answer
twins, most unusual member) so they are neither lost nor implemented on a hunch.

---

## 4. Semantic signature and deduplication

Wording is never the duplicate test. Every candidate now carries, in its metadata:

```
signature = (operation, topic, *fact)     # e.g. ('majority', 'music.genre', 'artist.genre', 'rock')
idea      = (idea_class, idea_topic)      # e.g. ('ranked_list', 'music.genre')
subgroup  = 'place.north'                 # the population a cross-domain question scopes to
anchor    = 'favorite_movie:p7'           # the one answer a question is built around
```

* **`operation`** is the reasoning act: count, majority, comparison, unique, diversity,
  distribution, minority, extreme, outlier, unanimity, exception, partner, link, both, twins,
  typical, agreement, variety, spread, attribution.
* **`topic`** is the *subject as a player experiences it*: `artist.genre` and `song.genre` both
  collapse to `music.genre`, so "which genre leads among your artists" and "which style leads among
  your songs" are one idea.
* **`idea_class`** groups mirror-image shapes that read as one question: distribution + minority →
  `ranked_list`; agreement + variety → `group_spread`; partner + link + both → `connection`.
* A **signature** or an **idea** may appear once per game. A **subgroup** ("among those from the
  north…") may anchor one question. A person's **answer** may anchor one question, so "Lior chose
  Coldplay — who else chose that style?" and "Lior chose Coldplay — who chose a song of theirs?"
  cannot both appear.

On top of this the existing disclosure protection is unchanged and still authoritative: every
counting or ranking family declares what it `reveals` and what would `settle` it, and no question is
shown that an earlier one already answers. Near-duplicates now count as disclosure too, because the
signature and idea keys are checked before the reveal check.

---

## 5. Selector changes

[backend/app/domain/questions/selector.py](backend/app/domain/questions/selector.py):

* **Candidates collapse to one per fact** before planning, so a rule that emits hundreds of
  renderings competes exactly like a rule that emits one.
* **Kind plan**: about 45% semantic discoveries, 20% cross-domain, 13% geography, 12% social, 10%
  direct — limited by what the room actually supports; an unsupported share flows to kinds that have
  more to offer, and is never padded.
* **Three variety passes.** Pass 0 takes only reasoning patterns not used yet. Pass 1 allows a
  pattern to return, but only on a subject it has not been applied to. Pass 2 is the last resort and
  relaxes the pattern cap. Family and subject caps relax *before* variety does.
* **Headline reservation**: the two strongest facts per subject are reserved before the variety
  staging, so "most of you live in the north" is not squeezed out by the diversity rules.
* **Raw lookups are deferred** to the end and capped at one per game and 10% of the requested count;
  they are only taken when no unsettled discovery is left.
* **Ranking** inside a pass is explainable and deterministic, in this order: reserved headline
  facts first → fewest uses of this reasoning pattern → the best remaining fact of its subject →
  fewest uses of this pattern-on-this-subject → fewest questions on this subject → least-used
  profile field → least-used family → least-used domain → least-used family-on-domain → facts not
  settled elsewhere → not the same subject as the previous question → distance from the difficulty
  band for this position → quality score → fewest questions about these players → stable fact order.
  No random tie-breaking, no large arbitrary bonuses.

---

## 6. Domain balancing

Music style, favourite artist and favourite song are **one subject** with one budget; film, place,
food, hobby, age and personal are the others. Caps for a 20-question game: 6 questions per subject
(never relaxed), 5 per domain, 4 per family, 1 per family-on-domain, 5 questions built on one
person's answer, 2 direct questions of which at most 1 is a raw lookup. A reasoning pattern may be
used once in pass 0, twice in pass 1 and four times in pass 2; only the final relaxation lifts it.

Cross-domain questions must clear a meaningfulness threshold: both sides need at least two people,
the subgroup must be large enough to say something, and a comparison is rejected when one side is
more than three times the other. This is what stops "among the one person who likes jazz…".

---

## 7. Reasoning-family balancing

| | BEFORE | AFTER |
|---|---:|---:|
| Distinct reasoning patterns per game | 5 – 9 | **9 – 12** |
| Share of the three most-used patterns | 72% | **55%** |
| Largest count of one pattern in a game | 8 | **6** |
| Distinct families in 20 games | 20 | **29** |
| Distinct families over 300 random rooms | — | **33** |

---

## 8. Before / after over twenty games

**Subjects** (a cross-domain question counts under each subject it touches):

| Subject | BEFORE | AFTER |
|---|---:|---:|
| Music (style + artist + song) | 143 (35.8%) | **118 (29.9%)** |
| Film | 82 (20.5%) | 106 (26.9%) |
| Place / city | 85 (21.2%) | 98 (24.9%) |
| Hobby | 84 (21.0%) | 93 (23.6%) |
| Food | 59 (14.8%) | 62 (15.7%) |
| Age | 11 (2.8%) | **19 (4.8%)** |
| Personal fact | 0 (0.0%) | **16 (4.1%)** |

**Profile fields** — every field is now used, and no field is unused:

| Field | BEFORE | AFTER |
|---|---:|---:|
| `city` | 85 (21.2%) | 98 (24.9%) |
| `favorite_movie` | 82 (20.5%) | 106 (26.9%) |
| `favorite_music` | 60 (15.0%) | 64 (16.2%) |
| `favorite_artist` | 55 (13.8%) | **38 (9.6%)** |
| `favorite_song` | 28 (7.0%) | 23 (5.8%) |
| `favorite_food` | 59 (14.8%) | 62 (15.7%) |
| `hobby` | 84 (21.0%) | 93 (23.6%) |
| `age` | 11 (2.8%) | **19 (4.8%)** |
| `personal_fact` | **0 (0.0%)** | **16 (4.1%)** |
| Distinct fields per game | 5 – 8 | **7 – 9** |

**Dominance inside a single game** — the honest measure of "too many questions about X" is how much
of one game one subject owns on its own:

| | BEFORE | AFTER |
|---|---|---|
| Largest single-subject share of a game | 20% – **45%** (9 of 20 about music) | 20% – **30%** |
| Games where one subject held ≥ 35% | 4 of 20 | **0 of 20** |
| Largest share counting shared subjects | 20% – 30% | 25% – 40% |

The last row is the one number that moved the wrong way, and it is worth being precise about why: a
question like "which two of you are most alike — based on films, hobbies and music" counts under
three subjects, so the new social and cross-domain families raise every subject's *touch* count
while lowering how much of the game any subject owns. City and film touches rose (21%→25%, 20%→27%)
because the music budget was cut and those slots went to the next best-supported subjects, and
because those subjects now host many *different* kinds of question rather than the same three.

**Cross-domain and lookups:**

| | BEFORE | AFTER |
|---|---:|---:|
| Cross-domain questions | 64 (16%) | 66 (17%) |
| Social questions (a person, not a statistic) | 0 (0%) | **16 (4%)** |
| Questions from families that did not exist before | 0 (0%) | **80 (20%)** |
| Direct-kind questions | 96 (24%) | **24 (6%)** |
| Raw answer lookups | 96 (24%) | **7 (1.8%)** |

**Acceptance targets, per game, all twenty rooms:**

| Target | Result |
|---|---|
| ≥ 6 distinct reasoning families | met in 20/20 (lowest 9) |
| ≥ 5 profile fields | met in 20/20 (lowest 7) |
| No subject over 30% of the requested count | met in 20/20 |
| No repeated semantic signature | met in 20/20 (0 repeats) |
| Direct lookups ≤ 10% | met in 20/20 (1.8% overall) |
| Zero already-answered questions | met in 20/20, and in 300/300 random rooms |

---

## 9. An example game — the same room, before and after

`university_en`: 30 players, ages 19–27, rich profiles, 20 questions requested.

**BEFORE** (6 × majority, 6 × count, 4 × comparison, 2 × literal):

| # | Pattern | Question | Answer |
|---:|---|---|---|
| 1 | majority | Which genre is most common among the favorite artists you chose? | Pop |
| 2 | majority | Which genre shows up most in the movies you chose? | Thriller |
| 3 | count | How many people here have a sports hobby? | 10 |
| 4 | count | Among the artist choices we recognized, how many chose an artist associated with rock music? | 7 |
| 5 | majority | **What is the most common age in this group?** | **20** |
| 6 | count | **How many players have "Painting" as their hobby?** | 4 |
| 7 | majority | In which region of Israel do the most of you live? | The center |
| 8 | count | How many people in our group chose a horror movie? | 6 |
| 9 | extreme | Which of you lives in the northernmost town? | Jonathan |
| 10 | count | How many of you picked electronic music as your favorite style? | 6 |
| 11 | comparison | Based on the movies you chose, which leads — Adventure or Horror? | Horror |
| 12 | comparison | Based on your choices, which leads — Pop or Electronic? | Electronic |
| 13 | comparison | Which appears more in the hobbies you chose — Sport or Nature? | Sports hobbies |
| 14 | literal | **Are there more Rock fans or Hip-hop fans in our group?** | Hip-hop |
| 15 | diversity | From how many regions of Israel does our group come? | 4 |
| 16 | literal | **Are there more Rock fans or R&B fans in our group?** | R&B |
| 17 | count | How many people live in the center of the country and chose a sports hobby? | 4 |
| 18 | majority | Among people who live in the north, which music style is the most common? | Pop |
| 19 | comparison | Among people who chose horror movies, which is more common — creative or relaxation hobbies? | Creative hobbies |
| 20 | majority | Among people who live in the south, which type of hobby is the most common? | Arts and crafts |

Six questions about music, an exact age revealed, a raw hobby lookup, and questions 14 and 16 are
the same question with one noun changed.

**AFTER** (11 distinct patterns, no subject above 6, nothing repeated):

| # | Pattern | Subject | Question | Answer |
|---:|---|---|---|---|
| 1 | majority | age | Most of the shared ages fall in one range. Which? | 19–24 |
| 2 | count | hobby | How many people here have a sports hobby? | 10 |
| 3 | majority | place | In which region of Israel do the most of you live? | The center |
| 4 | attribution | personal | Who wrote this about themselves: “I collect stamps”? | Yam |
| 5 | extreme | place | Which of you lives in the northernmost town? | Jonathan |
| 6 | count | music | Among the artist choices we recognized, how many chose an artist associated with rock music? | 7 |
| 7 | count | place | How many of you come from the south? | 6 |
| 8 | count | hobby | How many of you picked an outdoor hobby? | 6 |
| 9 | variety | film+music+place | Where are you the most different from each other — where you live, movies or music? | music |
| 10 | comparison | hobby | Which appears more in the hobbies you chose — Sport or Nature? | Sports hobbies |
| 11 | twins | film+music | Which two of you turned out to be the most alike? | Gal + Tal |
| 12 | partner | film | Yael chose “Finding Nemo”. Who else picked a movie from the same genre? | Nadav |
| 13 | distribution | music | Of these music styles, which did the most people choose? | Pop |
| 14 | diversity | place | From how many regions of Israel does our group come? | 4 |
| 15 | comparison | music | Based on your choices, which leads — Hip-hop or Mizrahi? | Hip-hop |
| 16 | unique | place | Who is the only one here from the Jerusalem area? | Dana |
| 17 | distribution | film | Of these genres, which appears most in the movies you chose? | Drama |
| 18 | comparison | film | Based on the movies you chose, which leads — Adventure or Horror? | Horror |
| 19 | count | hobby+music | How many people chose both electronic music and a sports hobby? | 4 |
| 20 | majority | film+hobby | Among people who chose crime movies, which type of hobby is the most common? | Sport |

---

## 10. Direct-question reduction

| | BEFORE | AFTER |
|---|---:|---:|
| Direct-kind questions | 96 of 400 (24%) | 24 of 394 (6%) |
| Raw answer lookups ("how many chose *Herzliya*?") | 96 (24%) | 7 (1.8%) |
| Games with more than 2 lookups | 20 of 20 | 0 of 20 |

The remaining direct questions are almost all `DIRECT_CHOICE` — facts about a listed music style,
which players see as an ordinary group question, not as their form being read back. Raw lookups are
capped at one per game and are only taken when nothing else is left.

---

## 11. Duplicate and near-duplicate reduction

| | BEFORE | AFTER |
|---|---:|---:|
| Same reasoning on the same dimension, twice in a game | 12 | **0** |
| Repeated semantic signature | 12 | **0** |
| Repeated idea key (mirror-image questions) | not detected | **0** |
| Same pattern applied to the same subject twice | 65 | 53 |
| Any repeat of a reasoning pattern | 253 | 183 |
| Any repeat of a family | 117 | 75 |
| Questions already answered by an earlier one | 0 | **0** |

Over 300 randomised rooms: **0** repeated signatures and **0** settled-answer leaks.

The middle rows are deliberately not zero. A 20-question game cannot have 20 different reasoning
patterns — there are not that many that stay simple — so a pattern returns, but only on a subject it
has not been used on, and never with the same signature or idea.

---

## 12. Performance

| Scenario | Time |
|---|---|
| 30 players, rich profiles, 20 questions (`university_en`) | **12.4 ms** median, 12.5 ms max |
| 300 randomised rooms, 4–30 players | median **13.1 ms**, p95 20.0 ms, max 26.6 ms |
| Budget | 500 ms |

Selection stayed linear: candidates collapse to one per fact before planning, and the staged fill
walks the remaining pool. The added dedupe keys are set lookups.

---

## 13. Tests

| Suite | Result |
|---|---|
| Full backend suite (`.venv/bin/python -m pytest backend/tests -q`) | **1560 passed, 2 skipped** |
| Question-variety tests (`backend/tests/unit/test_question_variety.py`, new) | **59 passed** |
| Frontend unit tests (`npm test`) | **300 passed**, 12 files |
| End-to-end (`npm run test:e2e`, Playwright) | **3 passed** |
| Classroom smoke (1 host + 20 players, 21 real WebSockets) | **PASS**, 0.20 s |
| Secrets scan (`scripts/check_secrets.py`) | 248 files, **0 findings** |
| `git diff --check` | clean |

The new test file covers: no repeated idea in any of the twenty rooms; the rich-room targets; one
question per anchoring answer; attribution respects consent and withheld names; twins, typical,
unanimity, exception, partner, both, song→artist and film-series correctness; age questions never
reveal an exact age; food formats and music-making; Hebrew/English equivalence; and generation under
500 ms.

**One existing E2E assertion was updated.** The Hebrew classroom test pinned one specific
cross-domain explanation (sports hobbies × horror films). The new selection picks different, equally
cross-domain pairings for that room, so the assertion now checks two cross-domain explanations that
the engine produces for it in 80 of 80 seeds (sports hobbies × Mizrahi music, horror films × Italian
food). The intent of the assertion — cross-domain reasoning reaching the players — is unchanged.

**One bug found and fixed during the manual audit.** The film-series family trusted the reference
data's "series" values, which include studio catalogues and critics' lists, and so claimed *Toy
Story* and *Finding Nemo* — and *Finding Nemo* and *The Dark Knight* — belong to the same film
series. Two films must now also share a distinctive word of their title in one of the game languages
before they are called one series. This is conservative: genuine links it cannot confirm (*The Lord
of the Rings* ↔ *The Hobbit*) are dropped rather than asserted.

---

## 14. Remaining limitations

1. **Short games can still lean on one subject.** The subject cap is a share of the *requested*
   count, so a room whose data supports only 14–18 questions can end with one subject at 33–40% of
   what it delivered — 15 of 300 randomised rooms by exclusive subject. A prefix-proportional cap
   was implemented and measured, and then reverted: it cut full 20-question games from 215/300 to
   90/300 and produced games of 4–6 questions. Losing a third of the game to improve a ratio is the
   wrong trade.
2. **Film, place and hobby touch counts rose**, as §8 explains. Music fell where it should (36% →
   30%) and no subject owns more than 30% of a game, but if the goal is read as "fewer questions
   mentioning the city", city is not yet lower.
3. **85 of 300 randomised rooms return fewer than 20 questions** (as few as 8, for a 4-player room).
   This is the intended behaviour — quality over count — and every such game is still fully
   playable, but a host asking for 20 will sometimes get 15.
4. **`personal_fact` supports exactly one family.** Free text is quoted, never interpreted, so it
   contributes about 4% of questions and only when players consented and did not withhold their
   name. This is a deliberate ceiling, not a gap to close later with inference.
5. **Two families are rare.** `SEMANTIC_SPREAD` (age range) appeared in 4 of 300 randomised rooms
   and `SEMANTIC_EXCEPTION` in 31 of 300; they need a specific shape of data. `SEMANTIC_LINK` now
   needs two films of one franchise in the room and did not appear in the twenty fixture rooms at
   all — correct, since none of those rooms contains two films from one series.
6. **The upper bound is the profile.** Six answers plus two optional ones cannot support twenty
   genuinely different discoveries in a thin room; in those rooms the game is shorter rather than
   repetitive.

---

## Acceptance question

> Does the game now feel like it is DISCOVERING interesting things about the group rather than
> repeating their profile form?

**Yes for rooms with real data, with the two qualifications below.**

The evidence for yes:

* Reading a profile answer back is now 1.8% of questions, down from 24%. A full quarter of the old
  game was a lookup; almost none of the new game is.
* 20% of questions come from families that did not exist before: who wrote this about themselves, which
  two of you are most alike, what you all share, who is the exception, who else chose your genre,
  who chose a song by your favourite artist, who is in both groups.
* A game now uses 9–12 distinct ways of thinking instead of 5–9, and the three commonest cover 55%
  instead of 72%.
* No subject owns more than 30% of a game, down from 45%; music specifically fell from 36% to 30%.
* No game contains two questions with the same semantic signature or the same idea, and no question
  is answered by an earlier one — in 20 fixture games and 300 randomised rooms alike.
* Age stopped being "who is 26?" — it is ranges, distributions and spreads, and no exact age is ever
  printed.

The qualifications:

* **Thin rooms**: where players skipped optional answers, the game falls back on the same four
  subjects and gets shorter. It does not repeat itself, but it discovers less.
* **Surface counts**: roughly half the questions are still a count, majority or comparison over a
  profile field. They are now spread across subjects, framed as group facts and never duplicated,
  but a player who dislikes "how many of you…" as a shape will still meet it several times.

---

MIZEMI QUESTION VARIETY COMPLETE
