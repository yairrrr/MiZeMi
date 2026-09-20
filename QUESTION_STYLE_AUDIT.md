# Question style audit

Reviewed on 2026-09-20, after the variety change ([QUESTION_VARIETY_REPORT.md](QUESTION_VARIETY_REPORT.md)) and the earlier category-first change ([QUESTION_ENGINE_DIAGNOSTIC.md](QUESTION_ENGINE_DIAGNOSTIC.md)). Ten complete games — 188 questions — were generated from ten realistic synthetic rooms, each in its own language, and every question, option set and explanation was read. The two thin rooms return 14 questions instead of 20 because repeating an idea is not allowed to fill a game. A second audit of 395 questions from twenty other rooms is in the variety report. Names and answers are fictional.

- Rooms: [backend/tests/fixtures/rooms.py](backend/tests/fixtures/rooms.py) — Hebrew rich room, English rich room, movie-heavy, hobby-heavy, food-heavy, geography-heavy, mixed English room with artists and songs, sparse room, unknown-heavy room and consent-restricted room.
- Games: [scripts/knowledge/group-games.json](scripts/knowledge/group-games.json), reproduced by `.venv/bin/python scripts/audit_group_questions.py`. It contains every profile answer (with withheld fields), question, option, correct answer, explanation and the internal family, kind and domain. Reviewed artifact SHA-256: `a946f3d9785f328a134800d80c38bfdc844d5a60df8e63da06374ef0a3681193`.
- Automated wording checks cover many more games: `test_scenario_11_hundreds_of_hebrew_questions_use_plain_spoken_hebrew` scans 600 Hebrew questions for implementation vocabulary, unformatted placeholders, raw English choice values and a singular subject with a plural verb; `test_scenario_12_hebrew_and_english_games_ask_the_same_facts` proves the two languages select identical facts and answers in all ten rooms; `test_no_question_is_answered_by_one_shown_before_it` replays every final game in presentation order and fails if an earlier question or its explanation already settles a later count, comparison or ranking.

## Criteria

- **GOOD** — a clear, objective discovery about these participants in natural spoken language: a group count, majority, comparison or unique member derived from their answers; a regional or distance fact; a simple cross-domain subgroup fact.
- **ACCEPTABLE** — correct and clear, but less of a discovery: a literal lookup ("who is the only one who chose shawarma?"), a listed-choice fact that no grouping changed, a scoped “of these…” question, a comparison where one side is a single person, a count of one, a subgroup led by two people, or a repeat of a geography or cross-domain family already asked in the same game.
- **BAD** — general-knowledge trivia, an unsupported inference about people, ambiguity or a hidden tie, a misleading group claim, implementation vocabulary, a grammar error, unclear wording, or a question that an earlier question (or its explanation) in the same game already answers. Every BAD pattern found was fixed in the engine and the games were regenerated.

## Outcome

**139 GOOD · 49 ACCEPTABLE · 0 BAD.**

| Room | Language | Players | Questions | Semantic | Geographic | Cross-domain | Social | Direct | GOOD | ACCEPTABLE | BAD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| he_rich | he | 20 | 20 | 12 | 4 | 3 | 0 | 1 | 17 | 3 | 0 |
| en_rich | en | 20 | 20 | 12 | 4 | 3 | 0 | 1 | 17 | 3 | 0 |
| movie_heavy | he | 16 | 20 | 10 | 5 | 3 | 0 | 2 | 15 | 5 | 0 |
| hobby_heavy | en | 18 | 20 | 7 | 5 | 3 | 0 | 5 | 15 | 5 | 0 |
| food_heavy | he | 18 | 20 | 11 | 4 | 2 | 0 | 3 | 14 | 6 | 0 |
| geo_heavy | he | 15 | 20 | 12 | 3 | 3 | 0 | 2 | 15 | 5 | 0 |
| mixed_en | en | 12 | 20 | 10 | 4 | 4 | 0 | 2 | 15 | 5 | 0 |
| sparse | he | 6 | 14 | 4 | 5 | 1 | 0 | 4 | 9 | 5 | 0 |
| unknown_heavy | he | 20 | 14 | 1 | 6 | 0 | 0 | 7 | 7 | 7 | 0 |
| consent_restricted | he | 14 | 20 | 11 | 3 | 4 | 0 | 2 | 15 | 5 | 0 |

