# Question style audit

Reviewed on 2026-09-14 after the category-first engine change ([QUESTION_ENGINE_DIAGNOSTIC.md](QUESTION_ENGINE_DIAGNOSTIC.md)). Ten complete 20-question games — 200 questions — were generated from ten realistic synthetic rooms, each in its own language, and every question, option set and explanation was read. Names and answers are fictional.

- Rooms: [backend/tests/fixtures/rooms.py](backend/tests/fixtures/rooms.py) — Hebrew rich room, English rich room, movie-heavy, hobby-heavy, food-heavy, geography-heavy, mixed English room with artists and songs, sparse room, unknown-heavy room and consent-restricted room.
- Games: [scripts/knowledge/group-games.json](scripts/knowledge/group-games.json), reproduced by `.venv/bin/python scripts/audit_group_questions.py`. It contains every profile answer (with withheld fields), question, option, correct answer, explanation and the internal family, kind and domain. Reviewed artifact SHA-256: `7f9257a4a56cc72b1a65a12cf422db7a01fe515390f568dfa08f10e5a97f5301`.
- Automated wording checks cover many more games: `test_scenario_11_hundreds_of_hebrew_questions_use_plain_spoken_hebrew` scans 600 Hebrew questions for implementation vocabulary, unformatted placeholders, raw English choice values and a singular subject with a plural verb; `test_scenario_12_hebrew_and_english_games_ask_the_same_facts` proves the two languages select identical facts and answers in all ten rooms; `test_no_question_is_answered_by_one_shown_before_it` replays every final game in presentation order and fails if an earlier question or its explanation already settles a later count, comparison or ranking.

## Criteria

- **GOOD** — a clear, objective discovery about these participants in natural spoken language: a group count, majority, comparison or unique member derived from their answers; a regional or distance fact; a simple cross-domain subgroup fact.
- **ACCEPTABLE** — correct and clear, but less of a discovery: a literal lookup ("who is the only one who chose shawarma?"), a listed-choice fact that no grouping changed, a scoped “of these…” question, a comparison where one side is a single person, a count of one, a subgroup led by two people, or a repeat of a geography or cross-domain family already asked in the same game.
- **BAD** — general-knowledge trivia, an unsupported inference about people, ambiguity or a hidden tie, a misleading group claim, implementation vocabulary, a grammar error, unclear wording, or a question that an earlier question (or its explanation) in the same game already answers. Every BAD pattern found was fixed in the engine and the games were regenerated.

## Outcome

**121 GOOD · 79 ACCEPTABLE · 0 BAD.**

| Room | Language | Players | Semantic | Geographic | Cross-domain | Direct | GOOD | ACCEPTABLE | BAD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| he_rich | he | 20 | 9 | 4 | 2 | 5 | 15 | 5 | 0 |
| en_rich | en | 20 | 9 | 3 | 3 | 5 | 12 | 8 | 0 |
| movie_heavy | he | 16 | 9 | 3 | 3 | 5 | 14 | 6 | 0 |
| hobby_heavy | en | 18 | 6 | 3 | 4 | 7 | 12 | 8 | 0 |
| food_heavy | he | 18 | 7 | 4 | 4 | 5 | 14 | 6 | 0 |
| geo_heavy | he | 15 | 9 | 3 | 4 | 4 | 14 | 6 | 0 |
| mixed_en | en | 12 | 10 | 3 | 3 | 4 | 13 | 7 | 0 |
| sparse | he | 6 | 6 | 7 | 1 | 6 | 6 | 14 | 0 |
| unknown_heavy | he | 20 | 0 | 7 | 3 | 10 | 7 | 13 | 0 |
| consent_restricted | he | 14 | 10 | 4 | 4 | 2 | 14 | 6 | 0 |

The sparse and unknown-heavy rooms have the most ACCEPTABLE questions, as designed: six players, or twenty players whose films and dishes are mostly unrecognized, leave little to discover, so the engine fills the game with valid literal and geographic questions instead of inventing group claims. The unknown-heavy room gets **no** movie or cuisine claims at all.

## BAD patterns found in this revision and fixed

