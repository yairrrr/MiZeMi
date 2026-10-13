"""Player-facing words for group discoveries, in Hebrew and English.

Templates are source literals; player values are only ever interpolated data.
Every template entry pairs an English and a Hebrew rendering of the same
question, so a seeded game asks the same thing, with the same answer, in either
language. Wording variants are picked by a stable hash of the discovery — not
by the random stream — so wording never changes which options are shuffled.
Nothing here names storage or engine concepts: players read about horror
movies, Italian food and the north, never about fields, values or categories.
"""

import zlib
from dataclasses import dataclass

from app.domain.questions.language import say


@dataclass(frozen=True)
class Term:
    en: str
    he: str
    en_items: str
    he_items: str
    en_item: str
    he_item: str
    en_fans: str = ''
    he_fans: str = ''
    he_def: str = ''
    en_topic: str = ''
    he_topic: str = ''
    en_from: str = ''
    he_from: str = ''
    en_in: str = ''
    he_in: str = ''


def _movie(en, he, en_items, he_items, en_item, he_item):
    return Term(en, he, en_items, he_items, en_item, he_item,
                en_fans=f'{en.lower()} fans', he_fans=f'חובבי {he}')


def _cuisine(en, he, he_def):
    article = 'an' if en[0] in 'AEIOU' else 'a'
    return Term(en, he, f'{en} food', f'אוכל {he}', f'{article} {en} dish', f'מאכל {he}',
                en_fans=f'{en} food fans', he_fans=f'חובבי אוכל {he}', he_def=he_def)


def _hobby(en, he, en_items, he_items, en_item, he_item, en_topic, he_topic):
    return Term(en, he, en_items, he_items, en_item, he_item, en_topic=en_topic, he_topic=he_topic)


def _music(en, he, en_items, he_items):
    return Term(en, he, en_items, he_items, en_items, he_items, en_fans=f'{en} fans', he_fans=f'חובבי {he}')


def _region(en, he, en_from, he_from, en_in, he_in):
    return Term(en, he, en, he, en, he, en_from=en_from, he_from=he_from, en_in=en_in, he_in=he_in)


