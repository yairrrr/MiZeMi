"""Profile type-ahead over the offline reference names."""

import pytest

from app.domain.questions.suggestions import MAX_SUGGESTIONS
from app.infrastructure.knowledge import get_knowledge, get_suggestion_index


@pytest.fixture(scope='module')
def index():
    return get_suggestion_index()


def test_hebrew_prefix_lists_matching_localities_across_spellings(index) -> None:
    suggestions = index.suggest('localities', 'קריית')

    assert 0 < len(suggestions) <= MAX_SUGGESTIONS
    assert all(s.startswith(('קריית', 'קרית')) for s in suggestions)
    assert 'קריית שמונה' in index.suggest('localities', 'קריית שמ')
    assert 'קרית אונו' in index.suggest('localities', 'קרית או')


def test_never_more_than_five(index) -> None:
    for kind in ('localities', 'foods', 'hobbies', 'movies', 'artists', 'songs'):
        assert len(index.suggest(kind, 'a')) == MAX_SUGGESTIONS
        assert len(index.suggest(kind, 'ש')) <= MAX_SUGGESTIONS


def test_suggestions_follow_the_typed_script(index) -> None:
    assert index.suggest('foods', 'פיצ')[0] == 'פיצה'
    assert all(s.isascii() for s in index.suggest('hobbies', 'foot'))


def test_every_suggestion_resolves_back_to_a_known_entity(index) -> None:
    knowledge = get_knowledge()
    for kind, query in (('movies', 'טיטא'), ('movies', 'harry'), ('songs', 'shot in'),
                        ('artists', 'עומר'), ('localities', 'תל'), ('hobbies', 'ריצ')):
        for name in index.suggest(kind, query):
            assert knowledge.resolve(kind, name).high_confidence, (kind, name)


def test_empty_overlong_or_unknown_queries_return_nothing(index) -> None:
    assert index.suggest('foods', '') == []
    assert index.suggest('foods', '   ') == []
    assert index.suggest('foods', 'x' * 61) == []
    assert index.suggest('foods', 'zzzzqqqq') == []
