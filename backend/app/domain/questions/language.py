"""Allowlisted bilingual labels. Player values are data, never templates."""

import unicodedata

FIELD_LABELS = {
    'city': ('city', 'עיר'),
    'favorite_food': ('favorite food', 'אוכל אהוב'),
    'hobby': ('hobby', 'תחביב'),
    'favorite_music': ('music style', 'סגנון מוזיקה'),
    'favorite_movie': ('favorite movie', 'סרט אהוב'),
    'age': ('age', 'גיל'),
    'personal_fact': ('personal fact', 'פרט אישי'),
}
PREFERENCE_FIELDS = ('city', 'favorite_food', 'hobby', 'favorite_music', 'favorite_movie')


def normalize(value: str | int) -> str | int:
    if isinstance(value, str):
        return unicodedata.normalize('NFC', ' '.join(value.split())).casefold()
    return value


def label(key: str, language: str) -> str:
    # Unknown keys remain supported by the original generic rules for pure
    # domain callers. The application profile schema rejects unknown fields.
    return FIELD_LABELS.get(key, (key.replace('_', ' '), key.replace('_', ' ')))[language == 'he']


def say(language: str, english: str, hebrew: str, **values: object) -> str:
    # Only source-code literal templates are passed here. format interpolates
    # data once; braces inside player text are not evaluated recursively.
    return (hebrew if language == 'he' else english).format(**values)


def direct_hebrew(kind: str, field: str) -> str:
    """Human concepts in question copy; never expose storage terminology."""
    templates = {
        'unique': {
            'city': 'מי היחיד/ה שגר/ה ב{value}?',
            'favorite_food': 'מי היחיד/ה שבחר/ה {value} כאוכל אהוב?',
            'hobby': 'מי היחיד/ה שהתחביב שלו/ה הוא {value}?',
            'favorite_music': 'מי היחיד/ה שבחר/ה במוזיקה בסגנון {value}?',
            'favorite_movie': 'מי היחיד/ה שהסרט האהוב עליו/ה הוא {value}?',
            'age': 'מי היחיד/ה בגיל {value}?',
            'personal_fact': 'מי שיתף/ה את הפרט {value}?',
        },
        'mode': {
            'city': 'איזו עיר מופיעה הכי הרבה בקבוצה?',
            'favorite_food': 'איזה אוכל אהוב נבחר הכי הרבה בקבוצה?',
            'hobby': 'איזה תחביב חוזר הכי הרבה בקבוצה?',
            'favorite_music': 'איזה סגנון מוזיקה נבחר הכי הרבה בקבוצה?',
            'favorite_movie': 'איזה סרט אהוב נבחר הכי הרבה בקבוצה?',
            'age': 'מה הגיל הנפוץ ביותר בקבוצה?',
            'personal_fact': 'איזה פרט אישי משותף להכי הרבה משתתפים?',
        },
        'count': {
            'city': 'כמה משתתפים גרים ב{value}?',
            'favorite_food': 'כמה משתתפים בחרו {value} כאוכל האהוב עליהם?',
            'hobby': 'לכמה משתתפים יש תחביב משותף: {value}?',
            'favorite_music': 'כמה משתתפים בחרו במוזיקה בסגנון {value}?',
            'favorite_movie': 'כמה משתתפים בחרו {value} כסרט האהוב עליהם?',
            'age': 'כמה משתתפים הם בגיל {value}?',
            'personal_fact': 'כמה משתתפים שיתפו את הפרט {value}?',
        },
    }
    fallback = {'unique':'מי היחיד/ה שאצלו/ה {field} הוא {value}?',
                'mode':'מה הכי נפוץ בקבוצה לפי {field}?',
                'count':'אצל כמה משתתפים {field} הוא {value}?'}
    return templates[kind].get(field, fallback[kind])