LEXICON = {
    'movie.horror': _movie('Horror', 'אימה', 'horror movies', 'סרטי אימה', 'a horror movie', 'סרט אימה'),
    'movie.thriller': _movie('Thriller', 'מתח', 'thrillers', 'סרטי מתח', 'a thriller', 'סרט מתח'),
    'movie.mystery': _movie('Mystery', 'מסתורין', 'mystery movies', 'סרטי מסתורין', 'a mystery movie', 'סרט מסתורין'),
    'movie.action': _movie('Action', 'פעולה', 'action movies', 'סרטי פעולה', 'an action movie', 'סרט פעולה'),
    'movie.adventure': _movie('Adventure', 'הרפתקאות', 'adventure movies', 'סרטי הרפתקאות', 'an adventure movie', 'סרט הרפתקאות'),
    'movie.comedy': _movie('Comedy', 'קומדיה', 'comedies', 'קומדיות', 'a comedy', 'קומדיה'),
    'movie.drama': _movie('Drama', 'דרמה', 'dramas', 'דרמות', 'a drama', 'דרמה'),
    'movie.romance': _movie('Romance', 'רומנטיקה', 'romantic movies', 'סרטים רומנטיים', 'a romantic movie', 'סרט רומנטי'),
    'movie.scifi': _movie('Science fiction', 'מדע בדיוני', 'science fiction movies', 'סרטי מדע בדיוני', 'a science fiction movie', 'סרט מדע בדיוני'),
    'movie.fantasy': _movie('Fantasy', 'פנטזיה', 'fantasy movies', 'סרטי פנטזיה', 'a fantasy movie', 'סרט פנטזיה'),
    'movie.musical': _movie('Musical', 'מחזמר', 'musicals', 'מחזות זמר', 'a musical', 'מחזמר'),
    'movie.family': _movie('Family', 'משפחה', 'family movies', 'סרטי משפחה', 'a family movie', 'סרט משפחה'),
    'movie.crime': _movie('Crime', 'פשע', 'crime movies', 'סרטי פשע', 'a crime movie', 'סרט פשע'),
    'movie.war': _movie('War', 'מלחמה', 'war movies', 'סרטי מלחמה', 'a war movie', 'סרט מלחמה'),
    'movie.western': _movie('Western', 'מערבון', 'westerns', 'מערבונים', 'a western', 'מערבון'),
    'movie.biographical': _movie('Biography', 'ביוגרפיה', 'biographical movies', 'סרטים ביוגרפיים', 'a biographical movie', 'סרט ביוגרפי'),
    'movie.superhero': _movie('Superhero', 'גיבורי על', 'superhero movies', 'סרטי גיבורי על', 'a superhero movie', 'סרט גיבורי על'),
    'movie.animation': _movie('Animation', 'אנימציה', 'animated movies', 'סרטי אנימציה', 'an animated movie', 'סרט אנימציה'),
    'food.soup': Term('Soup', 'מרק', 'soups', 'מרקים', 'a soup', 'מרק',
        en_fans='people who chose soups', he_fans='מי שבחרו מרקים'),
    'food.salad': Term('Salad', 'סלט', 'salads', 'סלטים', 'a salad', 'סלט',
        en_fans='people who chose salads', he_fans='מי שבחרו סלטים'),
    'food.sandwich': Term('Sandwich or wrap', 'כריך או ראפ', 'sandwiches and wraps', 'כריכים וראפים', 'a sandwich or a wrap', 'כריך או ראפ',
        en_fans='people who chose sandwiches and wraps', he_fans='מי שבחרו כריכים וראפים'),
    'food.dessert': Term('Dessert', 'קינוח', 'desserts', 'קינוחים', 'a dessert', 'קינוח',
        en_fans='people who chose desserts', he_fans='מי שבחרו קינוחים'),
    'food.pasta': Term('Pasta or noodles', 'פסטה או אטריות', 'pasta and noodle dishes', 'מנות פסטה ואטריות', 'a pasta or noodle dish', 'מנת פסטה או אטריות',
        en_fans='people who chose pasta and noodle dishes', he_fans='מי שבחרו מנות פסטה ואטריות'),
    'food.rice': Term('Rice dish', 'מנת אורז', 'rice dishes', 'מנות אורז', 'a rice dish', 'מנת אורז',
        en_fans='people who chose rice dishes', he_fans='מי שבחרו מנות אורז'),
    'food.dip': Term('Dip or spread', 'מטבל או ממרח', 'dips and spreads', 'מטבלים וממרחים', 'a dip or a spread', 'מטבל או ממרח',
        en_fans='people who chose dips and spreads', he_fans='מי שבחרו מטבלים וממרחים'),
    'food.stew': Term('Stew', 'תבשיל', 'stews', 'תבשילים', 'a stew', 'תבשיל',
        en_fans='people who chose stews', he_fans='מי שבחרו תבשילים'),
    'food.egg': Term('Egg dish', 'מנת ביצים', 'egg dishes', 'מנות ביצים', 'an egg dish', 'מנת ביצים',
        en_fans='people who chose egg dishes', he_fans='מי שבחרו מנות ביצים'),
    'food.potato': Term('Potato dish', 'מנת תפוחי אדמה', 'potato dishes', 'מנות תפוחי אדמה', 'a potato dish', 'מנת תפוחי אדמה',
        en_fans='people who chose potato dishes', he_fans='מי שבחרו מנות תפוחי אדמה'),
    'food.dumpling': Term('Dumplings', 'כיסונים', 'dumplings', 'כיסונים', 'a dumpling dish', 'מנת כיסונים',
        en_fans='people who chose dumplings', he_fans='מי שבחרו כיסונים'),
    'hobby.music': _hobby('Making music', 'נגינה ושירה', 'music-making hobbies',
        'תחביבים של נגינה או שירה', 'a music-making hobby', 'תחביב של נגינה או שירה',
        'making music', 'לנגינה ולשירה'),
    'age.12_under': Term('12 and under', '12 ומטה', 'people aged 12 and under', 'בני 12 ומטה', 'people aged 12 and under', 'בני 12 ומטה',
        en_fans='people aged 12 and under', he_fans='בני 12 ומטה'),
    'age.13_15': Term('13–15', '13–15', 'people aged 13–15', 'בני 13–15', 'people aged 13–15', 'בני 13–15',
        en_fans='people aged 13–15', he_fans='בני 13–15'),
    'age.16_18': Term('16–18', '16–18', 'people aged 16–18', 'בני 16–18', 'people aged 16–18', 'בני 16–18',
        en_fans='people aged 16–18', he_fans='בני 16–18'),
    'age.19_24': Term('19–24', '19–24', 'people aged 19–24', 'בני 19–24', 'people aged 19–24', 'בני 19–24',
        en_fans='people aged 19–24', he_fans='בני 19–24'),
    'age.25_34': Term('25–34', '25–34', 'people aged 25–34', 'בני 25–34', 'people aged 25–34', 'בני 25–34',
        en_fans='people aged 25–34', he_fans='בני 25–34'),
    'age.35_49': Term('35–49', '35–49', 'people aged 35–49', 'בני 35–49', 'people aged 35–49', 'בני 35–49',
        en_fans='people aged 35–49', he_fans='בני 35–49'),
    'age.50_plus': Term('50 and over', '50 ומעלה', 'people aged 50 and over', 'בני 50 ומעלה', 'people aged 50 and over', 'בני 50 ומעלה',
        en_fans='people aged 50 and over', he_fans='בני 50 ומעלה'),
    'food.italian': _cuisine('Italian', 'איטלקי', 'האיטלקי'),
    'food.asian': _cuisine('Asian', 'אסייתי', 'האסייתי'),
    'food.middle_eastern': _cuisine('Middle Eastern', 'מזרח תיכוני', 'המזרח תיכוני'),
    'food.american': _cuisine('American', 'אמריקאי', 'האמריקאי'),
    'food.mexican': _cuisine('Mexican', 'מקסיקני', 'המקסיקני'),
    'food.french': _cuisine('French', 'צרפתי', 'הצרפתי'),
    'food.greek': _cuisine('Greek', 'יווני', 'היווני'),
    'food.spanish': _cuisine('Spanish', 'ספרדי', 'הספרדי'),
    'food.north_african': _cuisine('North African', 'צפון אפריקאי', 'הצפון אפריקאי'),
    'food.jewish': _cuisine('Traditional Jewish', 'יהודי מסורתי', 'היהודי המסורתי'),
    'food.eastern_european': _cuisine('Eastern European', 'מזרח אירופי', 'המזרח אירופי'),
    'food.british': _cuisine('British', 'בריטי', 'הבריטי'),
    'food.south_american': _cuisine('South American', 'דרום אמריקאי', 'הדרום אמריקאי'),
    'hobby.sport': _hobby('Sport', 'ספורט', 'sports hobbies', 'תחביבי ספורט', 'a sports hobby', 'תחביב ספורטיבי', 'sport', 'לספורט'),
    'hobby.creative': _hobby('Arts and crafts', 'אמנות ויצירה', 'creative hobbies', 'תחביבי יצירה', 'a creative hobby', 'תחביב יצירתי', 'arts and crafts', 'לאמנות ויצירה'),
    'hobby.digital': _hobby('Digital', 'דיגיטל ומחשבים', 'digital hobbies', 'תחביבים דיגיטליים', 'a digital hobby', 'תחביב דיגיטלי', 'computers and digital media', 'לדיגיטל ומחשבים'),
    'hobby.table_games': _hobby('Board games and puzzles', 'משחקי שולחן וחידות', 'board game and puzzle hobbies', 'תחביבים של משחקי שולחן וחידות', 'a board game or puzzle hobby', 'תחביב של משחקי שולחן או חידות', 'board games and puzzles', 'למשחקי שולחן וחידות'),
    'hobby.nature': _hobby('Nature', 'טבע', 'nature hobbies', 'תחביבי טבע', 'a nature hobby', 'תחביב בטבע', 'nature', 'לטבע'),
    'hobby.learning': _hobby('Learning and reading', 'למידה וקריאה', 'learning and reading hobbies', 'תחביבים של למידה וקריאה', 'a learning or reading hobby', 'תחביב של למידה או קריאה', 'learning and reading', 'ללמידה וקריאה'),
    'hobby.cooking': _hobby('Cooking and baking', 'בישול ואפייה', 'cooking and baking hobbies', 'תחביבים של בישול ואפייה', 'a cooking or baking hobby', 'תחביב של בישול או אפייה', 'cooking and baking', 'לבישול ואפייה'),
    'hobby.collecting': _hobby('Collecting', 'אספנות', 'collecting hobbies', 'תחביבי אספנות', 'a collecting hobby', 'תחביב של אספנות', 'collecting', 'לאספנות'),
    'hobby.wellbeing': _hobby('Mindfulness and relaxation', 'קשיבות והרפיה', 'relaxation hobbies', 'תחביבי הרפיה', 'a relaxation hobby', 'תחביב של הרפיה', 'mindfulness and relaxation', 'לקשיבות והרפיה'),
    'hobby.social': _hobby('Community and social', 'פעילות חברתית', 'social hobbies', 'תחביבים חברתיים', 'a social hobby', 'תחביב חברתי', 'community and social life', 'לפעילות חברתית'),
    'hobby.travel': _hobby('Travel', 'טיולים ונסיעות', 'travel hobbies', 'תחביבי טיולים', 'a travel hobby', 'תחביב של טיולים', 'travel', 'לטיולים ונסיעות'),
    'activity.physical': _hobby('Physically active', 'פעילות גופנית', 'physically active hobbies', 'תחביבים עם פעילות גופנית', 'a physically active hobby', 'תחביב שכולל פעילות גופנית', 'physical activity', 'לפעילות גופנית'),
    'activity.nonphysical': _hobby('Not physically demanding', 'בלי מאמץ גופני', 'hobbies without physical effort', 'תחביבים בלי מאמץ גופני', 'a hobby without physical effort', 'תחביב בלי מאמץ גופני', 'calm activities', 'לפעילות רגועה'),
    'setting.outdoor': _hobby('Outdoors', 'בחוץ', 'outdoor hobbies', 'תחביבי חוץ', 'an outdoor hobby', 'תחביב שעושים בחוץ', 'the outdoors', 'לחוץ'),
    'setting.indoor': _hobby('Indoors', 'בבית', 'indoor hobbies', 'תחביבי בית', 'an indoor hobby', 'תחביב שעושים בבית', 'indoor activities', 'לבית'),
    'music.pop': _music('Pop', 'פופ', 'pop music', 'מוזיקת פופ'),
    'music.rock': _music('Rock', 'רוק', 'rock music', 'מוזיקת רוק'),
    'music.hiphop': _music('Hip-hop', 'היפ הופ', 'hip-hop', 'היפ הופ'),
    'music.electronic': _music('Electronic', 'אלקטרונית', 'electronic music', 'מוזיקה אלקטרונית'),
    'music.mizrahi': _music('Mizrahi', 'מזרחית', 'Mizrahi music', 'מוזיקה מזרחית'),
    'music.mediterranean': _music('Mediterranean', 'ים תיכונית', 'Mediterranean music', 'מוזיקה ים תיכונית'),
    'music.israeli': _music('Israeli', 'זמר עברי', 'Israeli music', 'זמר עברי'),
    'music.jewish': _music('Jewish', 'מוזיקה יהודית', 'Jewish music', 'מוזיקה יהודית'),
    'music.classical': _music('Classical', 'קלאסית', 'classical music', 'מוזיקה קלאסית'),
    'music.jazz': _music('Jazz', 'ג׳אז', 'jazz', 'מוזיקת ג׳אז'),
    'music.indie': _music('Indie', 'אינדי', 'indie music', 'מוזיקת אינדי'),
    'music.rnb': _music('R&B', 'אר אנד בי', 'R&B', 'מוזיקת אר אנד בי'),
    'music.reggae': _music('Reggae', 'רגאיי', 'reggae', 'מוזיקת רגאיי'),
    'music.folk': _music('Folk', 'פולק', 'folk music', 'מוזיקת פולק'),
    'music.country': _music('Country', 'קאנטרי', 'country music', 'מוזיקת קאנטרי'),
    'music.blues': _music('Blues', 'בלוז', 'blues', 'מוזיקת בלוז'),
    'music.soul': _music('Soul', 'סול', 'soul music', 'מוזיקת סול'),
    'music.funk': _music('Funk', 'פאנק', 'funk', 'מוזיקת פאנק'),
    'music.gospel': _music('Gospel', 'גוספל', 'gospel music', 'מוזיקת גוספל'),
    'music.latin': _music('Latin', 'לטינית', 'Latin music', 'מוזיקה לטינית'),
    'music.disco': _music('Disco', 'דיסקו', 'disco', 'מוזיקת דיסקו'),
    'music.ska': _music('Ska', 'סקא', 'ska', 'מוזיקת סקא'),
    'region.north': _region('The north', 'הצפון', 'the north', 'מהצפון', 'the north', 'בצפון'),
    'region.central': _region('The center', 'המרכז', 'the center of the country', 'מהמרכז', 'the center of the country', 'במרכז'),
    'region.south': _region('The south', 'הדרום', 'the south', 'מהדרום', 'the south', 'בדרום'),
    'region.jerusalem': _region('The Jerusalem area', 'אזור ירושלים', 'the Jerusalem area', 'מאזור ירושלים', 'the Jerusalem area', 'באזור ירושלים'),
}