The sparse and unknown-heavy rooms have the most ACCEPTABLE questions, as designed: six players, or twenty players whose films and dishes are mostly unrecognized, leave little to discover, so the engine fills the game with valid literal and geographic questions instead of inventing group claims. The unknown-heavy room gets **no** movie or cuisine claims at all. A room that cannot support the requested length without a question an earlier one already answers gets a shorter game instead: all ten audit games still have 20 questions, and 7 of 300 randomized rooms (5–7 players, or 16 players with about 20 valid candidates) end at 13–19.

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
| “איזה ז׳אנר מוזיקה הכי נפוץ בין האמנים?”, “אם מסתכלים על השירים, איזה סגנון מוביל?” and “איזה סגנון מוזיקה הכי פופולרי?” in one game | Three questions about one subject: the group's music taste. | Music style, favourite artist and favourite song are one subject with one budget, and one reasoning pattern per subject. |
| “רק אדם אחד בחר מוזיקה קלאסית. מי?” next to “רק אדם אחד בחר מוזיקת רוק. מי?” | Different wording, same question. | Every candidate carries a semantic signature; the same reasoning on the same dimension is never asked twice. |
| “מבין הז׳אנרים האלה, איזה מופיע הכי הרבה?” next to “…הכי מעט?”; “במה אתם הכי מסכימים?” next to “במה אתם הכי שונים?” | Mirrored questions over the same list read as one question. | Mirrored patterns share one reasoning class, capped like any other. |
| “ליאור בחר/ה את קולדפליי. מי עוד בחר/ה אמן מאותו סגנון?” next to “ליאור בחר/ה את קולדפליי כאמן אהוב. מי בחר/ה שיר שלו?” | The same person's same answer anchoring two questions. | One question per anchoring answer, and the three “who else?” shapes share one class. |
| “כמה משתתפים גרים ב״תל אביב״?” (15 of 15) | A count whose answer is everyone is not a question. | Raw counts covering every shared answer are dropped; unanimity has its own family. |
| “כמה אנשים בחרו שיר בסגנון אר אנד בי?” (1) | A count of one is the weaker half of “who is the only one?”. | Counts need two people; the unique-member family asks who. |
| “באיזה אזור בארץ גרים הכי הרבה מכם?” (המרכז), later “מאיפה מגיעים יותר מכם — מהמרכז או מהדרום?”; “איזה סוג תחביב יש להכי הרבה אנשים כאן?” whose explanation names אמנות ויצירה second, later “מבין סוגי התחביבים האלה, איזה הכי נפוץ?” (אמנות ויצירה) | The later question was already answered. With the check disabled, all 12 fixture games had one (38 questions), and 290 of 300 randomized rooms. The same held for raw answers (“איזו עיר מופיעה הכי הרבה?” then “באיזו משתי הערים האלה…?”), subgroups (“מבין מי שגרים במרכז… איטלקי או אסייתי?” explaining “4 בחרו אוכל איטלקי”, then “כמה גרים במרכז ובחרו מאכל איטלקי?”) and counts of one (“only one chose American food”, then “which cuisine is least common?”). | Every counting or ranking family declares what it discloses and what would settle it; the selector, knowing games run easy to hard, never picks a question an earlier one settles and prefers the fact that settles the other when it reasons at least as deeply. Fixture games: 0. Randomized rooms: 0 of 300; seven of them are shorter games (13–19 questions) rather than include one. |
| “9 אנשים גרים במרכז — יותר מכל אזור אחר. במקום השני: הצפון (4).” with the south also at 4 | A hidden tie presented as a ranking (6 of 26 named runners-up). | A runner-up is named only when it leads third place by more than the number of unrecognized answers. |
| “צעצוע של סיפור״ ו״מוצאים את נמו״ שייכים לאותה סדרת סרטים” (also “Finding Nemo” and “The Dark Knight”) | False: the shared reference "series" is a studio catalogue (Pixar films, Disney films) or a critics' list, not a film series. | Two films must also share a distinctive title word in one of the game languages before they are called one series. |
| “אדם אחד בחרו גם מוזיקה מזרחית וגם תחביב ספורטיבי” | Grammar: a singular subject with a plural verb (also “One person live in…”). | Intersection explanations use singular verbs for one person; the Hebrew scan rejects the pattern. |
| “Among people who chose pop music, which type of hobby…?” (sport) and “among people with a sports hobby, which music style…?” (pop) in one game | The same two people, asked from both sides. | Subgroup leaders and intersection counts about the same two categories share one membership signature. |

Earlier rejected patterns remain rejected: entity trivia (“באיזה עשור יצא המסור?”), person similarity (“מי הכי דומה לדני?”), inferred listening (“למי בטוח יש עומר אדם בפלייליסט?”) and implementation vocabulary (“מי בחר ערך נדיר בשדה X?”).

## Complete-game review

### he_rich — he

