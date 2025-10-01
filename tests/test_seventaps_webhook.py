"""Tests for the 7taps webhook endpoints and credential handling."""

import base64
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.api import seventaps
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_webhook_stats():
    """Ensure webhook statistics are reset between tests."""
    seventaps.webhook_stats.update(
        {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_request_time": None,
            "authentication_failures": 0,
        }
    )
    yield
    seventaps.webhook_stats.update(
        {
            "total_requests": 0,
            "successful_requests": 0,
            "failed_requests": 0,
            "last_request_time": None,
            "authentication_failures": 0,
        }
    )


def _auth_header(username: str, password: str) -> dict:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def _sample_payload() -> dict:
    return {
        "event_type": "xapi_statement",
        "timestamp": "2025-01-01T00:00:00Z",
        "data": {
            "actor": {"mbox": "mailto:webhook@example.com"},
            "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
            "object": {"id": "http://example.com/activity"},
        },
    }


@patch("app.api.seventaps.publish_statement_async", new_callable=AsyncMock)
def test_post_webhook_accepts_basic_auth(mock_publish: AsyncMock):
    mock_publish.return_value = {"message_id": "pubsub-1"}

    response = client.post(
        "/statements",
        json=_sample_payload(),
        headers=_auth_header("7taps.team", "PracticeofLife"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["processed_count"] == 1
    mock_publish.assert_called_once()


@patch("app.api.seventaps.publish_statement_async", new_callable=AsyncMock)
def test_put_webhook_uses_statement_id_override(mock_publish: AsyncMock):
    mock_publish.return_value = {"message_id": "pubsub-2"}

    response = client.put(
        "/statements",
        json={"actor": {"mbox": "mailto:put@example.com"}, "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"}, "object": {"id": "http://example.com/activity"}},
        params={"statementId": "fixed-id"},
        headers=_auth_header("7taps.team", "PracticeofLife"),
    )

    assert response.status_code == 200
    data = response.json()
    assert data["processed_count"] == 1
    mock_publish.assert_called_once()
    published_statement = mock_publish.call_args.args[0]
    assert published_statement.id == "fixed-id"


def test_webhook_rejects_invalid_credentials():
    response = client.post(
        "/statements",
        json=_sample_payload(),
        headers=_auth_header("bad", "credentials"),
    )
    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]