| Pattern (real examples) | Why it was BAD | Fix |
|---|---|---|
| “כמה משתתפים בחרו במוזיקה בסגנון "Pop"?” | Raw English choice values inside Hebrew questions. | Music-choice facts come only from the music families, rendered with Hebrew labels. |
| “מבין דנה, עומר, נועה, עמית, ליאור, יעל, כמה בחרו סרטים בז׳אנר אימה?” | A list of six names; requires knowing who is who and reads like a lookup. | Removed from production; the coverage policy replaces name-scoped counts. |
| “מבין המשתתפים שבחרו "Pop" לגבי סגנון מוזיקה, מה הכי נפוץ אצלם לגבי תחביב?” | Form-like wording (“לגבי”) and raw values. | Replaced by cross-domain subgroup families with natural wording. |
| “אצל בעלי איזה תחביב יש בקבוצה את המגוון הכי רחב של סגנונות מוזיקה?” | Opaque, needs explanation to understand. | Removed from production. |
| “מה יש יותר — אוכל איטלקי או מקסיקני?” (6 vs 1); later “Are there more sports hobbies or cooking and baking hobbies?” (11 vs 2) | A lopsided comparison is not a discovery. | Pairs ranked by the smaller side, then closeness; the smaller side needs two people when eight or more answered; no side may have more than three times the other. |
| “רוב הקבוצה גרה באותו אזור” for 7 of the 11 shared towns in a 14-person room | Players see 14 people; 7 is not “most of the group”. | “Most of the group” requires more than half of the visible room; strong claims need half the room to have shared. |
| “Only one person chose a Electronic song.” | Grammar. | “a song in the Electronic style”. |
| Explanations listing “פארק היורה (סרט)”, “H̱olon”, “הייקינג” for טיולים | Reference labels players do not recognize. | Explanations show what the player typed; reference names only when the typed script differs from the game language, without disambiguation. |
| “מי היחיד שגר בהרצליה?” and “כמה משתתפים גרים בהרצליה?” (1) | The same fact asked twice. | Counts of one are dropped; direct and discovery facts share membership signatures. |
| “איזה סגנון מוזיקה הכי פופולרי?” and “כמה בחרו מוזיקת פופ?” | The majority's winner count repeats the majority. | The majority carries the winner's membership signature. |
| Four “מבין … האלה” questions in one game | Repetitive, low discovery. | Supporting families (minority, distribution, region counts) are capped at one each per 20 questions. |
| “באיזה אזור בארץ גרים הכי הרבה מכם?” (המרכז), later “מאיפה מגיעים יותר מכם — מהמרכז או מהדרום?”; “איזה סוג תחביב יש להכי הרבה אנשים כאן?” whose explanation names אמנות ויצירה second, later “מבין סוגי התחביבים האלה, איזה הכי נפוץ?” (אמנות ויצירה) | The later question was already answered. With the check disabled, all 12 fixture games had one (38 questions), and 290 of 300 randomized rooms. The same held for raw answers (“איזו עיר מופיעה הכי הרבה?” then “באיזו משתי הערים האלה…?”), subgroups (“מבין מי שגרים במרכז… איטלקי או אסייתי?” explaining “4 בחרו אוכל איטלקי”, then “כמה גרים במרכז ובחרו מאכל איטלקי?”) and counts of one (“only one chose American food”, then “which cuisine is least common?”). | Every counting or ranking family declares what it discloses and what would settle it; the selector, knowing games run easy to hard, never picks a question an earlier one settles and prefers the fact that settles the other when it reasons at least as deeply. Fixture games: 0. Randomized rooms: 7, only as the last resort in tiny rooms. |
| “9 אנשים גרים במרכז — יותר מכל אזור אחר. במקום השני: הצפון (4).” with the south also at 4 | A hidden tie presented as a ranking (6 of 26 named runners-up). | A runner-up is named only when it leads third place by more than the number of unrecognized answers. |
| “אדם אחד בחרו גם מוזיקה מזרחית וגם תחביב ספורטיבי” | Grammar: a singular subject with a plural verb (also “One person live in…”). | Intersection explanations use singular verbs for one person; the Hebrew scan rejects the pattern. |
| “Among people who chose pop music, which type of hobby…?” (sport) and “among people with a sports hobby, which music style…?” (pop) in one game | The same two people, asked from both sides. | Subgroup leaders and intersection counts about the same two categories share one membership signature. |

Earlier rejected patterns remain rejected: entity trivia (“באיזה עשור יצא המסור?”), person similarity (“מי הכי דומה לדני?”), inferred listening (“למי בטוח יש עומר אדם בפלייליסט?”) and implementation vocabulary (“מי בחר ערך נדיר בשדה X?”).

## Complete-game review

### he_rich — he

Hebrew classroom: realistic spellings, a few unknown or skipped answers and consent choices.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | איזה סוג תחביב יש להכי הרבה אנשים כאן? | ספורט |  |
| 2 | GOOD | semantic | SEMANTIC_COUNT | כמה מהמאכלים שבחרתם הם מהמטבח האיטלקי? | 6 |  |
| 3 | GOOD | semantic | SEMANTIC_COUNT | לכמה מכם יש תחביב שעושים בחוץ? | 4 |  |
| 4 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה מכם בחרו מוזיקת רוק כסגנון האהוב? | 3 | Simple lookup or listed choice. |
| 5 | ACCEPTABLE | direct | DIRECT_UNIQUE | מי היחיד/ה שהתחביב שלו/ה הוא "קריאה"? | תמר | Simple lookup or listed choice. |
| 6 | ACCEPTABLE | direct | DIRECT_COMPARISON | איזה משני המאכלים האלה נבחר יותר בקבוצה? | פיצה | Simple lookup or listed choice. |
| 7 | GOOD | geographic | GEO_REGION_MAJORITY | באיזה אזור בארץ גרים הכי הרבה מכם? | המרכז |  |
| 8 | ACCEPTABLE | direct | DIRECT_COUNT | כמה משתתפים בחרו "סושי" כאוכל האהוב עליהם? | 2 | Simple lookup or listed choice. |
| 9 | GOOD | semantic | SEMANTIC_COUNT | כמה סרטי הרפתקאות יש בין הסרטים שבחרתם? | 7 |  |
| 10 | ACCEPTABLE | direct | DIRECT_UNIQUE | מי היחיד/ה שבחר/ה "שווארמה" כאוכל אהוב? | רוני | Simple lookup or listed choice. |
| 11 | GOOD | geographic | GEO_EXTREME | מי מכם גר/ה ביישוב הכי צפוני? | ליאור |  |
| 12 | GOOD | semantic | SEMANTIC_COMPARISON | אם מסתכלים על בחירות הסרטים, איזה צד מנצח — הרפתקאות או פשע? | הרפתקאות |  |
| 13 | GOOD | semantic | SEMANTIC_UNIQUE | רק אדם אחד בחר אמן שמזוהה עם מוזיקת רוק. מי זה? | מאיה |  |
| 14 | GOOD | semantic | SEMANTIC_COMPARISON | לפי המאכלים שבחרתם, מה מוביל — אוכל איטלקי או אמריקאי? | איטלקי |  |
| 15 | GOOD | semantic | SEMANTIC_DIVERSITY | כמה סגנונות מוזיקה שונים מיוצגים כאן? | 5 |  |
| 16 | GOOD | geographic | GEO_REGION_COMPARISON | מה יש יותר בקבוצה — אנשים מהדרום או מאזור ירושלים? | הדרום |  |
| 17 | GOOD | semantic | SEMANTIC_UNIQUE | רק אדם אחד בקבוצה בחר תחביב של הרפיה. מי זה? | נדב |  |
| 18 | GOOD | geographic | GEO_REGION_DIVERSITY | מכמה אזורים בארץ מגיעים חברי הקבוצה? | 4 |  |
| 19 | GOOD | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שגרים במרכז, איזה סגנון מוזיקה הכי נפוץ? | פופ |  |
| 20 | GOOD | cross_domain | CROSS_INTERSECTION_COUNT | כמה אנשים בחרו גם מוזיקה אלקטרונית וגם תחביב ספורטיבי? | 2 |  |