Hebrew classroom: realistic spellings, a few unknown or skipped answers and consent choices.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | איזה סוג תחביב יש להכי הרבה אנשים כאן? | ספורט |  |
| 2 | GOOD | semantic | SEMANTIC_MAJORITY | רוב הגילים ששיתפתם נמצאים בטווח אחד. איזה? | 16–18 |  |
| 3 | GOOD | semantic | SEMANTIC_COUNT | כמה מהמאכלים שבחרתם הם מהמטבח האיטלקי? | 6 |  |
| 4 | GOOD | geographic | GEO_REGION_MAJORITY | באיזה אזור בארץ גרים הכי הרבה מכם? | המרכז |  |
| 5 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה מכם בחרו מוזיקת רוק כסגנון האהוב? | 3 | Fact about a listed choice that no grouping changed. |
| 6 | GOOD | geographic | GEO_EXTREME | מי מכם גר/ה ביישוב הכי צפוני? | ליאור |  |
| 7 | GOOD | semantic | SEMANTIC_COUNT | מבין בחירות הסרטים שזוהו, כמה אנשים בחרו סרט הרפתקאות? | 7 |  |
| 8 | GOOD | semantic | SEMANTIC_PARTNER | שירה בחר/ה בישול. מי עוד בחר/ה תחביב מאותו סוג? | גל |  |
| 9 | GOOD | semantic | SEMANTIC_COMPARISON | אם מסתכלים על בחירות הסרטים, איזה צד מנצח — הרפתקאות או פשע? | הרפתקאות |  |
| 10 | GOOD | semantic | SEMANTIC_UNIQUE | רק אדם אחד בחר אמן שמזוהה עם מוזיקת רוק. מי זה? | מאיה |  |
| 11 | GOOD | semantic | SEMANTIC_DIVERSITY | כמה סגנונות מוזיקה שונים מיוצגים כאן? | 5 |  |
| 12 | GOOD | geographic | GEO_OUTLIER | מי גר/ה הכי רחוק משאר הקבוצה? | יונתן |  |
| 13 | ACCEPTABLE | semantic | SEMANTIC_DISTRIBUTION | מבין סגנונות המוזיקה האלה, איזה נבחר הכי הרבה? | מזרחית | Scoped “of these” question. |
| 14 | GOOD | semantic | SEMANTIC_UNIQUE | מי היחיד/ה בקבוצה שבחר/ה תחביב של למידה או קריאה? | תמר |  |
| 15 | GOOD | geographic | GEO_REGION_DIVERSITY | מכמה אזורים בארץ מגיעים חברי הקבוצה? | 4 |  |
| 16 | GOOD | semantic | SEMANTIC_COMPARISON | לפי הבחירות שלכם, מה מוביל — פופ או אלקטרונית? | פופ |  |
| 17 | GOOD | semantic | SEMANTIC_COMPARISON | לפי המאכלים שבחרתם, מה מוביל — אוכל איטלקי או אמריקאי? | איטלקי |  |
| 18 | GOOD | cross_domain | CROSS_INTERSECTION_COUNT | כמה אנשים בחרו גם סרט הרפתקאות וגם תחביב ספורטיבי? | 3 |  |
| 19 | GOOD | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שגרים במרכז, איזה סגנון מוזיקה הכי נפוץ? | פופ |  |
| 20 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_COMPARISON | מבין מי שבחרו אוכל איטלקי, מה יותר נפוץ — תחביבי ספורט או תחביבי יצירה? | תחביבי ספורט | One side is a single person. |

### en_rich — en

English classroom with the same realistic gaps as he_rich.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | Which type of hobby do the most people here have? | Sport |  |
| 2 | GOOD | semantic | SEMANTIC_MAJORITY | Most of the shared ages fall in one range. Which? | 25–34 |  |
| 3 | GOOD | semantic | SEMANTIC_COUNT | How many of you picked electronic music as your favorite style? | 3 |  |
| 4 | GOOD | geographic | GEO_EXTREME | Which of you lives in the northernmost town? | Lior |  |
| 5 | GOOD | semantic | SEMANTIC_COUNT | How many people in our group chose an Asian dish? | 5 |  |
| 6 | GOOD | semantic | SEMANTIC_MAJORITY | Which genre shows up most in the movies you chose? | Adventure |  |
| 7 | GOOD | semantic | SEMANTIC_COUNT | Among the movie choices we recognized, how many people chose a comedy? | 6 |  |
| 8 | GOOD | semantic | SEMANTIC_PARTNER | Shira chose Cooking. Who else picked a hobby of the same kind? | Gal |  |
| 9 | GOOD | semantic | SEMANTIC_COMPARISON | Among your chosen movies, which genre appears more — Comedy or Crime? | Comedy |  |
| 10 | GOOD | semantic | SEMANTIC_UNIQUE | Only one person chose an artist associated with country music. Who? | Omer |  |
| 11 | ACCEPTABLE | semantic | SEMANTIC_DISTRIBUTION | Of these music styles, which did the most people choose? | Rock | Scoped “of these” question. |
| 12 | GOOD | semantic | SEMANTIC_DIVERSITY | How many music genres are represented by your chosen artists? | 4 |  |
| 13 | GOOD | geographic | GEO_OUTLIER | Who lives furthest from the rest of the group? | Jonathan |  |
| 14 | GOOD | semantic | SEMANTIC_UNIQUE | Only one person in our group chose a board game or puzzle hobby. Who? | Eitan |  |
| 15 | GOOD | geographic | GEO_REGION_DIVERSITY | From how many regions of Israel does our group come? | 4 |  |
| 16 | ACCEPTABLE | direct | DIRECT_CHOICE | Are there more Pop fans or Hip-hop fans in our group? | Pop | Fact about a listed choice that no grouping changed. |
| 17 | GOOD | geographic | GEO_REGION_COMPARISON | Are there more people from the south or from the Jerusalem area in our group? | The south |  |
| 18 | GOOD | cross_domain | CROSS_INTERSECTION_COUNT | How many people chose both an adventure movie and a sports hobby? | 4 |  |
| 19 | GOOD | cross_domain | CROSS_SUBGROUP_MAJORITY | Among people who chose Italian food, which region do the most come from? | The north |  |
| 20 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_COMPARISON | Among people who chose Asian food, which is more common — creative hobbies or cooking and baking hobbies? | Cooking and baking hobbies | One side is a single person. |

