# Question style audit

Reviewed manually on 2026-09-14: four synthetic groups, each played as a complete 20-question game in Hebrew and English (160 questions). Names and profile choices are fictional.

Source: [group-games.json](scripts/knowledge/group-games.json). It contains every profile, question, option, correct answer and explanation. The audit script reproduces the games; it does not automatically grade their quality.

Reviewed artifact SHA-256: `7f13741c35be993e1582d7d84605c3c81ba90f16c8b81cd2c45736d7eb42bcb2`.

GOOD means a clear, objective discovery about these participants. ACCEPTABLE means a limited simple-person question, a more demanding literal group-diversity question, or one overlapping comparison/majority. BAD means trivia, an unsupported inference, ambiguity, implementation terminology or unclear wording; BAD patterns were removed/redesigned.

## Rejected and redesigned patterns

| BAD example | Why | Replacement |
|---|---|---|
| באיזה עשור יצא המסור? | Entity trivia does not reveal this group. | Count the group’s horror choices. |
| מי הכי דומה לדני? | Requires prior familiarity and an opaque similarity score. | Compare shared group tastes or a stated subgroup. |
| למי בטוח יש עומר אדם בפלייליסט? | A genre preference does not prove listening behavior. | Count genres of artists actually chosen. |
| מי בחר ערך נדיר בשדה X? | Implementation vocabulary and unclear meaning. | Name the human concept and state the unique condition. |
| How many film genres? (10 across six people) | An unwieldy taxonomy inventory. | Diversity is limited to 2–6 meaningful families. |
| Sport versus fitness as competing broad-family winners | Parent/child overlap can make both answers true. | Only comparable broad families compete. |
| Separate counts for trance and electronic, with identical holders | Repeats the same discovery through a parent label. | Suppress equivalent membership sets within a source field. |
| Treating ריצה (ספורט) as an unqualified alias for a narrower discipline | Masks the general running activity. | Keep activity qualifiers unless a synonym is reviewed. |

## Complete-game review

### new_class — he

| # | Rating | Question | Correct answer |
|---:|---|---|---|
| 1 | GOOD | איזה סגנון מוזיקה הכי נפוץ בקבוצה? | מזרחית |
| 2 | GOOD | רק אחד בקבוצה בחר מאכל שמזוהה עם המטבח היפני. מי זה? | עמית |
| 3 | GOOD | מי בקבוצה גר הכי דרומה? | ליאור |
| 4 | GOOD | לפי התחביבים שבחרתם, איזה תחום הכי נפוץ בקבוצה? | ספורט |
| 5 | ACCEPTABLE | מי המבוגר ביותר מבין המשתתפים ששיתפו את הגיל שלהם? | נועה |
| 6 | GOOD | כמה אנשים בקבוצה בחרו מאכלים שמזוהים עם המטבח האיטלקי? | 3 |
| 7 | GOOD | רק אחד בקבוצה בחר תחביב שקשור לפעילות בטבע. מי זה? | ליאור |
| 8 | GOOD | מאיזה אזור בארץ מגיע רוב הקבוצה? | המרכז |
| 9 | GOOD | כמה אנשים בקבוצה בחרו מוזיקה בסגנון אלקטרונית? | 1 |
| 10 | GOOD | כמה אנשים בקבוצה בחרו מאכלים שמזוהים עם מטבחי המזרח התיכון? | 1 |
| 11 | GOOD | לפי המאכלים שבחרתם, איזה מטבח הכי פופולרי בקבוצה? | המטבח האיטלקי |
| 12 | GOOD | כמה אזורים בארץ מיוצגים בקבוצה? | 3 |
| 13 | GOOD | אילו שני אנשים בקבוצה גרים ביישובים הקרובים ביותר זה לזה בקו אווירי? | דנה + עומר |
| 14 | GOOD | מה נפוץ יותר בקבוצה מבין ז׳אנרי הסרטים הבאים? | אימה |
| 15 | GOOD | כמה מטבחים שונים מסתתרים מאחורי המאכלים שבחרתם? | 3 |
| 16 | GOOD | מה נפוץ יותר בקבוצה מבין תחומי התחביבים הבאים? | ספורט |
| 17 | GOOD | מה נפוץ יותר בקבוצה מבין סגנונות המוזיקה הבאים? | מזרחית |
| 18 | ACCEPTABLE | אצל חובבי איזה סגנון מוזיקה יש בקבוצה את המגוון הכי רחב של סרטים אהובים? | מוזיקה מזרחית |
| 19 | GOOD | מבין מי שבחרו תחביבים שקשורים לספורט, איזה ז׳אנר קולנוע הכי נפוץ? | אימה |
| 20 | GOOD | כמה אנשים בחרו גם סרטים בז׳אנר אנימציה וגם תחביבים שקשורים לספורט? | 1 |