### en_rich — en

English classroom with the same realistic gaps as he_rich.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | Which type of hobby do the most people here have? | Sport |  |
| 2 | GOOD | semantic | SEMANTIC_COUNT | How many of you picked electronic music as your favorite style? | 3 |  |
| 3 | GOOD | semantic | SEMANTIC_COUNT | How many people in our group chose an Asian dish? | 5 |  |
| 4 | ACCEPTABLE | direct | DIRECT_CHOICE | Which music style is the most popular here? | Pop | Simple lookup or listed choice. |
| 5 | GOOD | semantic | SEMANTIC_MAJORITY | Which genre shows up most in the movies you chose? | Adventure |  |
| 6 | ACCEPTABLE | direct | DIRECT_UNIQUE | Who is the only player whose favorite food is "Salad"? | Michal | Simple lookup or listed choice. |
| 7 | ACCEPTABLE | direct | DIRECT_COUNT | How many players have "Football" as their hobby? | 2 | Simple lookup or listed choice. |
| 8 | ACCEPTABLE | direct | DIRECT_COMPARISON | Which of these two favorite food choices was shared by more players? | Pizza | Simple lookup or listed choice. |
| 9 | GOOD | geographic | GEO_REGION_MAJORITY | In which region of Israel do the most of you live? | The center |  |
| 10 | GOOD | semantic | SEMANTIC_COUNT | How many people in our group chose a comedy? | 6 |  |
| 11 | ACCEPTABLE | direct | DIRECT_UNIQUE | Who is the only player whose hobby is "Reading"? | Tamar | Simple lookup or listed choice. |
| 12 | GOOD | geographic | GEO_EXTREME | Which of you lives in the southernmost town? | Jonathan |  |
| 13 | GOOD | semantic | SEMANTIC_COMPARISON | Are there more comedy fans or crime fans in our group? | Comedy |  |
| 14 | GOOD | semantic | SEMANTIC_UNIQUE | Only one person in our group chose a digital hobby. Who? | Lior |  |
| 15 | GOOD | geographic | GEO_REGION_COMPARISON | Are there more people from the south or from the Jerusalem area in our group? | The south |  |
| 16 | GOOD | semantic | SEMANTIC_COMPARISON | Are there more physically active hobbies or hobbies without physical effort in our group? | Physically active hobbies |  |
| 17 | ACCEPTABLE | semantic | SEMANTIC_UNIQUE | Only one person chose an artist associated with country music. Who? | Omer | Correct per the reference data, but players may think of this artist as pop. |
| 18 | GOOD | cross_domain | CROSS_INTERSECTION_COUNT | How many people chose both an action movie and an Asian dish? | 3 |  |
| 19 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_MAJORITY | Among people who live in the north, which music style is the most common? | Pop | Subgroup leader of two. |
| 20 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_MAJORITY | Among people who chose Asian food, which region do the most come from? | The center | Repeats a family already asked in this game. |

### movie_heavy — he