### movie_heavy — he

Sixteen recognized movies spanning horror, science fiction, animation, comedy and romance.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | רוב הגילים ששיתפתם נמצאים בטווח אחד. איזה? | 16–18 |  |
| 2 | GOOD | semantic | SEMANTIC_COUNT | לכמה מכם יש תחביב שדורש פעילות גופנית? | 8 |  |
| 3 | GOOD | geographic | GEO_REGION_MAJORITY | רוב הקבוצה גרה באותו אזור. באיזה? | המרכז |  |
| 4 | GOOD | semantic | SEMANTIC_COUNT | מבין בחירות הסרטים שזוהו, כמה אנשים בחרו קומדיה? | 7 |  |
| 5 | GOOD | geographic | GEO_EXTREME | מי מכם גר/ה ביישוב הכי צפוני? | תמר |  |
| 6 | GOOD | semantic | SOCIAL_TWINS | איזה שניים מכם יצאו הכי דומים בבחירות? | עמית + איתי |  |
| 7 | GOOD | semantic | SEMANTIC_PARTNER | יעל בחר/ה המבורגר. מי עוד בחר/ה מאכל מאותו מטבח? | אורי |  |
| 8 | GOOD | semantic | SEMANTIC_COMPARISON | לפי הסרטים שבחרתם, מה מוביל — קומדיה או מתח? | קומדיה |  |
| 9 | GOOD | semantic | SEMANTIC_UNIQUE | רק אדם אחד בקבוצה בחר תחביב של בישול או אפייה. מי זה? | יונתן |  |
| 10 | GOOD | semantic | SEMANTIC_DIVERSITY | כמה מטבחים שונים מיוצגים בבחירות האוכל שלכם? | 6 |  |
| 11 | GOOD | geographic | GEO_OUTLIER | מי גר/ה הכי רחוק משאר הקבוצה? | איתן |  |
| 12 | ACCEPTABLE | semantic | SEMANTIC_DISTRIBUTION | מבין המטבחים האלה, איזה הכי נפוץ בבחירות האוכל שלכם? | אסייתי | Scoped “of these” question. |
| 13 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה סגנונות מוזיקה שונים מיוצגים כאן? | 5 | Fact about a listed choice that no grouping changed. |
| 14 | ACCEPTABLE | semantic | SEMANTIC_DISTRIBUTION | מבין סוגי התחביבים האלה, איזה הכי נפוץ בקבוצה? | אמנות ויצירה | Scoped “of these” question. |
| 15 | GOOD | geographic | GEO_REGION_COMPARISON | מאיפה מגיעים יותר מכם — מהצפון או מהדרום? | הדרום |  |
| 16 | ACCEPTABLE | direct | DIRECT_CHOICE | מבין סגנונות המוזיקה האלה, איזה נבחר הכי הרבה? | מזרחית | Fact about a listed choice that no grouping changed. |
| 17 | GOOD | geographic | GEO_REGION_DIVERSITY | מכמה אזורים בארץ מגיעים חברי הקבוצה? | 4 |  |
| 18 | GOOD | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שגרים במרכז, איזה סגנון מוזיקה הכי נפוץ? | פופ |  |
| 19 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_COMPARISON | מבין מי שבחרו מוזיקת פופ, מה יותר נפוץ — תחביבי יצירה או תחביבים דיגיטליים? | תחביבי יצירה | One side is a single person. |
| 20 | GOOD | cross_domain | CROSS_INTERSECTION_COUNT | כמה אנשים בחרו גם סרט הרפתקאות וגם מאכל איטלקי? | 3 |  |

### hobby_heavy — en

