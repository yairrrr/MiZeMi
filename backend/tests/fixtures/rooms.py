"""Realistic synthetic rooms for engine diagnostics, style audits and tests.

All names and answers are fictional. Values are typed the way Israeli
classrooms actually answer: Hebrew titles, spelling variants, unknown local
films, skipped optional fields and per-field consent choices. The module only
depends on the stable ``Player``/``PlayerProfile`` domain types, so the
diagnostic script can load it against older engine revisions too.
"""

from dataclasses import dataclass

from app.domain.game import Player, PlayerProfile, ProfileField
from app.domain.questions.dataset import ProfileDataset

HE_NAMES = ('דנה', 'עומר', 'נועה', 'עמית', 'ליאור', 'יעל', 'איתי', 'רוני', 'מאיה', 'יונתן',
            'תמר', 'אורי', 'שירה', 'דניאל', 'מיכל', 'איתן', 'הילה', 'נדב', 'גל', 'אביב',
            'שחר', 'ענבל', 'רועי', 'אלה', 'בן', 'טל', 'עדי', 'ים', 'אריאל', 'נגה')
EN_NAMES = ('Dana', 'Omer', 'Noa', 'Amit', 'Lior', 'Yael', 'Itay', 'Roni', 'Maya', 'Jonathan',
            'Tamar', 'Uri', 'Shira', 'Daniel', 'Michal', 'Eitan', 'Hila', 'Nadav', 'Gal', 'Aviv',
            'Shahar', 'Inbal', 'Roy', 'Ella', 'Ben', 'Tal', 'Adi', 'Yam', 'Ariel', 'Noga')

FIELD_ORDER = ('city', 'favorite_food', 'hobby', 'favorite_music', 'age', 'favorite_movie',
               'favorite_artist', 'favorite_song', 'personal_fact')


def P(city, food, hobby, music, movie=None, age=None, *, artist=None, song=None, fact=None, hide=()):
    """One profile row; ``None`` means the optional field was skipped."""
    values = {'city': city, 'favorite_food': food, 'hobby': hobby, 'favorite_music': music,
              'age': age, 'favorite_movie': movie, 'favorite_artist': artist,
              'favorite_song': song, 'personal_fact': fact}
    return {'values': {k: v for k, v in values.items() if v is not None}, 'hide': tuple(hide)}


@dataclass(frozen=True)
class Room:
    name: str
    language: str
    rows: tuple
    description: str = ''

    def players(self) -> list[Player]:
        names = HE_NAMES if self.language == 'he' else EN_NAMES
        players = []
        for index, row in enumerate(self.rows):
            pid = f'p{index + 1:02d}'
            fields = tuple(
                ProfileField(key, row['values'][key], key not in row['hide'])
                for key in FIELD_ORDER if key in row['values']
            )
            players.append(Player(pid, names[index], profile=PlayerProfile(pid, fields)))
        return players

    def dataset(self, language: str | None = None) -> ProfileDataset:
        return ProfileDataset(self.players(), language=language or self.language)