Sixteen recognized movies spanning horror, science fiction, animation, comedy and romance.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | איזה סוג תחביב יש להכי הרבה אנשים כאן? | ספורט |  |
| 2 | GOOD | semantic | SEMANTIC_COUNT | כמה מהמאכלים שבחרתם הם מהמטבח האיטלקי? | 5 |  |
| 3 | GOOD | semantic | SEMANTIC_COUNT | כמה אנשים בקבוצה בחרו קומדיה? | 7 |  |
| 4 | ACCEPTABLE | direct | DIRECT_CHOICE | איזה סגנון מוזיקה הכי פופולרי כאן? | פופ | Simple lookup or listed choice. |
| 5 | ACCEPTABLE | direct | DIRECT_UNIQUE | מי היחיד/ה שגר/ה ב"ראשון לציון"? | מיכל | Simple lookup or listed choice. |
| 6 | ACCEPTABLE | direct | DIRECT_COMPARISON | איזה משני התחביבים האלה נפוץ יותר בקבוצה? | ריצה | Simple lookup or listed choice. |
| 7 | GOOD | geographic | GEO_REGION_MAJORITY | רוב הקבוצה גרה באותו אזור. באיזה? | המרכז |  |
| 8 | ACCEPTABLE | direct | DIRECT_COUNT | כמה משתתפים בחרו "ציור" כתחביב? | 2 | Simple lookup or listed choice. |
| 9 | ACCEPTABLE | direct | DIRECT_UNIQUE | מי היחיד/ה שהסרט האהוב עליו/ה הוא "בחזרה לעתיד"? | יעל | Simple lookup or listed choice. |
| 10 | GOOD | semantic | SEMANTIC_COUNT | לכמה מכם יש תחביב שעושים בחוץ? | 3 |  |
| 11 | GOOD | geographic | GEO_EXTREME | מי מכם גר/ה ביישוב הכי צפוני? | תמר |  |
| 12 | GOOD | semantic | SEMANTIC_COMPARISON | לפי הסרטים שבחרתם, מה מוביל — קומדיה או מתח? | קומדיה |  |
| 13 | GOOD | semantic | SEMANTIC_UNIQUE | רק אדם אחד בקבוצה בחר מאכל ספרדי. מי זה? | איתן |  |
| 14 | GOOD | semantic | SEMANTIC_UNIQUE | רק אדם אחד בקבוצה בחר תחביב של בישול או אפייה. מי זה? | יונתן |  |
| 15 | GOOD | semantic | SEMANTIC_DIVERSITY | כמה מטבחים שונים מיוצגים בבחירות האוכל שלכם? | 6 |  |
| 16 | GOOD | geographic | GEO_REGION_COMPARISON | מאיפה מגיעים יותר מכם — מהצפון או מהדרום? | הדרום |  |
| 17 | ACCEPTABLE | semantic | SEMANTIC_DISTRIBUTION | מבין המטבחים האלה, איזה הכי נפוץ בבחירות האוכל שלכם? | אסייתי | Scoped “of these” question. |
| 18 | GOOD | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שגרים במרכז, איזה סגנון מוזיקה הכי נפוץ? | פופ |  |
| 19 | GOOD | cross_domain | CROSS_SUBGROUP_COMPARISON | מבין מי שגרים במרכז, מה יותר אהוב — אוכל אסייתי או מזרח תיכוני? | אסייתי |  |
| 20 | GOOD | cross_domain | CROSS_INTERSECTION_COUNT | כמה אנשים גרים במרכז ובחרו תחביב ספורטיבי? | 4 |  |

### hobby_heavy — en

Eighteen different hobbies across sport, creative, digital, outdoor and indoor activities.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | Which type of hobby do the most people here have? | Sport |  |
| 2 | GOOD | semantic | SEMANTIC_COUNT | How many of the dishes you chose are Italian? | 6 |  |
| 3 | GOOD | semantic | SEMANTIC_COUNT | How many of you picked an outdoor hobby? | 3 |  |
| 4 | ACCEPTABLE | direct | DIRECT_CHOICE | Which music style is the most popular here? | Pop | Simple lookup or listed choice. |
| 5 | ACCEPTABLE | direct | DIRECT_UNIQUE | Who is the only player whose city is "Petah Tikva"? | Eitan | Simple lookup or listed choice. |
| 6 | ACCEPTABLE | direct | DIRECT_MAJORITY | What is the most common favorite food in this group? | Pizza | Simple lookup or listed choice. |
| 7 | GOOD | geographic | GEO_REGION_MAJORITY | In which region of Israel do the most of you live? | The center |  |
| 8 | ACCEPTABLE | direct | DIRECT_COUNT | How many players have "Hummus" as their favorite food? | 2 | Simple lookup or listed choice. |
| 9 | GOOD | geographic | GEO_EXTREME | Which of you lives in the northernmost town? | Shira |  |
| 10 | ACCEPTABLE | direct | DIRECT_UNIQUE | Who is the only player whose hobby is "Photography"? | Maya | Simple lookup or listed choice. |
| 11 | ACCEPTABLE | direct | DIRECT_COUNT | How many players have "Falafel" as their favorite food? | 2 | Simple lookup or listed choice. |
| 12 | GOOD | semantic | SEMANTIC_UNIQUE | Only one person in our group chose a cooking or baking hobby. Who? | Hila |  |
| 13 | GOOD | semantic | SEMANTIC_COMPARISON | Based on your food choices, which leads — Italian or Asian food? | Italian |  |
| 14 | GOOD | semantic | SEMANTIC_COMPARISON | What is more common here — outdoor hobbies or indoor hobbies? | Indoor hobbies |  |
| 15 | ACCEPTABLE | direct | DIRECT_CHOICE | Only one person in our group chose classical music. Who? | Nadav | Simple lookup or listed choice. |
| 16 | GOOD | geographic | GEO_REGION_DIVERSITY | From how many regions of Israel does our group come? | 4 |  |
| 17 | GOOD | cross_domain | CROSS_SUBGROUP_MAJORITY | Among people who live in the center of the country, which music style is the most common? | Pop |  |
| 18 | GOOD | cross_domain | CROSS_SUBGROUP_COMPARISON | Among people who live in the center of the country, which is more popular — Italian or Asian food? | Asian |  |
| 19 | GOOD | cross_domain | CROSS_INTERSECTION_COUNT | How many people live in the center of the country and chose a creative hobby? | 2 |  |
| 20 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_MAJORITY | Among people who live in the center of the country, which type of hobby is the most common? | Sport | Repeats a family already asked in this game. |