Eighteen different hobbies across sport, creative, digital, outdoor and indoor activities.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | Which type of hobby do the most people here have? | Sport |  |
| 2 | GOOD | semantic | SEMANTIC_COUNT | How many of the dishes you chose are Italian? | 6 |  |
| 3 | GOOD | geographic | GEO_REGION_MAJORITY | In which region of Israel do the most of you live? | The center |  |
| 4 | GOOD | semantic | SEMANTIC_COUNT | How many of you picked an outdoor hobby? | 3 |  |
| 5 | GOOD | geographic | GEO_EXTREME | Which of you lives in the northernmost town? | Shira |  |
| 6 | ACCEPTABLE | direct | DIRECT_CHOICE | How many of you picked electronic music as your favorite style? | 2 | Fact about a listed choice that no grouping changed. |
| 7 | GOOD | semantic | SEMANTIC_COUNT | How many of you picked a rice dish? | 3 |  |
| 8 | ACCEPTABLE | direct | DIRECT_MAJORITY | What is the most common favorite food in this group? | Pizza | Simple lookup of a raw answer. |
| 9 | ACCEPTABLE | direct | DIRECT_COUNT | How many players have "Hummus" as their favorite food? | 2 | Simple lookup of a raw answer. |
| 10 | GOOD | semantic | SEMANTIC_UNIQUE | Only one person in our group chose a relaxation hobby. Who? | Nadav |  |
| 11 | GOOD | semantic | SEMANTIC_COMPARISON | Based on your food choices, which leads — Italian or Asian food? | Italian |  |
| 12 | GOOD | geographic | GEO_OUTLIER | Who lives furthest from the rest of the group? | Amit |  |
| 13 | ACCEPTABLE | direct | DIRECT_CHOICE | Of these music styles, which did the most people choose? | Rock | Fact about a listed choice that no grouping changed. |
| 14 | GOOD | geographic | GEO_REGION_DIVERSITY | From how many regions of Israel does our group come? | 4 |  |
| 15 | GOOD | semantic | SEMANTIC_COMPARISON | What is more common here — outdoor hobbies or indoor hobbies? | Indoor hobbies |  |
| 16 | GOOD | geographic | GEO_REGION_UNIQUE | Who is the only one here from the Jerusalem area? | Yael |  |
| 17 | ACCEPTABLE | direct | DIRECT_CHOICE | Which music style wins here — Pop or Mizrahi? | Pop | Fact about a listed choice that no grouping changed. |
| 18 | GOOD | cross_domain | CROSS_INTERSECTION_PERSON | Who here chose both electronic music and a sports hobby? | Amit |  |
| 19 | GOOD | cross_domain | CROSS_SUBGROUP_COMPARISON | Among people who live in the center of the country, which is more popular — Asian or Middle Eastern food? | Middle Eastern |  |
| 20 | GOOD | cross_domain | CROSS_SUBGROUP_MAJORITY | Among people who chose pop music, which type of hobby is the most common? | Sport |  |

### food_heavy — he

Italian, Asian, Middle Eastern, American and other cuisines, all recognized.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | רוב הגילים ששיתפתם נמצאים בטווח אחד. איזה? | 25–34 |  |
| 2 | GOOD | semantic | SEMANTIC_COUNT | לכמה מכם יש תחביב שדורש פעילות גופנית? | 8 |  |
| 3 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה אנשים בקבוצה בחרו מוזיקה מזרחית? | 4 | Fact about a listed choice that no grouping changed. |
| 4 | GOOD | geographic | GEO_REGION_COUNT | כמה מכם מגיעים מהדרום? | 4 |  |
| 5 | GOOD | semantic | SEMANTIC_COUNT | כמה מהמאכלים שבחרתם הם מהמטבח המזרח תיכוני? | 3 |  |
| 6 | GOOD | geographic | GEO_REGION_MAJORITY | באיזה אזור בארץ גרים הכי הרבה מכם? | המרכז |  |
| 7 | GOOD | semantic | SEMANTIC_PARTNER | שירה בחר/ה המבורגר. מי עוד בחר/ה מאכל מאותו מטבח? | דניאל |  |
| 8 | GOOD | semantic | SEMANTIC_PARTNER | תמר בחר/ה בישול. מי עוד בחר/ה תחביב מאותו סוג? | מיכל |  |
| 9 | GOOD | semantic | SEMANTIC_UNIQUE | מי היחיד/ה בקבוצה שבחר/ה מאכל צפון אפריקאי? | איתן |  |
| 10 | GOOD | geographic | GEO_CLOSEST_PAIR | אילו שניים מכם גרים הכי קרוב זה לזה? | עומר + יעל |  |
| 11 | ACCEPTABLE | semantic | SEMANTIC_DISTRIBUTION | מבין המטבחים האלה, איזה הכי נפוץ בבחירות האוכל שלכם? | אסייתי | Scoped “of these” question. |
| 12 | GOOD | geographic | GEO_REGION_DIVERSITY | מכמה אזורים בארץ מגיעים חברי הקבוצה? | 4 |  |
| 13 | GOOD | semantic | SEMANTIC_COMPARISON | איזה מטבח מנצח בבחירות האוכל שלכם — האיטלקי או המזרח תיכוני? | איטלקי |  |
| 14 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה סגנונות מוזיקה שונים מיוצגים כאן? | 5 | Fact about a listed choice that no grouping changed. |
| 15 | ACCEPTABLE | semantic | SEMANTIC_DISTRIBUTION | מבין סוגי התחביבים האלה, איזה הכי נפוץ בקבוצה? | אמנות ויצירה | Scoped “of these” question. |
| 16 | ACCEPTABLE | direct | DIRECT_CHOICE | איזה סגנון מוזיקה מנצח כאן — פופ או מזרחית? | פופ | Fact about a listed choice that no grouping changed. |
| 17 | GOOD | semantic | SEMANTIC_COMPARISON | מה נפוץ יותר כאן — תחביבי חוץ או תחביבי בית? | תחביבי בית |  |
| 18 | GOOD | semantic | SOCIAL_TYPICAL | מי מכם בחר/ה הכי הרבה מהבחירות הנפוצות בקבוצה? | דנה |  |
| 19 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_COMPARISON | מבין מי שגרים בדרום, מה יותר נפוץ — תחביבי חוץ או תחביבי בית? | תחביבי בית | One side is a single person. |
| 20 | GOOD | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שגרים במרכז, איזה סגנון מוזיקה הכי נפוץ? | פופ |  |