HE_RICH = Room('he_rich', 'he', (
    P('חיפה', 'פיצה', 'ריצה', 'Mizrahi', 'המסור', 17),
    P('תל אביב', 'סושי', 'כדורגל', 'Pop', 'מטריקס', 16, artist='נועה קירל'),
    P('רמת גן', 'פסטה', 'ציור', 'Rock', 'לזמן את הרוע', 17),
    P('באר שבע', 'חומוס', 'גלישה', 'Mizrahi', 'בחזרה לעתיד', 16, artist='עומר אדם'),
    P('קרית שמונה', 'לזניה', 'גיימינג', 'Hip-Hop / Rap', 'פארק היורה', 17),
    P('פתח תקווה', 'פלאפל', 'פילאטיס', 'Pop', 'שרק', 16),
    P('ראשון לציון', 'ראמן', 'צילום', 'Electronic', 'צעצוע של סיפור'),
    P('נהריה', 'שווארמה', 'כדורסל', 'Mizrahi', 'הסנדק', 17, hide=('city',)),
    P('רחובות', 'המבורגר', 'גיטרה', 'Rock', 'פורסט גאמפ', 16, artist='Coldplay'),
    P('אילת', 'ספגטי', 'שחייה', 'Pop', None, 17),
    P('נתניה', 'שניצל', 'קריאה', 'Israeli Pop', 'שכחו אותי בבית', 16),
    P('עכו', 'טאקו', 'חדר כושר', 'Mizrahi', 'ג׳וקר', 17),
    P('כפר סבא', 'פאד תאי', 'בישול', 'Pop', 'האביר האפל', 16),
    P('ירושלים', 'שקשוקה', 'טיולים', 'Rock', 'מוצאים את נמו', 17),
    P('הרצליה', 'סלט', 'יוגה', 'Trance', 'אסקימו לימון', 16, fact='אני מגדלת זוחלים', hide=('personal_fact',)),
    P('אשדוד', 'ריזוטו', 'שחמט', 'Hip-Hop / Rap', 'הנוקמים: סוף המשחק', 17),
    P('חולון', 'גלידה', 'כדורגל', 'Pop', 'לה לה לנד', 16, hide=('favorite_movie',)),
    P('כרמיאל', 'קוסקוס', 'מדיטציה', 'Other', 'בדרך לחתונה עוצרים בווגאס', 17),
    P('אשקלון', 'פיצה', 'אפייה', 'Mizrahi', None),
    P('בית שמש', 'סושי', 'ריצה', 'Electronic', 'מלחמת הכוכבים', 16),
), 'Hebrew classroom: realistic spellings, a few unknown or skipped answers and consent choices.')

EN_RICH = Room('en_rich', 'en', (
    P('Haifa', 'Pizza', 'Running', 'Pop', 'Saw', 24),
    P('Tel Aviv', 'Sushi', 'Football', 'Rock', 'The Matrix', 25, artist='Taylor Swift'),
    P('Ramat Gan', 'Pasta', 'Painting', 'Pop', 'The Conjuring', 23),
    P('Beersheba', 'Hummus', 'Surfing', 'Mizrahi', 'Back to the Future', 26, artist='Coldplay'),
    P('Kiryat Shmona', 'Lasagna', 'Gaming', 'Hip-Hop / Rap', 'Jurassic Park', 27),
    P('Petah Tikva', 'Falafel', 'Pilates', 'Electronic', 'Shrek', 24),
    P('Rishon LeZion', 'Ramen', 'Photography', 'Rock', 'Toy Story'),
    P('Nahariya', 'Burger', 'Basketball', 'Pop', 'The Godfather', 25, hide=('city',)),
    P('Rehovot', 'Nachos', 'Guitar', 'Jazz', 'Forrest Gump', 28, artist='Eminem'),
    P('Eilat', 'Spaghetti', 'Swimming', 'Pop', None, 22),
    P('Netanya', 'Schnitzel', 'Reading', 'Indie', 'Home Alone', 24),
    P('Acre', 'Burrito', 'Gym', 'Mizrahi', 'Joker', 26),
    P('Herzliya', 'Pad Thai', 'Cooking', 'Pop', 'The Dark Knight', 25),
    P('Jerusalem', 'Falafel', 'Hiking', 'Rock', 'Finding Nemo', 29),
    P('Holon', 'Salad', 'Yoga', 'Trance', 'Some indie short film', 23),
    P('Ashdod', 'Paella', 'Chess', 'Hip-Hop / Rap', 'Iron Man', 27),
    P('Tiberias', 'Ice cream', 'Football', 'Pop', 'La La Land', 24, hide=('favorite_movie',)),
    P('Safed', 'Pizza', 'Meditation', 'Other', 'The Hangover', 26),
    P('Ashkelon', 'Bibimbap', 'Baking', 'Rock', None),
    P('Jerusalem', 'Sushi', 'Running', 'Electronic', 'Star Wars', 25),
), 'English classroom with the same realistic gaps as he_rich.')