### food_heavy — he

Italian, Asian, Middle Eastern, American and other cuisines, all recognized.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | איזה סוג תחביב יש להכי הרבה אנשים כאן? | ספורט |  |
| 2 | GOOD | semantic | SEMANTIC_COUNT | כמה מהמאכלים שבחרתם הם מהמטבח המזרח תיכוני? | 3 |  |
| 3 | GOOD | semantic | SEMANTIC_COUNT | לכמה מכם יש תחביב שעושים בחוץ? | 3 |  |
| 4 | ACCEPTABLE | direct | DIRECT_CHOICE | איזה סגנון מוזיקה הכי פופולרי כאן? | פופ | Simple lookup or listed choice. |
| 5 | ACCEPTABLE | direct | DIRECT_AGE | מי המבוגר ביותר מבין המשתתפים ששיתפו את הגיל שלהם? | תמר | Simple lookup or listed choice. |
| 6 | ACCEPTABLE | direct | DIRECT_UNIQUE | מי היחיד/ה שגר/ה ב"חיפה"? | דנה | Simple lookup or listed choice. |
| 7 | ACCEPTABLE | direct | DIRECT_MAJORITY | איזה אוכל אהוב נבחר הכי הרבה בקבוצה? | פיצה | Simple lookup or listed choice. |
| 8 | GOOD | geographic | GEO_REGION_MAJORITY | באיזה אזור בארץ גרים הכי הרבה מכם? | המרכז |  |
| 9 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה אנשים בקבוצה בחרו מוזיקה מזרחית? | 4 | Simple lookup or listed choice. |
| 10 | GOOD | geographic | GEO_REGION_COUNT | כמה מכם מגיעים מהדרום? | 4 |  |
| 11 | GOOD | semantic | SEMANTIC_UNIQUE | רק אדם אחד בקבוצה בחר תחביב דיגיטלי. מי זה? | עמית |  |
| 12 | GOOD | semantic | SEMANTIC_COMPARISON | לפי המאכלים שבחרתם, מה מוביל — אוכל איטלקי או אסייתי? | איטלקי |  |
| 13 | GOOD | semantic | SEMANTIC_COMPARISON | מה נפוץ יותר כאן — תחביבי חוץ או תחביבי בית? | תחביבי בית |  |
| 14 | GOOD | semantic | SEMANTIC_UNIQUE | מי היחיד/ה בקבוצה שבחר/ה מאכל צפון אפריקאי? | איתן |  |
| 15 | GOOD | geographic | GEO_CLOSEST_PAIR | אילו שניים מכם גרים הכי קרוב זה לזה? | עומר + יעל |  |
| 16 | GOOD | geographic | GEO_REGION_DIVERSITY | מכמה אזורים בארץ מגיעים חברי הקבוצה? | 4 |  |
| 17 | GOOD | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שגרים בדרום, איזה סגנון מוזיקה הכי נפוץ? | פופ |  |
| 18 | GOOD | cross_domain | CROSS_SUBGROUP_COMPARISON | מבין מי שבחרו אוכל איטלקי, מה יותר נפוץ — תחביבי ספורט או תחביבי יצירה? | תחביבי ספורט |  |
| 19 | GOOD | cross_domain | CROSS_INTERSECTION_COUNT | כמה אנשים בחרו גם מאכל אסייתי וגם תחביב יצירתי? | 2 |  |
| 20 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שבחרו מוזיקת פופ, איזה סוג תחביב הכי נפוץ? | ספורט | Repeats a family already asked in this game. |

### geo_heavy — he