def _fallback(category, domain: str) -> Term:
    """Natural phrasing for a category without a curated entry (small reference sets)."""
    en, he = category.english, category.hebrew
    if domain == 'movie':
        return _movie(en, he, f'{en.lower()} movies', f'סרטים בז׳אנר {he}', f'a {en.lower()} movie', f'סרט בז׳אנר {he}')
    if domain == 'food':
        return Term(en, he, f'food from {en}', f'אוכל מ{he}', f'a dish from {en}', f'מאכל מ{he}',
                    en_fans=f'fans of food from {en}', he_fans=f'חובבי אוכל מ{he}', he_def=he)
    if domain == 'hobby':
        return _hobby(en, he, f'hobbies related to {en.lower()}', f'תחביבים שקשורים ל{he}',
                      f'a hobby related to {en.lower()}', f'תחביב שקשור ל{he}', en.lower(), f'ל{he}')
    if domain == 'music':
        return _music(en, he, f'{en} music', f'מוזיקה בסגנון {he}')
    bare = he[1:] if he.startswith('ה') else he
    return _region(en, he, en, f'מ{he}', en, f'ב{bare}')


# (operation, dimension) → [(English, Hebrew), …]. Placeholders are filled by
# ``Wording.question`` with the forms of the categories being asked about.
TEMPLATES = {
    ('count', 'movie.genre'): [
        ('How many people in our group chose {item}?', 'כמה אנשים בקבוצה בחרו {item}?'),
        ('How many people picked {item} as their favorite movie?', 'כמה אנשים בחרו {item} כסרט האהוב?'),
        ('How many of you chose {item}?', 'כמה מכם בחרו {item}?'),
    ],
    ('count', 'food.cuisine'): [
        ('How many people in our group chose {item}?', 'כמה אנשים בקבוצה בחרו {item}?'),
        ('How many of you picked {items}?', 'כמה מכם בחרו {items}?'),
        ('How many of the dishes you chose are {label}?', 'כמה מהמאכלים שבחרתם הם מהמטבח {def}?'),
    ],
    ('count', 'hobby.family'): [
        ('How many people in our group chose {item}?', 'כמה אנשים בקבוצה בחרו {item}?'),
        ('How many of you have a hobby connected to {topic}?', 'כמה מכם בחרו תחביב שקשור {topic}?'),
        ('How many people here have {item}?', 'לכמה אנשים כאן יש {item}?'),
    ],
    ('count', 'hobby.physical'): [
        ('How many people in our group chose a hobby that involves physical activity?', 'כמה אנשים בקבוצה בחרו תחביב שכולל פעילות גופנית?'),
        ('How many of the hobbies you chose involve physical activity?', 'כמה מהתחביבים שבחרתם כוללים פעילות גופנית?'),
        ('How many of you picked a physically active hobby?', 'לכמה מכם יש תחביב שדורש פעילות גופנית?'),
    ],
    ('count', 'hobby.setting'): [
        ('How many people in our group chose a hobby usually done outdoors?', 'כמה אנשים בקבוצה בחרו תחביב שעושים בדרך כלל בחוץ?'),
        ('How many of the hobbies you chose are outdoor hobbies?', 'כמה מהתחביבים שבחרתם הם תחביבי חוץ?'),
        ('How many of you picked an outdoor hobby?', 'לכמה מכם יש תחביב שעושים בחוץ?'),
    ],
    ('count', 'music.genre'): [
        ('How many people in our group chose {items}?', 'כמה אנשים בקבוצה בחרו {items}?'),
        ('How many of you picked {items} as your favorite style?', 'כמה מכם בחרו {items} כסגנון האהוב?'),
        ('How many {fans} are there in our group?', 'כמה {fans} יש בקבוצה?'),
    ],
    ('count', 'artist.genre'): [
        ('How many people chose an artist associated with {items}?', 'כמה אנשים בחרו אמן שמזוהה עם {items}?'),
        ('How many people chose an artist known for {items}?', 'כמה אנשים בחרו אמן שמזוהה עם {items}?'),
        ('How many of you picked a favorite artist associated with {items}?', 'כמה מכם בחרו אמן אהוב שמזוהה עם {items}?'),
    ],
    ('count', 'song.genre'): [
        ('How many people chose a favorite song in the {style} style?', 'כמה אנשים בחרו שיר אהוב בסגנון {style}?'),
        ('How many people chose a song in the {style} style?', 'כמה אנשים בחרו שיר בסגנון {style}?'),
        ('How many of you picked a song in the {style} style?', 'כמה מכם בחרו שיר בסגנון {style}?'),
    ],
    ('recognized_count', 'movie.genre'): [
        ('Among the movie choices we recognized, how many people chose {item}?', 'מבין בחירות הסרטים שזוהו, כמה אנשים בחרו {item}?'),
    ],
    ('recognized_count', 'artist.genre'): [
        ('Among the artist choices we recognized, how many people chose an artist associated with {items}?', 'מבין בחירות האמנים שזוהו, כמה אנשים בחרו אמן שמזוהה עם {items}?'),
    ],
    ('recognized_count', 'song.genre'): [
        ('Among the song choices we recognized, how many people chose a song in the {style} style?', 'מבין בחירות השירים שזוהו, כמה אנשים בחרו שיר בסגנון {style}?'),
    ],
    ('count', 'place.region'): [
        ('How many people in our group live in {in}?', 'כמה אנשים בקבוצה גרים {in}?'),
        ('How many of you come from {from}?', 'כמה מכם מגיעים {from}?'),
        ('How many people here live in {in}?', 'כמה משתתפים כאן גרים {in}?'),
    ],
    ('majority', 'movie.genre'): [
        ('Which genre is most common among the favorite movies you chose?', 'איזה ז׳אנר הכי נפוץ בין הסרטים האהובים שבחרתם?'),
        ('Based on the movies you chose, which genre leads?', 'לפי הסרטים שבחרתם, איזה ז׳אנר מוביל?'),
        ('Which genre shows up most in the movies you chose?', 'איזה ז׳אנר חוזר הכי הרבה בסרטים שבחרתם?'),
    ],
    ('majority', 'food.cuisine'): [
        ('Based on your food choices, which cuisine is the most popular in our group?', 'לפי המאכלים שבחרתם, איזה מטבח הכי פופולרי בקבוצה?'),
        ('Which cuisine leads our group’s food choices?', 'איזה מטבח מוביל בבחירות האוכל שלכם?'),
        ('Which kind of food is the group’s favorite?', 'איזה סוג אוכל הכי אהוב בקבוצה?'),
    ],
    ('majority', 'hobby.family'): [
        ('Based on your hobbies, which type of hobby is the most common in our group?', 'לפי התחביבים שבחרתם, איזה סוג תחביב הכי נפוץ בקבוצה?'),
        ('Which type of hobby do the most people here have?', 'איזה סוג תחביב יש להכי הרבה אנשים כאן?'),
        ('What best describes the hobbies in our group?', 'מה הכי מאפיין את התחביבים בקבוצה?'),
    ],
    ('majority', 'music.genre'): [
        ('Which music style rules our group?', 'איזה סגנון מוזיקה הכי שולט בקבוצה?'),
        ('Which music style is the most popular here?', 'איזה סגנון מוזיקה הכי פופולרי כאן?'),
        ('Based on your choices, which music leads the group?', 'לפי הבחירות שלכם, איזו מוזיקה מובילה בקבוצה?'),
    ],
    ('majority', 'artist.genre'): [
        ('Which genre is most common among the favorite artists you chose?', 'איזה ז׳אנר מוזיקה הכי נפוץ בין האמנים האהובים שבחרתם?'),
        ('Which style connects the most of your favorite artists?', 'איזה סגנון מחבר בין הכי הרבה מהאמנים שבחרתם?'),
        ('Looking at your favorite artists, which style leads?', 'אם מסתכלים על האמנים האהובים עליכם, איזה סגנון מוביל?'),
    ],
    ('majority', 'song.genre'): [
        ('Which music style appears most often among the songs you chose?', 'איזה סגנון מוזיקלי חוזר הכי הרבה בין השירים שנבחרו?'),
        ('Which style connects the most of your favorite songs?', 'איזה סגנון מחבר בין הכי הרבה מהשירים שבחרתם?'),
        ('Looking at your favorite songs, which style leads?', 'אם מסתכלים על השירים האהובים עליכם, איזה סגנון מוביל?'),
    ],
    ('character', 'food.cuisine'): [
        ('Which food does our group love most — {a}, {b} or {c}?', 'איזה אוכל הכי אהוב בקבוצה — {a}, {b} או {c}?'),
    ],
    ('character', 'hobby.family'): [
        ('Based on your hobbies, what describes our group best — {a}, {b} or {c}?', 'לפי התחביבים שבחרתם, מה יותר מאפיין את הקבוצה — {a}, {b} או {c}?'),
    ],
    ('character', 'music.genre'): [
        ('Which music defines our group — {a}, {b} or {c}?', 'איזו מוזיקה הכי מאפיינת את הקבוצה — {a}, {b} או {c}?'),
    ],
    ('comparison', 'movie.genre'): [
        ('Among your chosen movies, which genre appears more — {a} or {b}?', 'בין הסרטים שבחרתם, איזה ז׳אנר מופיע יותר — {a} או {b}?'),
        ('Based on the movies you chose, which leads — {a} or {b}?', 'לפי הסרטים שבחרתם, מה מוביל — {a} או {b}?'),
        ('Looking at your movie picks, which side wins — {a} or {b}?', 'אם מסתכלים על בחירות הסרטים, איזה צד מנצח — {a} או {b}?'),
    ],
    ('overlap', 'movie.genre'): [
        ('Which genre appears more in the movies you chose — {a} or {b}?', 'איזה ז׳אנר מופיע יותר בסרטים שבחרתם — {a} או {b}?'),
        ('In your movie picks, which shows up more — {a} or {b}?', 'בסרטים שבחרתם, מה מופיע יותר — {a} או {b}?'),
    ],
    ('comparison', 'food.cuisine'): [
        ('Are there more fans of {a} or {b} food in our group?', 'מה יש יותר בקבוצה — חובבי אוכל {a} או {b}?'),
        ('Based on your food choices, which leads — {a} or {b} food?', 'לפי המאכלים שבחרתם, מה מוביל — אוכל {a} או {b}?'),
        ('Which cuisine wins in your food choices — {a} or {b}?', 'איזה מטבח מנצח בבחירות האוכל שלכם — {def_a} או {def_b}?'),
    ],
    ('overlap', 'food.cuisine'): [
        ('Which cuisine appears more in your food choices — {a} or {b}?', 'איזה מטבח מופיע יותר בבחירות האוכל שלכם — {def_a} או {def_b}?'),
    ],
    ('comparison', 'hobby.family'): [
        ('Are there more {items_a} or {items_b} in our group?', 'מה יש יותר בקבוצה — {items_a} או {items_b}?'),
        ('Based on your hobbies, which leads — {a} or {b}?', 'לפי התחביבים שבחרתם, מה מוביל — {a} או {b}?'),
        ('What is more common here — {items_a} or {items_b}?', 'מה נפוץ יותר כאן — {items_a} או {items_b}?'),
    ],
    ('overlap', 'hobby.family'): [
        ('Which appears more in the hobbies you chose — {a} or {b}?', 'מה מופיע יותר בתחביבים שבחרתם — {a} או {b}?'),
    ],
    ('comparison', 'hobby.setting'): [
        ('What is more common here — outdoor hobbies or indoor hobbies?', 'מה נפוץ יותר כאן — תחביבי חוץ או תחביבי בית?'),
        ('Are there more outdoor hobbies or indoor hobbies in our group?', 'מה יש יותר בקבוצה — תחביבים שעושים בחוץ או תחביבים שעושים בבית?'),
    ],
    ('comparison', 'hobby.physical'): [
        ('Are there more physically active hobbies or hobbies without physical effort in our group?', 'מה יש יותר בקבוצה — תחביבים עם פעילות גופנית או תחביבים בלי מאמץ גופני?'),
        ('What is more common here — hobbies with physical activity or hobbies without it?', 'מה נפוץ יותר כאן — תחביבים עם פעילות גופנית או תחביבים בלי מאמץ גופני?'),
    ],
    ('comparison', 'music.genre'): [
        ('Are there more {fans_a} or {fans_b} in our group?', 'מה יש יותר בקבוצה — חובבי {a} או {b}?'),
        ('Which music style wins here — {a} or {b}?', 'איזה סגנון מוזיקה מנצח כאן — {a} או {b}?'),
        ('Based on your choices, which leads — {a} or {b}?', 'לפי הבחירות שלכם, מה מוביל — {a} או {b}?'),
    ],
    ('overlap', 'music.genre'): [
        ('Which style appears more in your choices — {a} or {b}?', 'איזה סגנון מופיע יותר בבחירות שלכם — {a} או {b}?'),
    ],
    ('comparison', 'artist.genre'): [
        ('Among the artists you chose, which style appears more — {a} or {b}?', 'בין האמנים שבחרתם, איזה סגנון מופיע יותר — {a} או {b}?'),
    ],
    ('overlap', 'artist.genre'): [
        ('Among the artists you chose, which style appears more — {a} or {b}?', 'בין האמנים שבחרתם, איזה סגנון מופיע יותר — {a} או {b}?'),
    ],
    ('comparison', 'song.genre'): [
        ('Among the songs you chose, which style appears more — {a} or {b}?', 'בין השירים שבחרתם, איזה סגנון מופיע יותר — {a} או {b}?'),
    ],
    ('overlap', 'song.genre'): [
        ('Among the songs you chose, which style appears more — {a} or {b}?', 'בין השירים שבחרתם, איזה סגנון מופיע יותר — {a} או {b}?'),
    ],
    ('comparison', 'place.region'): [
        ('Are there more people from {from_a} or from {from_b} in our group?', 'מה יש יותר בקבוצה — אנשים {from_a} או {from_b}?'),
        ('Where do more of you come from — {from_a} or {from_b}?', 'מאיפה מגיעים יותר מכם — {from_a} או {from_b}?'),
        ('Which region is better represented in our group — {a} or {b}?', 'איזה אזור מיוצג יותר בקבוצה — {a} או {b}?'),
    ],
    ('unique', 'movie.genre'): [
        ('Only one person in our group chose {item}. Who?', 'רק אדם אחד בקבוצה בחר {item}. מי זה?'),
        ('Who is the only one here who picked {item}?', 'מי היחיד/ה בקבוצה שבחר/ה {item}?'),
    ],
    ('unique', 'food.cuisine'): [
        ('Only one person in our group chose {item}. Who?', 'רק אדם אחד בקבוצה בחר {item}. מי זה?'),
        ('Who is the only one here who picked {item}?', 'מי היחיד/ה בקבוצה שבחר/ה {item}?'),
    ],
    ('unique', 'hobby.family'): [
        ('Only one person in our group chose {item}. Who?', 'רק אדם אחד בקבוצה בחר {item}. מי זה?'),
        ('Who is the only one here with {item}?', 'מי היחיד/ה בקבוצה שבחר/ה {item}?'),
    ],
    ('unique', 'music.genre'): [
        ('Only one person in our group chose {items}. Who?', 'רק אדם אחד בקבוצה בחר {items}. מי זה?'),
        ('Who is the only {fan} here?', 'מי היחיד/ה בקבוצה שבחר/ה {items}?'),
    ],
    ('unique', 'artist.genre'): [
        ('Only one person chose an artist associated with {items}. Who?', 'רק אדם אחד בחר אמן שמזוהה עם {items}. מי זה?'),
    ],
    ('unique', 'song.genre'): [
        ('Only one person chose a song in the {style} style. Who?', 'רק אדם אחד בחר שיר בסגנון {style}. מי זה?'),
    ],
    ('unique', 'place.region'): [
        ('Only one person in our group lives in {in}. Who?', 'רק אדם אחד בקבוצה גר {in}. מי זה?'),
        ('Who is the only one here from {from}?', 'מי היחיד/ה בקבוצה שמגיע/ה {from}?'),
    ],
    ('genre_outlier', 'movie.genre'): [
        ('Who chose a movie with a genre nobody else’s movie represents?', 'מי בחר סרט מז׳אנר שאף אחד אחר בקבוצה לא בחר?'),
    ],
    ('genre_outlier', 'artist.genre'): [
        ('Who chose an artist with a genre nobody else’s artist represents?', 'מי בחר אמן מסגנון שאף אחד אחר בקבוצה לא בחר?'),
    ],
    ('genre_outlier', 'song.genre'): [
        ('Who chose a song with a genre nobody else’s song represents?', 'מי בחר שיר מסגנון שאף אחד אחר בקבוצה לא בחר?'),
    ],
    ('diversity', 'movie.genre'): [
        ('How many genres are represented by the movies you chose?', 'כמה ז׳אנרים שונים מיוצגים בסרטים שבחרתם?'),
    ],
    ('diversity', 'artist.genre'): [
        ('How many music genres are represented by your chosen artists?', 'כמה סגנונות מוזיקה שונים מיוצגים באמנים שבחרתם?'),
    ],
    ('diversity', 'song.genre'): [
        ('How many music genres are represented by the songs you chose?', 'כמה סגנונות מוזיקה שונים מיוצגים בשירים שבחרתם?'),
    ],
    ('diversity', 'food.cuisine'): [
        ('How many different cuisines are behind your food choices?', 'כמה מטבחים שונים מסתתרים מאחורי המאכלים שבחרתם?'),
        ('How many cuisines are represented in your favorite foods?', 'כמה מטבחים שונים מיוצגים בבחירות האוכל שלכם?'),
    ],
    ('diversity', 'hobby.family'): [
        ('How many different types of hobbies are there in our group?', 'כמה סוגי תחביבים שונים יש בקבוצה?'),
        ('Into how many different types do your hobbies fall?', 'לכמה סוגים שונים מתחלקים התחביבים שבחרתם?'),
    ],
    ('diversity', 'music.genre'): [
        ('How many different music styles are represented here?', 'כמה סגנונות מוזיקה שונים מיוצגים כאן?'),
        ('How many music styles do your choices cover?', 'כמה סגנונות מוזיקה שונים יש בבחירות שלכם?'),
    ],
    ('diversity', 'place.region'): [
        ('How many different regions of Israel are represented here?', 'כמה אזורים שונים בארץ מיוצגים כאן?'),
        ('From how many regions of Israel does our group come?', 'מכמה אזורים בארץ מגיעים חברי הקבוצה?'),
    ],
    ('minority', 'movie.genre'): [
        ('Of these genres, which appears least in the movies you chose?', 'מבין הז׳אנרים האלה, איזה מופיע הכי מעט בסרטים שבחרתם?'),
    ],
    ('minority', 'food.cuisine'): [
        ('Of these cuisines, which is the least common in your food choices?', 'מבין המטבחים האלה, איזה הכי פחות נפוץ בבחירות האוכל שלכם?'),
    ],
    ('minority', 'hobby.family'): [
        ('Of these types of hobbies, which is the least common in our group?', 'מבין סוגי התחביבים האלה, איזה הכי פחות נפוץ בקבוצה?'),
    ],
    ('minority', 'music.genre'): [
        ('Of these music styles, which did the fewest people choose?', 'מבין סגנונות המוזיקה האלה, איזה נבחר הכי מעט?'),
    ],
    ('distribution', 'movie.genre'): [
        ('Of these genres, which appears most in the movies you chose?', 'מבין הז׳אנרים האלה, איזה מופיע הכי הרבה בסרטים שבחרתם?'),
    ],
    ('distribution', 'food.cuisine'): [
        ('Of these cuisines, which is the most common in your food choices?', 'מבין המטבחים האלה, איזה הכי נפוץ בבחירות האוכל שלכם?'),
    ],
    ('distribution', 'hobby.family'): [
        ('Of these types of hobbies, which is the most common in our group?', 'מבין סוגי התחביבים האלה, איזה הכי נפוץ בקבוצה?'),
    ],
    ('distribution', 'music.genre'): [
        ('Of these music styles, which did the most people choose?', 'מבין סגנונות המוזיקה האלה, איזה נבחר הכי הרבה?'),
    ],
    ('distribution', 'artist.genre'): [
        ('Of these styles, which fits the most of the artists you chose?', 'מבין הסגנונות האלה, איזה מתאים להכי הרבה מהאמנים שבחרתם?'),
    ],
    ('distribution', 'song.genre'): [
        ('Of these styles, which fits the most of the songs you chose?', 'מבין הסגנונות האלה, איזה מתאים להכי הרבה מהשירים שבחרתם?'),
    ],
    ('count', 'food.format'): [
        ('How many of the dishes you chose are {items}?', 'כמה מהמאכלים שבחרתם הם {items}?'),
        ('How many of you picked {item}?', 'כמה מכם בחרו {item}?'),
    ],
    ('majority', 'food.format'): [
        ('Which kind of dish shows up most in your food choices?', 'איזה סוג מנה הכי נפוץ בבחירות האוכל שלכם?'),
        ('Looking at the dishes you chose, which kind leads?', 'אם מסתכלים על המאכלים שבחרתם, איזה סוג מנה מוביל?'),
    ],
    ('comparison', 'food.format'): [
        ('Which shows up more in your choices — {items_a} or {items_b}?', 'מה מופיע יותר בבחירות שלכם — {items_a} או {items_b}?'),
    ],
    ('unique', 'food.format'): [
        ('Only one person chose {item}. Who?', 'רק אדם אחד בחר {item}. מי זה?'),
    ],
    ('diversity', 'food.format'): [
        ('How many different kinds of dishes are in your food choices?', 'כמה סוגי מנות שונים יש בבחירות האוכל שלכם?'),
    ],
    ('count', 'hobby.making_music'): [
        ('How many of you chose a hobby that means playing or singing?', 'כמה מכם בחרו תחביב של נגינה או שירה?'),
    ],
    ('unique', 'hobby.making_music'): [
        ('Only one person here chose a music-making hobby. Who?', 'רק אדם אחד כאן בחר תחביב של נגינה או שירה. מי זה?'),
    ],
    ('count', 'age.band'): [
        ('How many of you are {label}?', 'כמה מכם בני {label}?'),
    ],
    ('majority', 'age.band'): [
        ('Which age range is the most common in our group?', 'איזה טווח גילים הכי נפוץ בקבוצה?'),
        ('Most of the shared ages fall in one range. Which?', 'רוב הגילים ששיתפתם נמצאים בטווח אחד. איזה?'),
    ],
    ('comparison', 'age.band'): [
        ('Which is bigger in our group — {items_a} or {items_b}?', 'מי יותר גדולה בקבוצה — הקבוצה של {items_a} או של {items_b}?'),
    ],
    ('diversity', 'age.band'): [
        ('How many different age ranges are in this group?', 'כמה טווחי גיל שונים יש בקבוצה?'),
    ],
    ('spread', 'age.band'): [
        ('How many years are there between the youngest and the oldest of you?', 'כמה שנים מפרידות בין הצעיר/ה ביותר למבוגר/ת ביותר בקבוצה?'),
    ],
    ('attribution', 'personal.fact'): [
        ('Who wrote this about themselves: “{line}”?', 'מי כתב/ה את זה על עצמו/ה: ״{line}״?'),
        ('One of you shared this: “{line}”. Who?', 'אחד מכם שיתף את זה: ״{line}״. מי?'),
    ],
    ('twins', 'multi'): [
        ('Which two of you turned out to be the most alike?', 'איזה שניים מכם יצאו הכי דומים בבחירות?'),
        ('Which pair here has the most in common?', 'לאיזה זוג כאן יש הכי הרבה במשותף?'),
    ],
    ('typical', 'multi'): [
        ('Whose answers match the group’s most common choices?', 'מי מכם בחר/ה הכי הרבה מהבחירות הנפוצות בקבוצה?'),
        ('Who turned out to be the most typical member of this group?', 'מי יצא/ה הכי מייצג/ת את הקבוצה?'),
    ],
    ('agreement', 'multi'): [
        ('Where do you agree the most — {a}, {b} or {c}?', 'במה אתם הכי מסכימים — {a}, {b} או {c}?'),
    ],
    ('variety', 'multi'): [
        ('Where are you the most different from each other — {a}, {b} or {c}?', 'במה אתם הכי שונים זה מזה — {a}, {b} או {c}?'),
    ],
    ('song_link', 'multi'): [
        ('{name} picked {artist} as a favorite artist. Which of you chose a song by {artist}?',
         '{name} בחר/ה את {artist} כאמן/ית אהוב/ה. מי מכם בחר/ה שיר של {artist}?'),
    ],
    ('series_link', 'movie.genre'): [
        ('{name} chose “{choice}”. Who picked another movie from the same series?',
         '{name} בחר/ה את ״{choice}״. מי בחר/ה סרט אחר מאותה סדרה?'),
    ],
    ('region_majority', 'place.region'): [
        ('Which region of Israel is home to most of our group?', 'מאיזה אזור בארץ מגיע רוב הקבוצה?'),
        ('Most of our group lives in one region. Which one?', 'רוב הקבוצה גרה באותו אזור. באיזה?'),
        ('Where in Israel does most of the group live?', 'איפה בארץ גר רוב הקבוצה?'),
    ],
    ('region_plurality', 'place.region'): [
        ('Which region of Israel do the most people in our group come from?', 'מאיזה אזור בארץ מגיעים הכי הרבה אנשים בקבוצה?'),
        ('In which region of Israel do the most of you live?', 'באיזה אזור בארץ גרים הכי הרבה מכם?'),
        ('Which region of Israel is best represented in our group?', 'איזה אזור בארץ הכי מיוצג בקבוצה?'),
    ],
    ('north', 'place.region'): [
        ('Who lives the furthest north?', 'מי גר/ה הכי צפונה?'),
        ('Which of you lives in the northernmost town?', 'מי מכם גר/ה ביישוב הכי צפוני?'),
    ],
    ('south', 'place.region'): [
        ('Who lives the furthest south?', 'מי גר/ה הכי דרומה?'),
        ('Which of you lives in the southernmost town?', 'מי מכם גר/ה ביישוב הכי דרומי?'),
    ],
    ('closest_pair', 'place.region'): [
        ('Which two people live closest to each other?', 'איזה זוג גר הכי קרוב אחד לשני?'),
        ('Which pair of you lives the shortest distance apart?', 'אילו שניים מכם גרים הכי קרוב זה לזה?'),
    ],
    ('outlier', 'place.region'): [
        ('Who lives furthest from the rest of the group?', 'מי גר/ה הכי רחוק משאר הקבוצה?'),
        ('Whose town is the farthest from everyone else’s?', 'היישוב של מי הכי רחוק מכל השאר?'),
    ],
}

