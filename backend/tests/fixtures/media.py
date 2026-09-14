"""Fictional Israeli rooms with concrete media choices, never pre-entered genres."""
from tests.fixtures.rooms import P, Room


MEDIA_RICH = Room('media_rich', 'he', (
    P('תל אביב', 'פיצה', 'ריצה', 'Pop', 'המסור', artist='עומר אדם', song='Blank Space'),
    P('חיפה', 'סושי', 'ציור', 'Rock', 'לזמן את הרוע', artist='אייל גולן', song='Shake It Off - Taylor Swift'),
    P('ירושלים', 'חומוס', 'כדורגל', 'Mizrahi', 'המסור', artist='שרית חדד', song='Paradise - Coldplay'),
    P('באר שבע', 'המבורגר', 'גיימינג', 'Pop', 'לזמן את הרוע', artist='משה פרץ', song='Yellow - Coldplay'),
    P('נתניה', 'פסטה', 'שחייה', 'Electronic', 'המסור', artist='זהבה בן', song='Enter Sandman'),
    P('רמת גן', 'פלאפל', 'צילום', 'Rock', 'טרון: ארס', artist='עדן בן זקן', song='Enter Sandman'),
    P('עכו', 'ראמן', 'קריאה', 'Pop', 'בחזרה לעתיד', artist='Metallica', song='Shake It Off - Taylor Swift'),
    P('אילת', 'לזניה', 'גיטרה', 'Mizrahi', 'היומן', artist='Metallica', song='Blank Space'),
    P('רחובות', 'טאקו', 'פילאטיס', 'Jazz', 'שרק', artist='Coldplay', song='Enter Sandman'),
    P('חולון', 'שווארמה', 'בישול', 'Pop', 'שכחו אותי בבית', artist='Eminem', song='Enter Sandman'),
), 'Ten people: horror leads movie picks, Mizrahi leads artists, pop leads songs; other fields compete for slots.')

MEDIA_SMALL = Room('media_small', 'he', MEDIA_RICH.rows[:4], 'Four people with complete optional media choices.')
MEDIA_OPTIONAL = Room('media_optional', 'he', tuple(
    {'values': {k: v for k, v in row['values'].items()
                if index < 4 or k not in ('favorite_artist', 'favorite_song')}, 'hide': ()}
    for index, row in enumerate(MEDIA_RICH.rows)
), 'Only four of ten people share artists/songs; questions describe those choices explicitly.')

MEDIA_ROOMS = (MEDIA_RICH, MEDIA_SMALL, MEDIA_OPTIONAL)
