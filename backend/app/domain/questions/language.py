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
