"""Twenty varied synthetic rooms for the question-variety diversity report.

Each room is a different kind of real group — a school class, a workplace
team, a sports club, an art studio, a family gathering — so the report shows
how the engine behaves across group shapes, sizes, languages, age spreads and
optional-field coverage. All names and answers are fictional.
"""

from random import Random

from tests.fixtures.rooms import P, Room

HE_CITIES = ('חיפה', 'תל אביב', 'רמת גן', 'באר שבע', 'נתניה', 'ירושלים', 'עכו', 'אילת', 'רחובות',
             'חולון', 'הרצליה', 'אשדוד', 'כפר סבא', 'פתח תקווה', 'נהריה', 'אשקלון', 'צפת',
             'ראשון לציון', 'כרמיאל', 'בית שמש', 'טבריה', 'מודיעין', 'רעננה', 'גבעתיים')
EN_CITIES = ('Haifa', 'Tel Aviv', 'Ramat Gan', 'Beersheba', 'Netanya', 'Jerusalem', 'Acre', 'Eilat',
             'Rehovot', 'Holon', 'Herzliya', 'Ashdod', 'Kfar Saba', 'Petah Tikva', 'Nahariya',
             'Ashkelon', 'Safed', 'Rishon LeZion', 'Karmiel', 'Beit Shemesh', 'Tiberias', 'Modiin')
HE_FOODS = ('פיצה', 'סושי', 'פסטה', 'חומוס', 'לזניה', 'פלאפל', 'ראמן', 'שווארמה', 'המבורגר',
            'ספגטי', 'שניצל', 'טאקו', 'פאד תאי', 'שקשוקה', 'סלט', 'ריזוטו', 'גלידה', 'קוסקוס',
            'פאייה', 'ניוקי', 'מג׳דרה', 'בורקס', 'סביח', 'מרק עוף', 'ביבימבאפ', 'צ׳יזבורגר')
EN_FOODS = ('Pizza', 'Sushi', 'Pasta', 'Hummus', 'Lasagna', 'Falafel', 'Ramen', 'Shawarma', 'Burger',
            'Spaghetti', 'Schnitzel', 'Tacos', 'Pad Thai', 'Shakshuka', 'Salad', 'Risotto',
            'Ice cream', 'Couscous', 'Paella', 'Gnocchi', 'Bibimbap', 'Burrito', 'Nachos', 'Curry')
HE_SPORT = ('ריצה', 'כדורגל', 'גלישה', 'שחייה', 'כדורסל', 'פילאטיס', 'יוגה', 'חדר כושר', 'טניס', 'אופניים')
HE_CREATIVE = ('ציור', 'צילום', 'גיטרה', 'בישול', 'אפייה', 'סריגה', 'פסנתר', 'ריקוד', 'כתיבה')
HE_INDOOR = ('גיימינג', 'קריאה', 'שחמט', 'תכנות', 'מדיטציה', 'פאזלים', 'צפייה בסרטים')
HE_OUTDOOR = ('טיולים', 'קמפינג', 'דיג', 'גינון')
EN_SPORT = ('Running', 'Football', 'Surfing', 'Swimming', 'Basketball', 'Pilates', 'Yoga', 'Gym', 'Tennis')
EN_CREATIVE = ('Painting', 'Photography', 'Guitar', 'Cooking', 'Baking', 'Knitting', 'Piano', 'Dancing')
EN_INDOOR = ('Gaming', 'Reading', 'Chess', 'Programming', 'Meditation', 'Puzzles')
EN_OUTDOOR = ('Hiking', 'Camping', 'Fishing', 'Gardening')
MUSIC = ('Pop', 'Rock', 'Mizrahi', 'Hip-Hop / Rap', 'Electronic', 'Jazz', 'Israeli Pop', 'Trance',
         'Indie', 'Classical', 'R&B', 'Other')
HE_MOVIES = ('המסור', 'מטריקס', 'לזמן את הרוע', 'בחזרה לעתיד', 'פארק היורה', 'שרק', 'צעצוע של סיפור',
             'הסנדק', 'פורסט גאמפ', 'שכחו אותי בבית', 'ג׳וקר', 'האביר האפל', 'מוצאים את נמו',
             'לה לה לנד', 'הנוקמים: סוף המשחק', 'מלחמת הכוכבים', 'הניצוץ', 'למעלה', 'תברח', 'היומן')