### geo_heavy — he

A clear northern majority, with the center, the south and Jerusalem also represented.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | איזה סוג תחביב יש להכי הרבה אנשים כאן? | ספורט |  |
| 2 | GOOD | semantic | SEMANTIC_COUNT | כמה אנשים בחרו דרמה כסרט האהוב? | 6 |  |
| 3 | GOOD | geographic | GEO_REGION_MAJORITY | רוב הקבוצה גרה באותו אזור. באיזה? | הצפון |  |
| 4 | GOOD | semantic | SEMANTIC_COUNT | לכמה מכם יש תחביב שעושים בחוץ? | 3 |  |
| 5 | GOOD | semantic | SEMANTIC_MAJORITY | איזה ז׳אנר חוזר הכי הרבה בסרטים שבחרתם? | קומדיה |  |
| 6 | GOOD | semantic | SEMANTIC_PARTNER | יעל בחר/ה המבורגר. מי עוד בחר/ה מאכל מאותו מטבח? | תמר |  |
| 7 | GOOD | semantic | SEMANTIC_PARTNER | נועה בחר/ה את ״מטריקס״. מי עוד בחר/ה סרט מאותו ז׳אנר? | תמר |  |
| 8 | GOOD | semantic | SEMANTIC_UNIQUE | רק אדם אחד בקבוצה בחר תחביב דיגיטלי. מי זה? | עמית |  |
| 9 | GOOD | semantic | SEMANTIC_DIVERSITY | כמה מטבחים שונים מיוצגים בבחירות האוכל שלכם? | 5 |  |
| 10 | ACCEPTABLE | semantic | SEMANTIC_MINORITY | מבין הז׳אנרים האלה, איזה מופיע הכי מעט בסרטים שבחרתם? | מחזמר | Scoped “of these” question. |
| 11 | GOOD | geographic | GEO_CLOSEST_PAIR | אילו שניים מכם גרים הכי קרוב זה לזה? | יונתן + תמר |  |
| 12 | GOOD | semantic | SEMANTIC_COMPARISON | אם מסתכלים על בחירות הסרטים, איזה צד מנצח — הרפתקאות או מתח? | הרפתקאות |  |
| 13 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה סגנונות מוזיקה שונים מיוצגים כאן? | 4 | Fact about a listed choice that no grouping changed. |
| 14 | ACCEPTABLE | semantic | SEMANTIC_DISTRIBUTION | מבין המטבחים האלה, איזה הכי נפוץ בבחירות האוכל שלכם? | מזרח תיכוני | Scoped “of these” question. |
| 15 | GOOD | geographic | GEO_REGION_DIVERSITY | מכמה אזורים בארץ מגיעים חברי הקבוצה? | 4 |  |
| 16 | ACCEPTABLE | direct | DIRECT_CHOICE | איזה סגנון מוזיקה מנצח כאן — פופ או מזרחית? | פופ | Fact about a listed choice that no grouping changed. |
| 17 | GOOD | cross_domain | CROSS_SUBGROUP_COMPARISON | מבין מי שגרים בצפון, מה יותר אהוב — אוכל אסייתי או מזרח תיכוני? | מזרח תיכוני |  |
| 18 | GOOD | semantic | SOCIAL_TYPICAL | מי מכם בחר/ה הכי הרבה מהבחירות הנפוצות בקבוצה? | אורי |  |
| 19 | GOOD | cross_domain | CROSS_INTERSECTION_COUNT | כמה אנשים בחרו גם מוזיקת פופ וגם תחביב ספורטיבי? | 4 |  |
| 20 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שגרים במרכז, איזה סגנון מוזיקה הכי נפוץ? | פופ | Subgroup leader of two. |

### mixed_en — en

A mixed English room with artists and songs where shared.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | Most of the shared ages fall in one range. Which? | 25–34 |  |
| 2 | GOOD | semantic | SEMANTIC_COUNT | How many people chose a favorite song in the Rock style? | 2 |  |
| 3 | GOOD | semantic | SEMANTIC_MAJORITY | Which type of hobby do the most people here have? | Sport |  |
| 4 | GOOD | semantic | SEMANTIC_COUNT | Among the movie choices we recognized, how many people chose a comedy? | 5 |  |
| 5 | GOOD | semantic | SEMANTIC_COUNT | How many of you picked an outdoor hobby? | 3 |  |
| 6 | GOOD | geographic | GEO_REGION_MAJORITY | In which region of Israel do the most of you live? | The center |  |
| 7 | GOOD | semantic | SOCIAL_TWINS | Which two of you turned out to be the most alike? | Omer + Maya |  |
| 8 | GOOD | semantic | SEMANTIC_COMPARISON | In your movie picks, which shows up more — Adventure or Thriller? | Adventure |  |
| 9 | GOOD | semantic | SEMANTIC_UNIQUE | Only one person in our group chose a cooking or baking hobby. Who? | Tamar |  |
| 10 | ACCEPTABLE | semantic | SEMANTIC_MINORITY | Of these cuisines, which is the least common in your food choices? | American | Scoped “of these” question. |
| 11 | GOOD | semantic | SEMANTIC_DIVERSITY | How many music genres are represented by the songs you chose? | 3 |  |
| 12 | GOOD | geographic | GEO_CLOSEST_PAIR | Which pair of you lives the shortest distance apart? | Omer + Tamar |  |
| 13 | ACCEPTABLE | direct | DIRECT_CHOICE | Of these music styles, which did the most people choose? | Rock | Fact about a listed choice that no grouping changed. |
| 14 | GOOD | geographic | GEO_OUTLIER | Who lives furthest from the rest of the group? | Yael |  |
| 15 | ACCEPTABLE | direct | DIRECT_CHOICE | Which music style wins here — Pop or Mizrahi? | Pop | Fact about a listed choice that no grouping changed. |
| 16 | GOOD | geographic | GEO_REGION_DIVERSITY | From how many regions of Israel does our group come? | 4 |  |
| 17 | GOOD | cross_domain | CROSS_INTERSECTION_PERSON | Who here chose both pop music and a creative hobby? | Maya |  |
| 18 | GOOD | cross_domain | CROSS_INTERSECTION_COUNT | How many people chose both an adventure movie and an Asian dish? | 2 |  |
| 19 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_MAJORITY | Among people who chose Asian food, which region do the most come from? | The center | Subgroup leader of two. |
| 20 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_COMPARISON | Among people who live in the south, which is more popular — Italian or Asian food? | Italian | One side is a single person. |