### new_class — en

| # | Rating | Question | Correct answer |
|---:|---|---|---|
| 1 | GOOD | Which activity family is most common in our group? | Sport |
| 2 | GOOD | Only one person in our group chose Electronic music. Who? | ליאור |
| 3 | GOOD | Whose town is furthest north in the group? | עמית |
| 4 | GOOD | Which cuisine is most popular in our group’s food choices? | Italian cuisine |
| 5 | GOOD | How many people in our group chose Action movies? | 1 |
| 6 | ACCEPTABLE | Who is oldest among the players who shared their age? | נועה |
| 7 | GOOD | Only one person in our group chose Pop music. Who? | עומר |
| 8 | GOOD | Which region is home to the majority of our group? | Central Israel |
| 9 | GOOD | How many people in our group chose Adventure movies? | 2 |
| 10 | GOOD | How many people in our group chose Crime movies? | 1 |
| 11 | GOOD | Which music style is most common in our group? | Mizrahi |
| 12 | GOOD | How many activity families are represented in our group? | 3 |
| 13 | GOOD | Which pair chose the towns that are closest by air distance? | דנה + עומר |
| 14 | GOOD | Which of these film genres is more common in our group? | Horror |
| 15 | GOOD | How many cuisines are behind our group’s food choices? | 3 |
| 16 | GOOD | What is more common in our group: outdoor hobbies or indoor hobbies? | Outdoors |
| 17 | GOOD | Which of these activity families is more common in our group? | Sport |
| 18 | ACCEPTABLE | Which shared music style connects the widest variety of favorite food choices? | Mizrahi |
| 19 | GOOD | Among people from Central Israel, which cuisine is most common? | Italian cuisine |
| 20 | GOOD | How many people chose both Mizrahi music and foods associated with Italian cuisine? | 1 |

### creative_workshop — he

| # | Rating | Question | Correct answer |
|---:|---|---|---|
| 1 | GOOD | איזה סגנון מוזיקה הכי נפוץ בקבוצה? | רוק |
| 2 | GOOD | רק אחד בקבוצה בחר מאכל ממשפחת מאפים. מי זה? | נועה |
| 3 | GOOD | מי בקבוצה גר הכי דרומה? | יעל |
| 4 | GOOD | לפי התחביבים שבחרתם, איזה תחום הכי נפוץ בקבוצה? | אמנות ויצירה |
| 5 | GOOD | כמה אנשים בקבוצה בחרו סרטים בז׳אנר אימה? | 1 |
| 6 | ACCEPTABLE | מי המבוגר ביותר מבין המשתתפים ששיתפו את הגיל שלהם? | יעל |
| 7 | GOOD | באיזו משתי הערים האלה גרים יותר אנשים בקבוצה? | חיפה |
| 8 | GOOD | איזה אוכל אהוב נבחר הכי הרבה בקבוצה? | סושי |
| 9 | ACCEPTABLE | איזו עיר מופיעה הכי הרבה בקבוצה? | חיפה |
| 10 | GOOD | איזו מהבחירות האלה של סגנון מוזיקה נמצאת במקום השני בקבוצה? | מוזיקת פופ |
| 11 | GOOD | איזה שני אנשים בחרו תחביבים שונים שמתחברים דרך ספורט? | עמית + ליאור |
| 12 | GOOD | מי גר הכי רחוק משאר הקבוצה, בממוצע? | עומר |
| 13 | GOOD | כמה מטבחים שונים מסתתרים מאחורי המאכלים שבחרתם? | 3 |
| 14 | GOOD | מה הכי פחות נפוץ בקבוצה מבין הבחירות האלה של סגנון מוזיקה? | ג'אז |
| 15 | GOOD | מה נפוץ יותר בקבוצה מבין המטבחים הבאים? | מטבחים אסייתיים |
| 16 | GOOD | מה נפוץ יותר בקבוצה מבין ז׳אנרי הסרטים הבאים? | הרפתקאות |
| 17 | GOOD | כמה אזורים בארץ מיוצגים בקבוצה? | 3 |
| 18 | GOOD | מבין מי שבחרו סרטים בז׳אנר אנימציה, איזה תחום תחביבים הכי נפוץ? | אמנות ויצירה |
| 19 | ACCEPTABLE | אצל חובבי איזה סגנון מוזיקה יש בקבוצה את המגוון הכי רחב של סרטים אהובים? | מוזיקת רוק |
| 20 | GOOD | כמה אנשים בחרו גם מאכלים שמזוהים עם המטבח האיטלקי וגם תחביבים שקשורים לאמנות ויצירה? | 1 |