EN_MOVIES = ('Saw', 'The Matrix', 'The Conjuring', 'Back to the Future', 'Jurassic Park', 'Shrek',
             'Toy Story', 'The Godfather', 'Forrest Gump', 'Home Alone', 'Joker', 'The Dark Knight',
             'Finding Nemo', 'La La Land', 'Iron Man', 'Star Wars', 'The Shining', 'Up', 'Get Out')
HE_ARTISTS = ('עומר אדם', 'נועה קירל', 'עדן בן זקן', 'שלמה ארצי', 'Coldplay', 'Taylor Swift', 'Metallica')
EN_ARTISTS = ('Taylor Swift', 'Coldplay', 'Metallica', 'Eminem', 'Beyoncé', 'Queen', 'Adele')
SONGS = ('Blank Space', 'Yellow - Coldplay', 'Enter Sandman', 'Shake It Off - Taylor Swift',
         'Paradise - Coldplay', 'Bohemian Rhapsody')
HE_FACTS = ('אני מגדלת זוחלים', 'נולדתי בחו״ל', 'אני יודע לנגן בחמישה כלים', 'רצתי מרתון',
            'יש לי תאום', 'אני אוספת בולים')
EN_FACTS = ('I grew up abroad', 'I have a twin', 'I ran a marathon', 'I collect stamps',
            'I play five instruments', 'I once met a film star')


def _row(rng, language, *, hobby_pool, ages, artists=0.0, songs=0.0, facts=0.0, skip=0.0,
         hide=0.0, cities=None, foods=None):
    he = language == 'he'
    city = rng.choice(cities if cities else (HE_CITIES if he else EN_CITIES))
    food = rng.choice(foods if foods else (HE_FOODS if he else EN_FOODS))
    hobby = rng.choice(hobby_pool)
    music = rng.choice(MUSIC)
    movie = None if rng.random() < skip else rng.choice(HE_MOVIES if he else EN_MOVIES)
    age = None if ages is None else rng.randint(*ages)
    artist = rng.choice(HE_ARTISTS if he else EN_ARTISTS) if rng.random() < artists else None
    song = rng.choice(SONGS) if rng.random() < songs else None
    fact = rng.choice(HE_FACTS if he else EN_FACTS) if rng.random() < facts else None
    withheld = ()
    if rng.random() < hide:
        withheld = (rng.choice(('city', 'favorite_movie', 'favorite_food', 'age')),)
    if fact is not None and rng.random() < 0.5:
        withheld = (*withheld, 'personal_fact')
    return P(city, food, hobby, music, movie, age, artist=artist, song=song, fact=fact, hide=withheld)


def _room(name, language, size, seed, description, **kwargs):
    rng = Random(seed)
    return Room(name, language, tuple(_row(rng, language, **kwargs) for _ in range(size)), description)


HE_ALL = (*HE_SPORT, *HE_CREATIVE, *HE_INDOOR, *HE_OUTDOOR)
EN_ALL = (*EN_SPORT, *EN_CREATIVE, *EN_INDOOR, *EN_OUTDOOR)