# How a subgroup is introduced, and what is asked about it.
# "Everyone except one", "who else shares this" and "who chose both".
EXCEPTIONS = {
    'movie.genre': ('Everyone here chose {items} — except one person. Who?', 'כולם כאן בחרו {items} — חוץ מאדם אחד. מי?'),
    'food.cuisine': ('Everyone here chose {items} — except one person. Who?', 'כולם כאן בחרו {items} — חוץ מאדם אחד. מי?'),
    'food.format': ('Everyone here chose {items} — except one person. Who?', 'כולם כאן בחרו {items} — חוץ מאדם אחד. מי?'),
    'hobby.family': ('Everyone here chose {items} — except one person. Who?', 'כולם כאן בחרו {items} — חוץ מאדם אחד. מי?'),
    'hobby.setting': ('Everyone here chose {items} — except one person. Who?', 'כולם כאן בחרו {items} — חוץ מאדם אחד. מי?'),
    'hobby.physical': ('Everyone here chose {items} — except one person. Who?', 'כולם כאן בחרו {items} — חוץ מאדם אחד. מי?'),
    'music.genre': ('Everyone here chose {items} — except one person. Who?', 'כולם כאן בחרו {items} — חוץ מאדם אחד. מי?'),
    'place.region': ('Everyone here lives {in} — except one person. Who?', 'כולם כאן גרים {in} — חוץ מאדם אחד. מי?'),
    'age.band': ('Everyone who shared an age is {items} — except one person. Who?', 'כל מי ששיתף גיל הוא {items} — חוץ מאדם אחד. מי?'),
}
UNANIMITY = {
    'movie.genre': ('Every movie you chose shares one thing. What?', 'מה משותף לכל הסרטים שבחרתם?'),
    'food.cuisine': ('Every dish you chose shares one thing. What?', 'מה משותף לכל המאכלים שבחרתם?'),
    'food.format': ('Every dish you chose shares one thing. What?', 'מה משותף לכל המאכלים שבחרתם?'),
    'hobby.family': ('Every hobby you chose shares one thing. What?', 'מה משותף לכל התחביבים שבחרתם?'),
    'hobby.setting': ('Every hobby you chose shares one thing. What?', 'מה משותף לכל התחביבים שבחרתם?'),
    'hobby.physical': ('Every hobby you chose shares one thing. What?', 'מה משותף לכל התחביבים שבחרתם?'),
    'music.genre': ('Every music choice here shares one thing. What?', 'מה משותף לכל בחירות המוזיקה שלכם?'),
    'place.region': ('Everyone here shares one thing about where they live. What?', 'מה משותף לכולכם מבחינת מקום המגורים?'),
}
PARTNERS = {
    'movie.genre': ('{name} chose “{choice}”. Who else picked a movie from the same genre?',
                    '{name} בחר/ה את ״{choice}״. מי עוד בחר/ה סרט מאותו ז׳אנר?'),
    'food.cuisine': ('{name} chose {choice}. Who else picked a dish from the same cuisine?',
                     '{name} בחר/ה {choice}. מי עוד בחר/ה מאכל מאותו מטבח?'),
    'food.format': ('{name} chose {choice}. Who else picked the same kind of dish?',
                    '{name} בחר/ה {choice}. מי עוד בחר/ה מנה מאותו סוג?'),
    'hobby.family': ('{name} chose {choice}. Who else picked a hobby of the same kind?',
                     '{name} בחר/ה {choice}. מי עוד בחר/ה תחביב מאותו סוג?'),
    'artist.genre': ('{name} chose {choice}. Who else picked an artist of the same style?',
                     '{name} בחר/ה את {choice}. מי עוד בחר/ה אמן/ית מאותו סגנון?'),
}
BOTH = {
    'place.region': ('Who here lives {in_a} and also chose {item_b}?', 'מי מכם גר/ה {in_a} וגם בחר/ה {item_b}?'),
    None: ('Who here chose both {item_a} and {item_b}?', 'מי מכם בחר/ה גם {item_a} וגם {item_b}?'),
}
SUBGROUP_CONDITIONS = {
    'movie.genre': ('Among people who chose {items}', 'מבין מי שבחרו {items}'),
    'food.cuisine': ('Among people who chose {items}', 'מבין מי שבחרו {items}'),
    'hobby.family': ('Among people with {item}', 'מבין מי שבחרו {item}'),
    'music.genre': ('Among people who chose {items}', 'מבין מי שבחרו {items}'),
    'artist.genre': ('Among people who chose artists associated with {items}', 'מבין מי שבחרו אמנים שמזוהים עם {items}'),
    'song.genre': ('Among people who chose songs in the {style} style', 'מבין מי שבחרו שירים בסגנון {style}'),
    'place.region': ('Among people who live in {in}', 'מבין מי שגרים {in}'),
    'age.band': ('Among {items}', 'מבין {items}'),
    'food.format': ('Among people who chose {items}', 'מבין מי שבחרו {items}'),
}
SUBGROUP_QUESTIONS = {
    'hobby.family': ('which type of hobby is the most common?', 'איזה סוג תחביב הכי נפוץ?'),
    'movie.genre': ('which genre leads their movie choices?', 'איזה ז׳אנר הכי נפוץ בסרטים שבחרו?'),
    'artist.genre': ('which genre leads their artist choices?', 'איזה סגנון הכי נפוץ באמנים שבחרו?'),
    'song.genre': ('which genre leads their song choices?', 'איזה סגנון הכי נפוץ בשירים שבחרו?'),
    'food.cuisine': ('which cuisine is the favorite?', 'איזה מטבח הכי אהוב?'),
    'place.region': ('which region do the most come from?', 'מאיזה אזור בארץ מגיעים הכי הרבה?'),
    'music.genre': ('which music style is the most common?', 'איזה סגנון מוזיקה הכי נפוץ?'),
}
SUBGROUP_COMPARISONS = {
    'hobby.family': ('which is more common — {items_a} or {items_b}?', 'מה יותר נפוץ — {items_a} או {items_b}?'),
    'movie.genre': ('which genre is more common — {a} or {b}?', 'איזה ז׳אנר יותר נפוץ — {a} או {b}?'),
    'artist.genre': ('which style appears more in their chosen artists — {a} or {b}?', 'איזה סגנון מופיע יותר באמנים שבחרו — {a} או {b}?'),
    'song.genre': ('which style appears more in their chosen songs — {a} or {b}?', 'איזה סגנון מופיע יותר בשירים שבחרו — {a} או {b}?'),
    'food.cuisine': ('which is more popular — {a} or {b} food?', 'מה יותר אהוב — אוכל {a} או {b}?'),
    'place.region': ('where do more of them come from — {from_a} or {from_b}?', 'מאיפה מגיעים יותר — {from_a} או {from_b}?'),
    'hobby.setting': ('which is more common — outdoor hobbies or indoor hobbies?', 'מה יותר נפוץ — תחביבי חוץ או תחביבי בית?'),
}
INTERSECTIONS = {
    'place.region': ('How many people live in {in_a} and chose {item_b}?', 'כמה אנשים גרים {in_a} ובחרו {item_b}?'),
    None: ('How many people chose both {item_a} and {item_b}?', 'כמה אנשים בחרו גם {item_a} וגם {item_b}?'),
}