CURATED_COMPLETE = Room('curated_complete', 'he', (
    P('חיפה', 'פיצה', 'ריצה', 'Mizrahi', 'המסור', 17),
    P('תל אביב', 'סושי', 'כדורגל', 'Pop', 'מטריקס', 16),
    P('רמת גן', 'פסטה', 'ציור', 'Rock', 'לזמן את הרוע', 17),
    P('באר שבע', 'חומוס', 'גלישה', 'Mizrahi', 'בחזרה לעתיד', 16),
    P('קריית שמונה', 'ספגטי', 'גיימינג', 'Pop', 'פארק היורה', 17),
    P('פתח תקווה', 'פלאפל', 'פילאטיס', 'Pop', 'שרק', 16),
    P('ראשון לציון', 'ראמן', 'צילום', 'Electronic', 'צעצוע של סיפור', 17),
    P('נהריה', 'שווארמה', 'כדורסל', 'Mizrahi', 'הסנדק', 16),
    P('רחובות', 'המבורגר', 'גיטרה', 'Rock', 'פורסט גאמפ', 17),
    P('אילת', 'ריזוטו', 'שחייה', 'Pop', 'שכחו אותי בבית', 16),
    P('נתניה', 'פאייה', 'קריאה', 'Mizrahi', 'ג׳וקר', 17),
    P('עכו', 'טאקו', 'חדר כושר', 'Rock', 'האביר האפל', 16),
    P('כפר סבא', 'פאד תאי', 'שחמט', 'Pop', 'מוצאים את נמו', 17),
    P('ירושלים', 'שקשוקה', 'טיולים', 'Mizrahi', 'לה לה לנד', 16),
    P('הרצליה', 'ניוקי', 'מדיטציה', 'Trance', 'הניצוץ', 17),
    P('אשדוד', 'מג׳דרה', 'טניס', 'Pop', 'הנוקמים: סוף המשחק', 16),
    P('חולון', 'פיצה', 'פסנתר', 'Rock', 'למעלה', 17),
    P('כרמיאל', 'חביתה', 'סריגה', 'Mizrahi', 'בדרך לחתונה עוצרים בווגאס', 16),
    P('אשקלון', 'סושי', 'תכנות', 'Electronic', 'תברח', 17),
    P('ירושלים', 'פסטה', 'ריצה', 'Pop', 'היומן', 16),
), 'Every answer resolves in every dimension; isolates selection from recognition.')

UNKNOWN_HEAVY = Room('unknown_heavy', 'he', (
    P('חיפה', 'שניצל', 'ריצה', 'Pop', 'המסור', 17),
    P('תל אביב', 'סטייק', 'כדורגל', 'Pop', 'לזמן את הרוע', 16),
    P('רמת גן', 'אורז', 'ציור', 'Rock', 'הניצוץ', 17),
    P('באר שבע', 'צ׳ולנט', 'יוגה', 'Mizrahi', 'מטריקס', 16),
    P('חיפה', 'קבב', 'גיימינג', 'Other', 'סרט של אבא שלי', 17),
    P('נתניה', 'דג', 'טרקים', 'Pop', 'הסרט מהקיץ', 16),
    P('עכו', 'סמבוסק', 'נגינה', 'Rock', 'משהו עם זומבים', 17),
    P('אילת', 'באגט', 'אופניים', 'Mizrahi', 'לא זוכרת את השם', 16),
    P('רחובות', 'מנגל', 'סרטים', 'Pop', 'הסרט הישראלי ההוא', 17),
    P('אשדוד', 'בורשט', 'מוזיקה', 'Other', 'סדרה ולא סרט', 16),
    P('חולון', 'שניצל', 'ריצה', 'Pop', 'אנימה כלשהי', 17),
    P('כפר סבא', 'קבב', 'כדורגל', 'Rock', 'שובר קופות', 16),
    P('ירושלים', 'סטייק', 'לשיר', 'Mizrahi', 'הראשון שראיתי', 17),
    P('הרצליה', 'דג', 'יוגה', 'Pop', 'קומדיה צרפתית', 16),
    P('אשקלון', 'אורז', 'טרקים', 'Pop', 'סרט טורקי', 17),
    P('נהריה', 'צ׳ולנט', 'אופניים', 'Rock', 'הסרט עם הכלב', 16),
    P('כרמיאל', 'באגט', 'גיימינג', 'Mizrahi', 'דוקו על טבע', 17),
    P('רעננה', 'מנגל', 'ציור', 'Pop', 'סרט אימה מקוריאה', 16),
    P('מודיעין', 'סמבוסק', 'נגינה', 'Other', 'קלאסיקה ישנה', 17),
    P('גבעתיים', 'בורשט', 'לשיר', 'Pop', 'מה שהיה בנטפליקס', 16),
), 'Twenty movie answers but only four are recognized; most foods are unknown too.')