VARIETY_ROOMS = (
    _room('school_class_he', 'he', 24, 101, 'Ninth-grade class, narrow ages, mixed tastes.',
          hobby_pool=HE_ALL, ages=(14, 15), artists=0.3, songs=0.2, facts=0.3, skip=0.1, hide=0.15),
    _room('school_class_en', 'en', 22, 102, 'English-speaking class, narrow ages.',
          hobby_pool=EN_ALL, ages=(15, 16), artists=0.3, songs=0.2, facts=0.25, skip=0.1, hide=0.15),
    _room('workplace_team_he', 'he', 14, 103, 'Small work team, wide adult ages, same few towns.',
          hobby_pool=HE_ALL, ages=(24, 48), artists=0.5, songs=0.4, facts=0.4, skip=0.15, hide=0.1,
          cities=('תל אביב', 'רמת גן', 'גבעתיים', 'הרצליה')),
    _room('workplace_team_en', 'en', 18, 104, 'Workplace team with a wide age range.',
          hobby_pool=EN_ALL, ages=(23, 55), artists=0.5, songs=0.4, facts=0.35, skip=0.15, hide=0.1),
    _room('sports_club_he', 'he', 20, 105, 'Sports club: hobbies concentrated on sport.',
          hobby_pool=HE_SPORT, ages=(16, 34), artists=0.3, songs=0.2, facts=0.2, skip=0.2, hide=0.1),
    _room('art_studio_en', 'en', 16, 106, 'Art studio: creative hobbies dominate.',
          hobby_pool=EN_CREATIVE, ages=(19, 40), artists=0.6, songs=0.5, facts=0.4, skip=0.1, hide=0.1),
    _room('gamers_he', 'he', 15, 107, 'Gaming group: indoor hobbies, film-heavy.',
          hobby_pool=HE_INDOOR, ages=(17, 29), artists=0.4, songs=0.3, facts=0.3, skip=0.05, hide=0.1),
    _room('family_event_he', 'he', 21, 108, 'Family gathering: very wide ages, shared hometowns.',
          hobby_pool=HE_ALL, ages=(12, 68), artists=0.35, songs=0.25, facts=0.5, skip=0.2, hide=0.2,
          cities=('חיפה', 'קרית שמונה', 'נהריה', 'עכו', 'כרמיאל')),
    _room('north_group_he', 'he', 17, 109, 'Northern group: one region, varied tastes.',
          hobby_pool=HE_ALL, ages=(18, 35), artists=0.4, songs=0.3, facts=0.3, skip=0.15, hide=0.1,
          cities=('חיפה', 'עכו', 'נהריה', 'צפת', 'כרמיאל', 'טבריה', 'קרית שמונה')),
    _room('spread_country_en', 'en', 19, 110, 'People from every region of the country.',
          hobby_pool=EN_ALL, ages=(20, 45), artists=0.4, songs=0.3, facts=0.3, skip=0.15, hide=0.1),
    _room('foodies_he', 'he', 18, 111, 'Food-lovers: wide cuisine spread.',
          hobby_pool=HE_ALL, ages=(22, 44), artists=0.3, songs=0.2, facts=0.3, skip=0.25, hide=0.1,
          foods=HE_FOODS),
    _room('music_heavy_en', 'en', 20, 112, 'Music-first group: artists and songs mostly filled.',
          hobby_pool=EN_ALL, ages=(18, 38), artists=0.9, songs=0.85, facts=0.3, skip=0.2, hide=0.1),
    _room('quiet_optional_he', 'he', 20, 113, 'Many optional answers skipped.',
          hobby_pool=HE_ALL, ages=(16, 24), artists=0.1, songs=0.05, facts=0.1, skip=0.5, hide=0.25),
    _room('no_ages_en', 'en', 18, 114, 'Nobody shared an age.',
          hobby_pool=EN_ALL, ages=None, artists=0.4, songs=0.3, facts=0.3, skip=0.15, hide=0.1),
    _room('teen_camp_he', 'he', 26, 115, 'Summer camp: large group of teenagers.',
          hobby_pool=HE_ALL, ages=(13, 17), artists=0.4, songs=0.3, facts=0.45, skip=0.15, hide=0.15),
    _room('university_en', 'en', 30, 116, 'Large university cohort.',
          hobby_pool=EN_ALL, ages=(19, 27), artists=0.45, songs=0.35, facts=0.3, skip=0.15, hide=0.1),
    _room('mixed_adults_he', 'he', 16, 117, 'Neighbourhood group of adults.',
          hobby_pool=HE_ALL, ages=(28, 60), artists=0.4, songs=0.3, facts=0.4, skip=0.2, hide=0.15),
    _room('outdoors_en', 'en', 14, 118, 'Hiking group: outdoor hobbies.',
          hobby_pool=(*EN_OUTDOOR, *EN_SPORT), ages=(21, 50), artists=0.35, songs=0.25, facts=0.35,
          skip=0.2, hide=0.1),
    _room('one_city_he', 'he', 15, 119, 'Everyone lives in the same city.',
          hobby_pool=HE_ALL, ages=(17, 30), artists=0.4, songs=0.3, facts=0.35, skip=0.15, hide=0.1,
          cities=('תל אביב',)),
    _room('small_office_en', 'en', 12, 120, 'Twelve colleagues, rich optional answers.',
          hobby_pool=EN_ALL, ages=(25, 52), artists=0.7, songs=0.6, facts=0.5, skip=0.1, hide=0.1),
)