### creative_workshop — en

| # | Rating | Question | Correct answer |
|---:|---|---|---|
| 1 | GOOD | Which activity family is most common in our group? | Arts and crafts |
| 2 | GOOD | Only one person in our group chose Jazz music. Who? | עמית |
| 3 | GOOD | Who is the only person from a region nobody else in our group comes from? | יעל |
| 4 | GOOD | Which music style is most common in our group? | Rock |
| 5 | GOOD | How many people in our group chose Action movies? | 1 |
| 6 | ACCEPTABLE | Who is oldest among the players who shared their age? | יעל |
| 7 | GOOD | Which of these two favorite food choices was shared by more players? | סושי |
| 8 | GOOD | Allowing for different spellings of the same place, how many different towns are represented here? | 5 |
| 9 | ACCEPTABLE | What is the most common favorite food in this group? | סושי |
| 10 | GOOD | How many people in our group chose foods associated with Asian cuisines? | 3 |
| 11 | GOOD | Which music style choice has the second-largest group? | Pop |
| 12 | GOOD | Which two people chose different foods, both in Italian cuisine? | נועה + עמית |
| 13 | GOOD | Who lives furthest from the rest of our group, on average? | עומר |
| 14 | GOOD | How many activity families are represented in our group? | 3 |
| 15 | GOOD | Which shared music style choice belongs to the smallest group? | Jazz |
| 16 | GOOD | Which of these film genres is more common in our group? | Adventure |
| 17 | GOOD | Which of these activity families is more common in our group? | Arts and crafts |
| 18 | GOOD | How many cuisines are behind our group’s food choices? | 3 |
| 19 | ACCEPTABLE | Which shared city connects the widest variety of favorite movie choices? | חיפה |
| 20 | GOOD | Among people who chose Adventure movies, which activity family is most common? | Arts and crafts |

### mixed_interests — he

| # | Rating | Question | Correct answer |
|---:|---|---|---|
| 1 | GOOD | לפי המאכלים שבחרתם, איזה מטבח הכי פופולרי בקבוצה? | המטבח האיטלקי |
| 2 | GOOD | רק אחד בקבוצה בחר מוזיקה בסגנון אלקטרונית. מי זה? | יעל |
| 3 | GOOD | מי בקבוצה גר הכי צפונה? | רוני |
| 4 | GOOD | לפי התחביבים שבחרתם, איזה תחום הכי נפוץ בקבוצה? | ספורט |
| 5 | ACCEPTABLE | מי המבוגר ביותר מבין המשתתפים ששיתפו את הגיל שלהם? | רוני |
| 6 | GOOD | כמה אנשים בקבוצה בחרו מוזיקה בסגנון ג׳אז? | 1 |
| 7 | GOOD | איזה משני המאכלים האלה נבחר יותר בקבוצה? | סושי |
| 8 | GOOD | כמה אנשים בקבוצה בחרו תחביבים שכוללים פעילות גופנית? | 4 |
| 9 | GOOD | כמה אנשים בקבוצה בחרו מאכלים שמזוהים עם המטבח האיטלקי? | 4 |
| 10 | GOOD | כמה אנשים בקבוצה בחרו מוזיקה בסגנון מזרחית? | 2 |
| 11 | GOOD | מי גר הכי רחוק משאר הקבוצה, בממוצע? | יעל |
| 12 | GOOD | כמה מטבחים שונים מסתתרים מאחורי המאכלים שבחרתם? | 4 |
| 13 | GOOD | מה נפוץ יותר בקבוצה מבין תחומי התחביבים הבאים? | ספורט |
| 14 | GOOD | אילו שני אנשים בקבוצה גרים ביישובים הקרובים ביותר זה לזה בקו אווירי? | דנה + עמית |
| 15 | GOOD | כמה סגנונות מוזיקה מיוצגים בקבוצה? | 5 |
| 16 | GOOD | מה נפוץ יותר בקבוצה מבין אזורי המגורים הבאים? | המרכז |
| 17 | GOOD | מה נפוץ יותר בקבוצה מבין המטבחים הבאים? | המטבח האיטלקי |
| 18 | GOOD | מבין מי שבחרו תחביבים שקשורים לספורט, איזה סגנון מוזיקה הכי נפוץ? | מזרחית |
| 19 | GOOD | כמה אנשים בחרו גם מאכלים שמזוהים עם המטבח האיטלקי וגם תחביבים שקשורים לאמנות ויצירה? | 1 |
| 20 | GOOD | מבין המשתתפים שמגיעים מהמרכז, איזה מטבח הכי נפוץ? | המטבח האיטלקי |