SPARSE = Room('sparse', 'he', (
    P('חיפה', 'פיצה', 'ריצה', 'Pop'),
    P('תל אביב', 'סושי', 'ציור', 'Rock'),
    P('באר שבע', 'חומוס', 'כדורגל', 'Pop'),
    P('ירושלים', 'שניצל', 'קריאה', 'Mizrahi'),
    P('נתניה', 'פסטה', 'גיימינג', 'Pop'),
    P('עכו', 'סלט', 'שחייה', 'Other'),
), 'Six players, required fields only, a couple of unknown answers.')

AUDIT_NEW_CLASS = Room('audit_new_class', 'he', (
    P('תל אביב', 'פיצה', 'ריצה', 'Mizrahi', 'המסור', 20),
    P('רמת גן', 'פסטה', 'כדורגל', 'Pop', 'לזמן את הרוע', 22),
    P('ראשון לציון', 'לזניה', 'גלישה', 'Rock', 'שרק', 24),
    P('חיפה', 'סושי', 'גיימינג', 'Mizrahi', 'טיטניק (סרט, 1997)', 21),
    P('באר שבע', 'פלאפל', 'גינון', 'Trance', 'שרק 2', 23),
), 'The five-player group from the previous style audit.')

MOVIE_HEAVY = Room('movie_heavy', 'he', (
    P('תל אביב', 'פיצה', 'ריצה', 'Pop', 'המסור', 16),
    P('רמת גן', 'סושי', 'ציור', 'Rock', 'לזמן את הרוע', 17),
    P('חולון', 'פסטה', 'גיימינג', 'Pop', 'הניצוץ', 16),
    P('חיפה', 'חומוס', 'כדורגל', 'Mizrahi', 'תברח', 17),
    P('נתניה', 'פלאפל', 'צילום', 'Pop', 'מטריקס', 16),
    P('ירושלים', 'המבורגר', 'קריאה', 'Rock', 'בחזרה לעתיד', 17),
    P('באר שבע', 'שווארמה', 'שחייה', 'Mizrahi', 'פארק היורה', 16),
    P('רחובות', 'ראמן', 'גיטרה', 'Pop', 'אינספשן', 17),
    P('הרצליה', 'לזניה', 'כדורסל', 'Electronic', 'שרק', 16),
    P('אשדוד', 'שקשוקה', 'בישול', 'Pop', 'צעצוע של סיפור', 17),
    P('עכו', 'פיצה', 'פילאטיס', 'Mizrahi', 'מוצאים את נמו', 16),
    P('כפר סבא', 'טאקו', 'שחמט', 'Rock', 'למעלה', 17),
    P('פתח תקווה', 'סושי', 'ריצה', 'Pop', 'בדרך לחתונה עוצרים בווגאס', 16),
    P('מודיעין', 'פסטה', 'ציור', 'Hip-Hop / Rap', 'שכחו אותי בבית', 17),
    P('ראשון לציון', 'חומוס', 'טיולים', 'Pop', 'היומן', 16),
    P('אילת', 'פאייה', 'גלישה', 'Mizrahi', 'לה לה לנד', 17),
), 'Sixteen recognized movies spanning horror, science fiction, animation, comedy and romance.')

HOBBY_HEAVY = Room('hobby_heavy', 'en', (
    P('Haifa', 'Pizza', 'Running', 'Pop'),
    P('Tel Aviv', 'Sushi', 'Football', 'Rock'),
    P('Ramat Gan', 'Falafel', 'Pilates', 'Pop'),
    P('Eilat', 'Pasta', 'Surfing', 'Electronic'),
    P('Netanya', 'Hummus', 'Basketball', 'Pop'),
    P('Jerusalem', 'Burger', 'Tennis', 'Rock'),
    P('Rehovot', 'Ramen', 'Swimming', 'Mizrahi'),
    P('Herzliya', 'Pizza', 'Painting', 'Indie'),
    P('Ashdod', 'Tacos', 'Photography', 'Pop'),
    P('Acre', 'Spaghetti', 'Guitar', 'Rock'),
    P('Holon', 'Sushi', 'Knitting', 'Jazz'),
    P('Tiberias', 'Shawarma', 'Drawing', 'Pop'),
    P('Safed', 'Pad Thai', 'Gaming', 'Electronic'),
    P('Beersheba', 'Paella', 'Hiking', 'Rock'),
    P('Ashkelon', 'Lasagna', 'Chess', 'Mizrahi'),
    P('Petah Tikva', 'Falafel', 'Gym', 'Pop'),
    P('Kfar Saba', 'Pizza', 'Cooking', 'Hip-Hop / Rap'),
    P('Rishon LeZion', 'Hummus', 'Meditation', 'Classical'),
), 'Eighteen different hobbies across sport, creative, digital, outdoor and indoor activities.')