### sparse — he

Six players, required fields only, a couple of unknown answers.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | איזה סוג תחביב יש להכי הרבה אנשים כאן? | ספורט |  |
| 2 | GOOD | geographic | GEO_EXTREME | מי מכם גר/ה ביישוב הכי צפוני? | יעל |  |
| 3 | ACCEPTABLE | direct | DIRECT_UNIQUE | מי היחיד/ה שבחר/ה "פיצה" כאוכל אהוב? | דנה | Simple lookup of a raw answer. |
| 4 | GOOD | geographic | GEO_REGION_COUNT | כמה משתתפים כאן גרים במרכז? | 2 |  |
| 5 | GOOD | semantic | SEMANTIC_UNIQUE | רק אדם אחד בקבוצה בחר תחביב יצירתי. מי זה? | עומר |  |
| 6 | GOOD | semantic | SOCIAL_AGREEMENT | במה אתם הכי שונים זה מזה — תחביבים, מוזיקה או מקום המגורים? | מקום המגורים |  |
| 7 | GOOD | semantic | SEMANTIC_DIVERSITY | כמה סוגי תחביבים שונים יש בקבוצה? | 4 |  |
| 8 | GOOD | geographic | GEO_CLOSEST_PAIR | אילו שניים מכם גרים הכי קרוב זה לזה? | דנה + יעל |  |
| 9 | ACCEPTABLE | direct | DIRECT_CHOICE | רק אדם אחד בקבוצה בחר מוזיקה מזרחית. מי זה? | עמית | Fact about a listed choice that no grouping changed. |
| 10 | ACCEPTABLE | geographic | GEO_REGION_COMPARISON | מאיפה מגיעים יותר מכם — מהמרכז או מהדרום? | המרכז | One side is a single person. |
| 11 | ACCEPTABLE | direct | DIRECT_CHOICE | איזה סגנון מוזיקה מנצח כאן — פופ או מזרחית? | פופ | Fact about a listed choice that no grouping changed. |
| 12 | GOOD | geographic | GEO_OUTLIER | מי גר/ה הכי רחוק משאר הקבוצה? | נועה |  |
| 13 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה סגנונות מוזיקה שונים מיוצגים כאן? | 3 | Fact about a listed choice that no grouping changed. |
| 14 | GOOD | cross_domain | CROSS_INTERSECTION_COUNT | כמה אנשים בחרו גם מוזיקת פופ וגם תחביב ספורטיבי? | 2 |  |

### unknown_heavy — he

Twenty movie answers but only four are recognized; most foods are unknown too.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | geographic | GEO_REGION_MAJORITY | באיזה אזור בארץ גרים הכי הרבה מכם? | המרכז |  |
| 2 | ACCEPTABLE | direct | DIRECT_CHOICE | איזה סגנון מוזיקה הכי פופולרי כאן? | פופ | Fact about a listed choice that no grouping changed. |
| 3 | GOOD | geographic | GEO_EXTREME | מי מכם גר/ה ביישוב הכי צפוני? | איתן |  |
| 4 | GOOD | semantic | SEMANTIC_MAJORITY | רוב הגילים ששיתפתם נמצאים בטווח אחד. איזה? | 16–18 |  |
| 5 | GOOD | geographic | GEO_REGION_COUNT | כמה מכם מגיעים מהדרום? | 4 |  |
| 6 | ACCEPTABLE | direct | DIRECT_COMPARISON | איזה משני התחביבים האלה נפוץ יותר בקבוצה? | ריצה | Simple lookup of a raw answer. |
| 7 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה אנשים בקבוצה בחרו מוזיקה מזרחית? | 4 | Fact about a listed choice that no grouping changed. |
| 8 | ACCEPTABLE | direct | DIRECT_UNIQUE | מי היחיד/ה שהסרט האהוב עליו/ה הוא "המסור"? | דנה | Simple lookup of a raw answer. |
| 9 | ACCEPTABLE | direct | DIRECT_COUNT | כמה משתתפים בחרו "שניצל" כאוכל האהוב עליהם? | 2 | Simple lookup of a raw answer. |
| 10 | ACCEPTABLE | direct | DIRECT_COUNT | כמה משתתפים בחרו "גיימינג" כתחביב? | 2 | Simple lookup of a raw answer. |
| 11 | GOOD | geographic | GEO_OUTLIER | מי גר/ה הכי רחוק משאר הקבוצה? | רוני |  |
| 12 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה סגנונות מוזיקה שונים מיוצגים כאן? | 3 | Fact about a listed choice that no grouping changed. |
| 13 | GOOD | geographic | GEO_REGION_DIVERSITY | מכמה אזורים בארץ מגיעים חברי הקבוצה? | 4 |  |
| 14 | GOOD | geographic | GEO_REGION_UNIQUE | מי היחיד/ה בקבוצה שמגיע/ה מאזור ירושלים? | שירה |  |