# Nouns used in explanations: (singular kind, plural kind, recognized-answers noun).
NOUNS = {
    'movie.genre': (('genre', 'ז׳אנר'), ('genres', 'ז׳אנרים'), ('movies chosen', 'סרטים')),
    'food.cuisine': (('cuisine', 'מטבח'), ('cuisines', 'מטבחים'), ('dishes chosen', 'מאכלים')),
    'hobby.family': (('type of hobby', 'סוג תחביב'), ('types of hobbies', 'סוגי תחביבים'), ('hobbies chosen', 'תחביבים')),
    'hobby.physical': (('kind of hobby', 'סוג תחביב'), ('kinds of hobbies', 'סוגי תחביבים'), ('hobbies chosen', 'תחביבים')),
    'hobby.setting': (('kind of hobby', 'סוג תחביב'), ('kinds of hobbies', 'סוגי תחביבים'), ('hobbies chosen', 'תחביבים')),
    'music.genre': (('style', 'סגנון'), ('styles', 'סגנונות'), ('music choices', 'בחירות מוזיקה')),
    'artist.genre': (('style', 'סגנון'), ('styles', 'סגנונות'), ('artists chosen', 'אמנים')),
    'song.genre': (('style', 'סגנון'), ('styles', 'סגנונות'), ('songs chosen', 'שירים')),
    'place.region': (('region', 'אזור'), ('regions', 'אזורים'), ('towns', 'יישובים')),
    'food.format': (('kind of dish', 'סוג מנה'), ('kinds of dishes', 'סוגי מנות'), ('dishes chosen', 'מאכלים')),
    'hobby.making_music': (('kind of hobby', 'סוג תחביב'), ('kinds of hobbies', 'סוגי תחביבים'),
                           ('hobbies chosen', 'תחביבים')),
    'age.band': (('age range', 'טווח גילים'), ('age ranges', 'טווחי גיל'), ('ages shared', 'גילים')),
}

