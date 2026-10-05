"""GET /api/v1/suggestions — profile type-ahead endpoint."""

from fastapi.testclient import TestClient

from app.main import create_app


def test_returns_at_most_five_reference_names() -> None:
    client = TestClient(create_app())

    response = client.get('/api/v1/suggestions', params={'field': 'city', 'q': 'קריית'})

    assert response.status_code == 200
    suggestions = response.json()['suggestions']
    assert 0 < len(suggestions) <= 5
    assert response.headers['cache-control'] == 'no-store'


def test_personal_fact_and_unknown_fields_are_rejected() -> None:
    client = TestClient(create_app())

    for field in ('personal_fact', 'age', 'favorite_music', 'nope'):
        response = client.get('/api/v1/suggestions', params={'field': field, 'q': 'a'})
        assert response.status_code == 422
        assert response.json()['error']['code'] == 'VALIDATION_ERROR'


def test_overlong_query_is_rejected_and_empty_query_is_empty() -> None:
    client = TestClient(create_app())

    assert client.get('/api/v1/suggestions', params={'field': 'hobby', 'q': 'x' * 61}).status_code == 422
    assert client.get('/api/v1/suggestions', params={'field': 'hobby'}).json() == {'suggestions': []}
