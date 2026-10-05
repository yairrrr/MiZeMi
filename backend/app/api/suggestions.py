"""Profile type-ahead: at most five reference names for a partially typed answer.

GET keeps the endpoint outside the POST rate bucket a whole classroom shares
while typing; the app runs without access logs, so the typed prefix is not
recorded. Free-text fields (the personal fact) have no reference names and
are deliberately not accepted here.
"""

from typing import Annotated, Literal

from fastapi import APIRouter, Query, Request
from pydantic import BaseModel

from app.domain.questions.suggestions import MAX_QUERY_LENGTH, SuggestionIndex

router = APIRouter()

FIELD_KINDS = {
    'city': 'localities',
    'favorite_food': 'foods',
    'hobby': 'hobbies',
    'favorite_movie': 'movies',
    'favorite_artist': 'artists',
    'favorite_song': 'songs',
}

SuggestableField = Literal['city', 'favorite_food', 'hobby', 'favorite_movie', 'favorite_artist', 'favorite_song']


class SuggestionsResponse(BaseModel):
    suggestions: list[str]


@router.get('/suggestions', response_model=SuggestionsResponse)
async def get_suggestions(
    request: Request,
    field: SuggestableField,
    q: Annotated[str, Query(max_length=MAX_QUERY_LENGTH)] = '',
) -> SuggestionsResponse:
    index: SuggestionIndex = request.app.state.suggestions
    return SuggestionsResponse(suggestions=index.suggest(FIELD_KINDS[field], q))