### mixed_interests — en

| # | Rating | Question | Correct answer |
|---:|---|---|---|
| 1 | GOOD | Which activity family is most common in our group? | Sport |
| 2 | GOOD | Only one person in our group chose Electronic music. Who? | יעל |
| 3 | GOOD | Whose town is furthest north in the group? | רוני |
| 4 | GOOD | Which cuisine is most popular in our group’s food choices? | Italian cuisine |
| 5 | ACCEPTABLE | Who is oldest among the players who shared their age? | רוני |
| 6 | GOOD | How many people in our group chose Jazz music? | 1 |
| 7 | GOOD | Which of these two favorite food choices was shared by more players? | סושי |
| 8 | GOOD | How many people in our group chose hobbies involving Physical activity? | 4 |
| 9 | GOOD | How many people in our group chose Mizrahi music? | 2 |
| 10 | GOOD | How many people in our group chose Pop music? | 2 |
| 11 | GOOD | Who lives furthest from the rest of our group, on average? | יעל |
| 12 | GOOD | How many activity families are represented in our group? | 3 |
| 13 | GOOD | Which of these cuisines is more common in our group? | Italian cuisine |
| 14 | GOOD | Which pair chose the towns that are closest by air distance? | דנה + עמית |
| 15 | GOOD | How many music styles are represented in our group? | 5 |
| 16 | GOOD | What is more common in our group: outdoor hobbies or indoor hobbies? | Outdoors |
| 17 | GOOD | Which of these activity families is more common in our group? | Sport |
| 18 | GOOD | Among people from Central Israel, which cuisine is most common? | Italian cuisine |
| 19 | GOOD | How many people chose both Mizrahi music and foods associated with Asian cuisines? | 1 |
| 20 | GOOD | Among people who chose foods associated with Italian cuisine, which region is most common? | Central Israel |

### music_circle — he