A clear northern majority, with the center, the south and Jerusalem also represented.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | איזה סוג תחביב יש להכי הרבה אנשים כאן? | ספורט |  |
| 2 | GOOD | semantic | SEMANTIC_COUNT | כמה מהסרטים שבחרתם הם דרמות? | 6 |  |
| 3 | GOOD | semantic | SEMANTIC_MAJORITY | לפי המאכלים שבחרתם, איזה מטבח הכי פופולרי בקבוצה? | איטלקי |  |
| 4 | ACCEPTABLE | direct | DIRECT_CHOICE | איזה סגנון מוזיקה הכי פופולרי כאן? | פופ | Simple lookup or listed choice. |
| 5 | ACCEPTABLE | direct | DIRECT_UNIQUE | מי היחיד/ה שגר/ה ב"חיפה"? | דנה | Simple lookup or listed choice. |
| 6 | ACCEPTABLE | direct | DIRECT_MAJORITY | איזה אוכל אהוב נבחר הכי הרבה בקבוצה? | פיצה | Simple lookup or listed choice. |
| 7 | ACCEPTABLE | direct | DIRECT_UNIQUE | מי היחיד/ה שהתחביב שלו/ה הוא "שחייה"? | ליאור | Simple lookup or listed choice. |
| 8 | GOOD | semantic | SEMANTIC_MAJORITY | איזה ז׳אנר חוזר הכי הרבה בסרטים שבחרתם? | קומדיה |  |
| 9 | GOOD | geographic | GEO_REGION_MAJORITY | רוב הקבוצה גרה באותו אזור. באיזה? | הצפון |  |
| 10 | GOOD | semantic | SEMANTIC_UNIQUE | רק אדם אחד בקבוצה בחר מאכל מקסיקני. מי זה? | תמר |  |
| 11 | GOOD | semantic | SEMANTIC_COMPARISON | אם מסתכלים על בחירות הסרטים, איזה צד מנצח — הרפתקאות או מתח? | הרפתקאות |  |
| 12 | GOOD | semantic | SEMANTIC_UNIQUE | רק אדם אחד בקבוצה בחר תחביב של משחקי שולחן או חידות. מי זה? | דניאל |  |
| 13 | GOOD | semantic | SEMANTIC_DIVERSITY | כמה מטבחים שונים מיוצגים בבחירות האוכל שלכם? | 5 |  |
| 14 | GOOD | geographic | GEO_CLOSEST_PAIR | אילו שניים מכם גרים הכי קרוב זה לזה? | יונתן + תמר |  |
| 15 | ACCEPTABLE | semantic | SEMANTIC_MINORITY | מבין הז׳אנרים האלה, איזה מופיע הכי מעט בסרטים שבחרתם? | מחזמר | Scoped “of these” question. |
| 16 | GOOD | geographic | GEO_REGION_COMPARISON | מאיפה מגיעים יותר מכם — מהמרכז או מהדרום? | המרכז |  |
| 17 | GOOD | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שבחרו מוזיקת פופ, איזה סוג תחביב הכי נפוץ? | ספורט |  |
| 18 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שגרים בצפון, איזה סגנון מוזיקה הכי נפוץ? | פופ | Repeats a family already asked in this game. |
| 19 | GOOD | cross_domain | CROSS_INTERSECTION_COUNT | כמה אנשים בחרו גם מאכל איטלקי וגם תחביב ספורטיבי? | 4 |  |
| 20 | GOOD | cross_domain | CROSS_SUBGROUP_COMPARISON | מבין מי שבחרו תחביב ספורטיבי, איזה ז׳אנר יותר נפוץ — הרפתקאות או דרמה? | דרמה |  |

### mixed_en — en

A mixed English room with artists and songs where shared.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | Which type of hobby do the most people here have? | Sport |  |
| 2 | GOOD | semantic | SEMANTIC_COUNT | How many of the dishes you chose are Italian? | 4 |  |
| 3 | GOOD | semantic | SEMANTIC_COUNT | How many of you picked an outdoor hobby? | 3 |  |
| 4 | ACCEPTABLE | direct | DIRECT_AGE | Who is oldest among the players who shared their age? | Amit | Simple lookup or listed choice. |
| 5 | ACCEPTABLE | direct | DIRECT_UNIQUE | Who is the only player whose city is "Eilat"? | Yael | Simple lookup or listed choice. |
| 6 | ACCEPTABLE | direct | DIRECT_MAJORITY | What is the most common favorite food in this group? | Pizza | Simple lookup or listed choice. |
| 7 | ACCEPTABLE | direct | DIRECT_CHOICE | Which music style is the most popular here? | Pop | Simple lookup or listed choice. |
| 8 | GOOD | geographic | GEO_REGION_MAJORITY | In which region of Israel do the most of you live? | The center |  |
| 9 | GOOD | semantic | SEMANTIC_COUNT | How many people in our group chose a comedy? | 5 |  |
| 10 | GOOD | semantic | SEMANTIC_COUNT | Among your favorite songs, how many are in the Pop style? | 2 |  |
| 11 | GOOD | semantic | SEMANTIC_COMPARISON | In your movie picks, which shows up more — Adventure or Thriller? | Adventure |  |
| 12 | GOOD | semantic | SEMANTIC_UNIQUE | Only one person chose a song in the Electronic style. Who? | Dana |  |
| 13 | ACCEPTABLE | semantic | SEMANTIC_MINORITY | Of these cuisines, which is the least common in your food choices? | American | Scoped “of these” question. |
| 14 | ACCEPTABLE | semantic | SEMANTIC_COMPARISON | Among the songs you chose, which style appears more — Rock or Electronic? | Rock | One side is a single person. |
| 15 | GOOD | geographic | GEO_CLOSEST_PAIR | Which pair of you lives the shortest distance apart? | Omer + Tamar |  |
| 16 | GOOD | semantic | SEMANTIC_UNIQUE | Only one person in our group chose a cooking or baking hobby. Who? | Tamar |  |
| 17 | GOOD | geographic | GEO_REGION_DIVERSITY | From how many regions of Israel does our group come? | 4 |  |
| 18 | GOOD | cross_domain | CROSS_SUBGROUP_MAJORITY | Among people who live in the center of the country, which type of hobby is the most common? | Arts and crafts |  |
| 19 | GOOD | cross_domain | CROSS_INTERSECTION_COUNT | How many people chose both an adventure movie and an Asian dish? | 2 |  |
| 20 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_COMPARISON | Among people who chose adventure movies, which is more common — sports hobbies or cooking and baking hobbies? | Sports hobbies | One side is a single person. |