FOOD_HEAVY = Room('food_heavy', 'he', (
    P('חיפה', 'פיצה', 'ריצה', 'Pop', age=24),
    P('תל אביב', 'פסטה', 'ציור', 'Rock', age=25),
    P('ירושלים', 'לזניה', 'כדורגל', 'Mizrahi', age=23),
    P('באר שבע', 'ספגטי', 'גיימינג', 'Pop', age=26),
    P('נתניה', 'ריזוטו', 'קריאה', 'Pop', age=27),
    P('רמת גן', 'סושי', 'שחייה', 'Rock', age=24),
    P('עכו', 'ראמן', 'צילום', 'Electronic', age=25),
    P('אשדוד', 'פאד תאי', 'כדורסל', 'Pop', age=28),
    P('חולון', 'ביבימבאפ', 'גיטרה', 'Mizrahi', age=23),
    P('רחובות', 'חומוס', 'פילאטיס', 'Pop', age=26),
    P('טבריה', 'פלאפל', 'בישול', 'Rock', age=29),
    P('אילת', 'שווארמה', 'גלישה', 'Mizrahi', age=24),
    P('הרצליה', 'המבורגר', 'שחמט', 'Pop', age=25),
    P('כרמיאל', 'טאקו', 'טיולים', 'Hip-Hop / Rap', age=27),
    P('מודיעין', 'פאייה', 'אפייה', 'Pop', age=26),
    P('צפת', 'קוסקוס', 'מדיטציה', 'Mizrahi', age=24),
    P('כפר סבא', 'פיצה', 'טניס', 'Rock', age=28),
    P('אשקלון', 'ניוקי', 'סריגה', 'Pop', age=23),
), 'Italian, Asian, Middle Eastern, American and other cuisines, all recognized.')

GEO_HEAVY = Room('geo_heavy', 'he', (
    P('חיפה', 'פיצה', 'ריצה', 'Pop', 'שרק'),
    P('עכו', 'סושי', 'ציור', 'Mizrahi', 'המסור'),
    P('נהריה', 'פסטה', 'כדורגל', 'Pop', 'מטריקס'),
    P('קרית שמונה', 'חומוס', 'גיימינג', 'Rock', 'צעצוע של סיפור'),
    P('טבריה', 'פלאפל', 'שחייה', 'Mizrahi', 'לזמן את הרוע'),
    P('צפת', 'המבורגר', 'צילום', 'Pop', 'בחזרה לעתיד'),
    P('כרמיאל', 'ראמן', 'גיטרה', 'Pop', 'מוצאים את נמו'),
    P('עפולה', 'שווארמה', 'כדורסל', 'Mizrahi', 'פורסט גאמפ'),
    P('נצרת', 'שקשוקה', 'קריאה', 'Rock', 'הסנדק'),
    P('תל אביב', 'לזניה', 'פילאטיס', 'Pop', 'ג׳וקר'),
    P('רמת גן', 'טאקו', 'בישול', 'Electronic', 'האביר האפל'),
    P('פתח תקווה', 'ספגטי', 'גלישה', 'Pop', 'שכחו אותי בבית'),
    P('באר שבע', 'פאד תאי', 'טיולים', 'Mizrahi', 'לה לה לנד'),
    P('אילת', 'ריזוטו', 'שחמט', 'Pop', 'היומן'),
    P('ירושלים', 'פיצה', 'מדיטציה', 'Rock', 'למעלה'),
), 'A clear northern majority, with the center, the south and Jerusalem also represented.')