| # | Rating | Question | Correct answer |
|---:|---|---|---|
| 1 | GOOD | איזה סגנון מוזיקה הכי נפוץ בקבוצה? | מזרחית |
| 2 | GOOD | רק אחד בקבוצה בחר אמן שמזוהה עם ים תיכונית. מי זה? | דנה |
| 3 | GOOD | מי בקבוצה גר הכי דרומה? | ליאור |
| 4 | GOOD | לפי השירים שבחרתם, איזה סגנון מוזיקה הכי נפוץ בקבוצה? | פופ |
| 5 | GOOD | כמה אנשים בקבוצה בחרו סרטים בז׳אנר אימה? | 2 |
| 6 | ACCEPTABLE | מי המבוגר ביותר מבין המשתתפים ששיתפו את הגיל שלהם? | נועה |
| 7 | GOOD | רק אחד בקבוצה בחר מאכל שמזוהה עם המטבח היפני. מי זה? | עמית |
| 8 | GOOD | כמה אנשים בקבוצה בחרו אמנים שמזוהים עם מזרחית? | 2 |
| 9 | GOOD | כמה אנשים בקבוצה בחרו סרטים בז׳אנר אנימציה? | 2 |
| 10 | GOOD | לפי האמנים שבחרתם, איזה סגנון מוזיקה הכי נפוץ בקבוצה? | פופ |
| 11 | GOOD | כמה תחומים שונים יש בתחביבים של הקבוצה? | 3 |
| 12 | GOOD | אילו שני אנשים בקבוצה גרים ביישובים הקרובים ביותר זה לזה בקו אווירי? | דנה + עומר |
| 13 | GOOD | לפי האמנים שבחרתם, איזה משני סגנונות המוזיקה האלה נפוץ יותר? | מזרחית |
| 14 | GOOD | כמה סגנונות מוזיקה יש בין השירים שבחרתם? | 5 |
| 15 | GOOD | לפי השירים שבחרתם, איזה משני סגנונות המוזיקה האלה נפוץ יותר? | פופ |
| 16 | GOOD | מה נפוץ יותר בקבוצה מבין אזורי המגורים הבאים? | המרכז |
| 17 | ACCEPTABLE | אצל חובבי איזה סגנון מוזיקה יש בקבוצה את המגוון הכי רחב של מאכלים אהובים? | מוזיקה מזרחית |
| 18 | GOOD | מבין מי שבחרו תחביבים שקשורים לספורט, איזה ז׳אנר קולנוע הכי נפוץ? | אימה |
| 19 | GOOD | כמה אנשים בחרו גם מוזיקה בסגנון מזרחית וגם מאכלים שמזוהים עם המטבח האיטלקי? | 1 |
| 20 | GOOD | כמה אנשים בחרו גם סרטים בז׳אנר אנימציה וגם תחביבים שקשורים לספורט? | 1 |

### music_circle — en

| # | Rating | Question | Correct answer |
|---:|---|---|---|
| 1 | GOOD | Looking at our chosen artists, which music style is most common? | Pop |
| 2 | GOOD | Only one person in our group chose Electronic music. Who? | ליאור |
| 3 | GOOD | Whose town is furthest north in the group? | עמית |
| 4 | GOOD | Looking at our chosen songs, which music style is most common? | Pop |
| 5 | GOOD | How many people in our group chose Action movies? | 1 |
| 6 | ACCEPTABLE | Who is oldest among the players who shared their age? | נועה |
| 7 | GOOD | Only one person in our group chose a Crime movie. Who? | דנה |
| 8 | GOOD | Which region is home to the majority of our group? | Central Israel |
| 9 | GOOD | How many people in our group chose Electronic songs? | 1 |
| 10 | GOOD | How many people in our group chose Metal songs? | 1 |
| 11 | GOOD | Which activity family is most common in our group? | Sport |
| 12 | GOOD | How many activity families are represented in our group? | 3 |
| 13 | GOOD | Which pair chose the towns that are closest by air distance? | דנה + עומר |
| 14 | GOOD | Looking at our chosen artists, which of these two music styles is more common? | Mizrahi |
| 15 | GOOD | How many cuisines are behind our group’s food choices? | 3 |
| 16 | GOOD | What is more common in our group: outdoor hobbies or indoor hobbies? | Outdoors |
| 17 | GOOD | Which of these cuisines is more common in our group? | Italian cuisine |
| 18 | ACCEPTABLE | Which shared music style connects the widest variety of favorite food choices? | Mizrahi |
| 19 | GOOD | Among people who chose hobbies related to Sport, which film genre is most common? | Horror |
| 20 | GOOD | How many people chose both Mizrahi music and foods associated with Italian cuisine? | 1 |

## Outcome

144 GOOD; 16 ACCEPTABLE; 0 BAD in the final samples.

Age ranking appears at most once per game. Literal group-diversity appears at most once; it is harder to interpret and remains an explicitly limited existing rule. Two workshop samples contain one overlapping simple comparison/majority, accepted as a small fallback overlap. No sample contains a trivia question, a person-similarity puzzle, or twenty versions of who chose a value.

Names stay as entered even in English games. Source titles retain their real native spelling when no English title exists. Question and explanation templates are bilingual; no runtime translation or AI is used.
