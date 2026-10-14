"""Integration: /api/v1/features and the AI-mode request rejection path."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.integration.test_game_flow_hardening import _app


def test_features_endpoint_reports_ai_unavailable_by_default():
    with TestClient(_app()) as client:
        body = client.get("/api/v1/features").json()
        assert body == {"ai_mode_available": False}


def test_ai_mode_rejected_when_server_has_no_key():
    with TestClient(_app()) as client:
        response = client.post(
            "/api/v1/rooms",
            json={"question_count": 5, "language": "he", "question_source": "ai"},
        )
        assert response.status_code == 400
        payload = response.json()
        assert payload["error"]["code"] == "VALIDATION_ERROR"
        # The message must not reveal the environment variable name or hint
        # at how to turn AI on — it just says the feature is unavailable.
        assert "sk-ant" not in payload["error"]["message"]
        assert "MIZEMI_" not in payload["error"]["message"]


def test_algorithmic_mode_still_works_by_default():
    with TestClient(_app()) as client:
        response = client.post(
            "/api/v1/rooms",
            json={"question_count": 5, "language": "he", "question_source": "algorithmic"},
        )
        assert response.status_code == 201
        assert response.json()["config"]["question_source"] == "algorithmic"