# The subject a whole-group comparison is about ("where do you agree most?").
TOPIC_LABELS = {
    'movie': ('movies', 'סרטים'), 'food': ('food', 'אוכל'), 'hobby': ('hobbies', 'תחביבים'),
    'music': ('music', 'מוזיקה'), 'artist': ('favorite artists', 'אמנים אהובים'),
    'song': ('favorite songs', 'שירים אהובים'), 'place': ('where you live', 'מקום המגורים'),
    'age': ('age', 'גיל'),
}


def stable_index(key, size: int) -> int:
    """The same variant for the same discovery in every language and process."""
    return zlib.crc32(repr(key).encode('utf-8')) % size


class Wording:
    """Renders categories, questions and explanations for one game language."""

    def __init__(self, language: str, knowledge) -> None:
        self.language = language
        self.he = language == 'he'
        self.knowledge = knowledge

    def text(self, en: str, he: str, **values) -> str:
        return say(self.language, en, he, **values)

    def term(self, category: str, domain: str) -> Term:
        term = LEXICON.get(category)
        if term is None:
            term = _fallback(self.knowledge.categories[category], domain)
        return term

    def forms(self, category: str, domain: str, suffix: str = '') -> dict[str, str]:
        term = self.term(category, domain)
        pick = (lambda en, he: he if self.he else en)
        forms = {
            'label': pick(term.en, term.he), 'items': pick(term.en_items, term.he_items),
            'style': pick(term.en, {'music.electronic': 'אלקטרוני', 'music.classical': 'קלאסי',
                                   'music.mizrahi': 'מזרחי', 'music.mediterranean': 'ים תיכוני',
                                   'music.latin': 'לטיני', 'music.jewish': 'יהודי'}.get(category, term.he)),
            'item': pick(term.en_item, term.he_item), 'fans': pick(term.en_fans, term.he_fans),
            'fan': pick(term.en_fans[:-1] if term.en_fans.endswith('s') else term.en_fans, term.he_fans),
            'def': term.he_def or term.he, 'topic': pick(term.en_topic, term.he_topic),
            'from': pick(term.en_from, term.he_from), 'in': pick(term.en_in, term.he_in),
        }
        return {f'{name}{suffix}': value for name, value in forms.items()}

    def variants(self, operation: str, dimension: str) -> list[tuple[str, str]]:
        return TEMPLATES[(operation, dimension)]

    def render(self, template: tuple[str, str], **values) -> str:
        return self.text(template[0], template[1], **values)

    def question(self, operation: str, dimension, fact, categories=(), **values) -> str:
        # Definite adjective forms exist only for curated categories; the
        # filter looks at both renderings so both languages keep one variant list.
        curated = all(c in LEXICON for c in categories)
        options = [pair for pair in self.variants(operation, dimension)
                   if curated or '{def' not in pair[1]]
        return self.render(options[stable_index(fact, len(options))], **values)

    # ----- explanation helpers -------------------------------------------------

    def people(self, n: int) -> str:
        if n == 1:
            return self.text('one person', 'אדם אחד')
        return self.text('{n} people', '{n} אנשים', n=n)

    def join(self, labels) -> str:
        labels = list(labels)
        if len(labels) < 2:
            return ''.join(labels)
        last = self.text(' and {x}', ' ו{x}', x=labels[-1])
        return ', '.join(labels[:-1]) + last

    def evidence(self, summary, people, limit: int = 3) -> str:
        labels = list(dict.fromkeys(summary.evidence_label(p, self.language) for p in people))
        shown = ', '.join(labels[:limit])
        extra = len(labels) - limit
        if extra > 0:
            shown += self.text(' and {n} more', ' ועוד {n}', n=extra)
        return shown

    def coverage_note(self, summary) -> str:
        if not summary.unknown:
            return ''
        noun = NOUNS[summary.dimension.key][2]
        return ' ' + self.text('{r} of the {c} {noun} were recognized.', 'זוהו {r} מתוך {c} {noun}.',
                               r=len(summary.recognized), c=len(summary.consented),
                               noun=noun[1] if self.he else noun[0])

    def answers_noun(self, dimension: str) -> str:
        """What the recognized answers are called: "movies", "dishes", "hobbies"."""
        noun = NOUNS[dimension][2]
        return noun[1] if self.he else noun[0]

    def kind(self, dimension: str, plural: bool = False) -> str:
        noun = NOUNS[dimension][1 if plural else 0]
        return noun[1] if self.he else noun[0]