### sparse — he

Six players, required fields only, a couple of unknown answers.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | איזה סוג תחביב יש להכי הרבה אנשים כאן? | ספורט |  |
| 2 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה אנשים בקבוצה בחרו מוזיקה מזרחית? | 1 | Simple lookup or listed choice. |
| 3 | ACCEPTABLE | semantic | SEMANTIC_COUNT | לכמה אנשים כאן יש תחביב יצירתי? | 1 | Count of one. |
| 4 | ACCEPTABLE | direct | DIRECT_UNIQUE | מי היחיד/ה שגר/ה ב"חיפה"? | דנה | Simple lookup or listed choice. |
| 5 | ACCEPTABLE | direct | DIRECT_UNIQUE | מי היחיד/ה שבחר/ה "סושי" כאוכל אהוב? | עומר | Simple lookup or listed choice. |
| 6 | GOOD | geographic | GEO_EXTREME | מי מכם גר/ה ביישוב הכי דרומי? | נועה |  |
| 7 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה מכם בחרו מוזיקת רוק כסגנון האהוב? | 1 | Simple lookup or listed choice. |
| 8 | GOOD | geographic | GEO_REGION_COUNT | כמה משתתפים כאן גרים במרכז? | 2 |  |
| 9 | ACCEPTABLE | semantic | SEMANTIC_COUNT | כמה אנשים בקבוצה בחרו תחביב של למידה או קריאה? | 1 | Count of one. |
| 10 | ACCEPTABLE | geographic | GEO_REGION_COUNT | כמה מכם מגיעים מהצפון? | 2 | Repeats a family already asked in this game. |
| 11 | ACCEPTABLE | semantic | SEMANTIC_COUNT | לכמה מכם יש תחביב שעושים בחוץ? | 1 | Count of one. |
| 12 | GOOD | geographic | GEO_CLOSEST_PAIR | אילו שניים מכם גרים הכי קרוב זה לזה? | דנה + יעל |  |
| 13 | GOOD | semantic | SEMANTIC_UNIQUE | רק אדם אחד בקבוצה בחר תחביב דיגיטלי. מי זה? | ליאור |  |
| 14 | ACCEPTABLE | geographic | GEO_REGION_COMPARISON | מאיפה מגיעים יותר מכם — מהמרכז או מאזור ירושלים? | המרכז | One side is a single person. |
| 15 | ACCEPTABLE | semantic | SEMANTIC_DIVERSITY | כמה סוגי תחביבים שונים יש בקבוצה? | 4 | Earlier counts in this game add up to it (3 + 1 + 1 + 1 players). |
| 16 | GOOD | geographic | GEO_REGION_DIVERSITY | מכמה אזורים בארץ מגיעים חברי הקבוצה? | 4 |  |
| 17 | ACCEPTABLE | direct | DIRECT_CHOICE | איזה סגנון מוזיקה מנצח כאן — פופ או מזרחית? | פופ | Simple lookup or listed choice. |
| 18 | ACCEPTABLE | geographic | GEO_REGION_COMPARISON | מאיפה מגיעים יותר מכם — מהצפון או מהדרום? | הצפון | One side is a single person. |
| 19 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה סגנונות מוזיקה שונים מיוצגים כאן? | 3 | Simple lookup or listed choice. |
| 20 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שבחרו מוזיקת פופ, איזה סוג תחביב הכי נפוץ? | ספורט | Subgroup leader of two. |

### unknown_heavy — he