### consent_restricted — he

Many players withheld one or two fields from questions.

| # | Rating | Kind | Family | Question | Correct answer | Note |
|---:|---|---|---|---|---|---|
| 1 | GOOD | semantic | SEMANTIC_MAJORITY | רוב הגילים ששיתפתם נמצאים בטווח אחד. איזה? | 16–18 |  |
| 2 | GOOD | semantic | SEMANTIC_COUNT | לכמה מכם יש תחביב שדורש פעילות גופנית? | 6 |  |
| 3 | GOOD | geographic | GEO_REGION_COUNT | כמה משתתפים כאן גרים במרכז? | 7 |  |
| 4 | GOOD | semantic | SEMANTIC_MAJORITY | לפי המאכלים שבחרתם, איזה מטבח הכי פופולרי בקבוצה? | איטלקי |  |
| 5 | GOOD | semantic | SOCIAL_TWINS | איזה שניים מכם יצאו הכי דומים בבחירות? | עמית + יעל |  |
| 6 | GOOD | semantic | SEMANTIC_PARTNER | רוני בחר/ה את ״פורסט גאמפ״. מי עוד בחר/ה סרט מאותו ז׳אנר? | אורי |  |
| 7 | GOOD | semantic | SEMANTIC_UNIQUE | מי היחיד/ה בקבוצה שבחר/ה מאכל אמריקאי? | מאיה |  |
| 8 | GOOD | semantic | SEMANTIC_COMPARISON | מה נפוץ יותר כאן — תחביבי חוץ או תחביבי בית? | תחביבי חוץ |  |
| 9 | ACCEPTABLE | semantic | SEMANTIC_DISTRIBUTION | מבין הז׳אנרים האלה, איזה מופיע הכי הרבה בסרטים שבחרתם? | הרפתקאות | Scoped “of these” question. |
| 10 | GOOD | semantic | SEMANTIC_DIVERSITY | כמה מטבחים שונים מיוצגים בבחירות האוכל שלכם? | 4 |  |
| 11 | GOOD | geographic | GEO_CLOSEST_PAIR | אילו שניים מכם גרים הכי קרוב זה לזה? | עומר + נועה |  |
| 12 | GOOD | semantic | SEMANTIC_COMPARISON | לפי הסרטים שבחרתם, מה מוביל — משפחה או מתח? | מתח |  |
| 13 | GOOD | geographic | GEO_REGION_DIVERSITY | מכמה אזורים בארץ מגיעים חברי הקבוצה? | 4 |  |
| 14 | ACCEPTABLE | direct | DIRECT_CHOICE | מבין סגנונות המוזיקה האלה, איזה נבחר הכי מעט? | מזרחית | Fact about a listed choice that no grouping changed. |
| 15 | ACCEPTABLE | semantic | SEMANTIC_DISTRIBUTION | מבין סוגי התחביבים האלה, איזה הכי נפוץ בקבוצה? | אמנות ויצירה | Scoped “of these” question. |
| 16 | ACCEPTABLE | direct | DIRECT_CHOICE | כמה סגנונות מוזיקה שונים מיוצגים כאן? | 3 | Fact about a listed choice that no grouping changed. |
| 17 | GOOD | cross_domain | CROSS_INTERSECTION_PERSON | מי מכם גר/ה במרכז וגם בחר/ה מאכל איטלקי? | נועה |  |
| 18 | GOOD | cross_domain | CROSS_SUBGROUP_MAJORITY | מבין מי שגרים במרכז, איזה סגנון מוזיקה הכי נפוץ? | רוק |  |
| 19 | GOOD | cross_domain | CROSS_INTERSECTION_COUNT | כמה אנשים בחרו גם סרט הרפתקאות וגם מאכל מזרח תיכוני? | 2 |  |
| 20 | ACCEPTABLE | cross_domain | CROSS_SUBGROUP_COMPARISON | מבין מי שבחרו מוזיקת פופ, מה יותר נפוץ — תחביבי ספורט או תחביבים דיגיטליים? | תחביבי ספורט | One side is a single person. |