MIXED_EN = Room('mixed_en', 'en', (
    P('Haifa', 'Pizza', 'Running', 'Pop', 'Saw', 30, artist='Taylor Swift', song='Blank Space'),
    P('Tel Aviv', 'Sushi', 'Painting', 'Rock', 'The Matrix', 34, artist='Coldplay', song='Yellow - Coldplay'),
    P('Jerusalem', 'Hummus', 'Football', 'Mizrahi', 'Toy Story', 29, artist='Omer Adam'),
    P('Beersheba', 'Pasta', 'Gaming', 'Pop', 'The Conjuring', 41, artist='Dua Lipa'),
    P('Netanya', 'Falafel', 'Guitar', 'Rock', 'Back to the Future', 36, artist='Metallica', song='Enter Sandman'),
    P('Eilat', 'Ramen', 'Surfing', 'Electronic', 'Finding Nemo', 27, artist='Avicii'),
    P('Rehovot', 'Burger', 'Reading', 'Pop', 'La La Land', 33, artist='Ed Sheeran'),
    P('Acre', 'Lasagna', 'Swimming', 'Mizrahi', 'The Godfather', 38, artist='Eden Ben Zaken'),
    P('Herzliya', 'Pad Thai', 'Photography', 'Pop', 'Jurassic Park', 31, artist='Bruno Mars'),
    P('Ashdod', 'Shawarma', 'Chess', 'Rock', 'Shrek', 35, artist='Queen'),
    P('Holon', 'Tacos', 'Cooking', 'Jazz', 'Home Alone', 28),
    P('Ashkelon', 'Pizza', 'Hiking', 'Pop', 'Inception', 32, artist='The Weeknd'),
), 'A mixed English room with artists and songs where shared.')

CONSENT_RESTRICTED = Room('consent_restricted', 'he', (
    P('חיפה', 'פיצה', 'ריצה', 'Pop', 'המסור', 17, hide=('favorite_movie', 'city')),
    P('תל אביב', 'סושי', 'כדורגל', 'Rock', 'מטריקס', 16, hide=('favorite_food',)),
    P('רמת גן', 'פסטה', 'ציור', 'Pop', 'לזמן את הרוע', 17, hide=('hobby', 'age')),
    P('באר שבע', 'חומוס', 'גלישה', 'Mizrahi', 'בחזרה לעתיד', 16, hide=('city',)),
    P('עכו', 'לזניה', 'גיימינג', 'Pop', 'שרק', 17, hide=('favorite_movie',)),
    P('נתניה', 'פלאפל', 'פילאטיס', 'Rock', 'צעצוע של סיפור', 16),
    P('ירושלים', 'ראמן', 'צילום', 'Mizrahi', 'הסנדק', 17, hide=('favorite_music',)),
    P('נהריה', 'שווארמה', 'כדורסל', 'Pop', 'פורסט גאמפ', 16, hide=('favorite_food', 'hobby')),
    P('רחובות', 'המבורגר', 'גיטרה', 'Rock', 'ג׳וקר', 17),
    P('אילת', 'ספגטי', 'שחייה', 'Pop', 'האביר האפל', 16, hide=('city', 'favorite_movie')),
    P('כפר סבא', 'פאד תאי', 'בישול', 'Mizrahi', 'מוצאים את נמו', 17),
    P('הרצליה', 'שקשוקה', 'טיולים', 'Pop', 'לה לה לנד', 16, hide=('favorite_music', 'age')),
    P('אשדוד', 'ריזוטו', 'שחמט', 'Rock', 'למעלה', 17, hide=('hobby',)),
    P('חולון', 'פיצה', 'מדיטציה', 'Pop', 'שכחו אותי בבית', 16, hide=('favorite_food',)),
), 'Many players withheld one or two fields from questions.')

DIAGNOSTIC_ROOMS = (HE_RICH, EN_RICH, CURATED_COMPLETE, UNKNOWN_HEAVY, SPARSE, AUDIT_NEW_CLASS)
AUDIT_ROOMS = (HE_RICH, EN_RICH, MOVIE_HEAVY, HOBBY_HEAVY, FOOD_HEAVY, GEO_HEAVY, MIXED_EN, SPARSE,
               UNKNOWN_HEAVY, CONSENT_RESTRICTED)