Twenty movie answers but only four are recognized; most foods are unknown too.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה אנשים בקבוצה בחרו מוזיקת פופ? | 9 | Simple lookup or listed choice. |
| 2 | ACCEPTABLE | direct | DIRECT_UNIQUE | מי היחיד/ה שגר/ה ב"תל אביב"? | עומר | Simple lookup or listed choice. |
| 3 | ACCEPTABLE | direct | DIRECT_COMPARISON | איזה משני התחביבים האלה נפוץ יותר בקבוצה? | ריצה | Simple lookup or listed choice. |
| 4 | ACCEPTABLE | direct | DIRECT_COUNT | כמה משתתפים בחרו "קבב" כאוכל האהוב עליהם? | 2 | Simple lookup or listed choice. |
| 5 | ACCEPTABLE | direct | DIRECT_MAJORITY | איזו עיר מופיעה הכי הרבה בקבוצה? | חיפה | Simple lookup or listed choice. |
| 6 | ACCEPTABLE | direct | DIRECT_UNIQUE | מי היחיד/ה שהסרט האהוב עליו/ה הוא "משהו עם זומבים"? | איתי | Simple lookup or listed choice. |
| 7 | ACCEPTABLE | direct | DIRECT_COUNT | כמה משתתפים בחרו "ציור" כתחביב? | 2 | Simple lookup or listed choice. |
| 8 | GOOD | geographic | GEO_EXTREME | מי מכם גר/ה ביישוב הכי צפוני? | איתן |  |
| 9 | GOOD | geographic | GEO_REGION_COUNT | כמה מכם מגיעים מהצפון? | 5 |  |
| 10 | ACCEPTABLE | direct | DIRECT_CHOICE | איזה סגנון מוזיקה מנצח כאן — פופ או מזרחית? | פופ | Simple lookup or listed choice. |
| 11 | GOOD | geographic | GEO_REGION_COMPARISON | מה יש יותר בקבוצה — אנשים מהצפון או מהמרכז? | המרכז |  |
| 12 | ACCEPTABLE | direct | DIRECT_CHOICE | איזה סגנון מוזיקה מנצח כאן — פופ או רוק? | פופ | Simple lookup or listed choice. |
| 13 | GOOD | geographic | GEO_OUTLIER | מי גר/ה הכי רחוק משאר הקבוצה? | רוני |  |
| 14 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה סגנונות מוזיקה שונים מיוצגים כאן? | 3 | Simple lookup or listed choice. |
| 15 | GOOD | geographic | GEO_REGION_DIVERSITY | מכמה אזורים בארץ מגיעים חברי הקבוצה? | 4 |  |
| 16 | GOOD | geographic | GEO_REGION_UNIQUE | מי היחיד/ה בקבוצה שמגיע/ה מאזור ירושלים? | שירה |  |
| 17 | ACCEPTABLE | geographic | GEO_REGION_COMPARISON | מאיפה מגיעים יותר מכם — מהצפון או מהדרום? | הצפון | Repeats a family already asked in this game. |
| 18 | GOOD | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שגרים במרכז, איזה סגנון מוזיקה הכי נפוץ? | פופ |  |
| 19 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שגרים בדרום, איזה סגנון מוזיקה הכי נפוץ? | מזרחית | Subgroup leader of two. |
| 20 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שגרים בצפון, איזה סגנון מוזיקה הכי נפוץ? | רוק | Subgroup leader of two. |

### consent_restricted — he

Many players withheld one or two fields from questions.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | איזה סוג תחביב יש להכי הרבה אנשים כאן? | ספורט |  |
| 2 | GOOD | semantic | SEMANTIC_COUNT | כמה אנשים בקבוצה בחרו סרט מתח? | 4 |  |
| 3 | GOOD | semantic | SEMANTIC_MAJORITY | לפי המאכלים שבחרתם, איזה מטבח הכי פופולרי בקבוצה? | איטלקי |  |
| 4 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה אנשים בקבוצה בחרו מוזיקה מזרחית? | 2 | Simple lookup or listed choice. |
| 5 | GOOD | geographic | GEO_REGION_MAJORITY | באיזה אזור בארץ גרים הכי הרבה מכם? | המרכז |  |
| 6 | GOOD | semantic | SEMANTIC_COUNT | כמה אנשים בקבוצה בחרו מאכל אסייתי? | 2 |  |
| 7 | GOOD | geographic | GEO_EXTREME | מי מכם גר/ה ביישוב הכי צפוני? | רוני |  |
| 8 | GOOD | semantic | SEMANTIC_UNIQUE | מי היחיד/ה בקבוצה שבחר/ה מאכל אמריקאי? | מאיה |  |
| 9 | GOOD | semantic | SEMANTIC_COMPARISON | מה יש יותר בקבוצה — תחביבים עם פעילות גופנית או תחביבים בלי מאמץ גופני? | תחביבים עם פעילות גופנית |  |
| 10 | GOOD | semantic | SEMANTIC_UNIQUE | רק אדם אחד בקבוצה בחר סרט אימה. מי זה? | נועה |  |
| 11 | GOOD | semantic | SEMANTIC_DIVERSITY | כמה מטבחים שונים מיוצגים בבחירות האוכל שלכם? | 4 |  |
| 12 | GOOD | geographic | GEO_CLOSEST_PAIR | אילו שניים מכם גרים הכי קרוב זה לזה? | עומר + נועה |  |
| 13 | GOOD | semantic | SEMANTIC_COMPARISON | לפי הסרטים שבחרתם, מה מוביל — משפחה או מתח? | מתח |  |
| 14 | GOOD | geographic | GEO_OUTLIER | מי גר/ה הכי רחוק משאר הקבוצה? | רוני |  |
| 15 | ACCEPTABLE | semantic | SEMANTIC_DISTRIBUTION | מבין הז׳אנרים האלה, איזה מופיע הכי הרבה בסרטים שבחרתם? | הרפתקאות | Scoped “of these” question. |
| 16 | ACCEPTABLE | direct | DIRECT_CHOICE | איזה סגנון מוזיקה מנצח כאן — פופ או רוק? | פופ | Simple lookup or listed choice. |
| 17 | ACCEPTABLE | cross_domain | CROSS_INTERSECTION_COUNT | כמה אנשים בחרו גם מוזיקה מזרחית וגם תחביב ספורטיבי? | 1 | Count of one. |
| 18 | GOOD | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שגרים במרכז, איזה סגנון מוזיקה הכי נפוץ? | רוק |  |
| 19 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_COMPARISON | מבין מי שבחרו תחביב ספורטיבי, איזה ז׳אנר יותר נפוץ — פעולה או הרפתקאות? | הרפתקאות | One side is a single person. |
| 20 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שבחרו מוזיקת רוק, איזה סוג תחביב הכי נפוץ? | ספורט | Subgroup leader of two. |
