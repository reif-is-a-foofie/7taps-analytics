"""Tests for the FastAPI xAPI ingestion endpoints using Pub/Sub publishing."""

from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.api.xapi import reset_ingestion_stats
from app.main import app

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_ingestion_state():
    """Ensure ingestion stats are reset between tests."""
    reset_ingestion_stats()
    yield
    reset_ingestion_stats()


def _sample_statement(actor: str = "mailto:test@example.com") -> dict:
    return {
        "actor": {"mbox": actor},
        "verb": {"id": "http://adlnet.gov/expapi/verbs/completed"},
        "object": {"id": "http://example.com/activity"},
    }


@patch("app.api.xapi._publish_payload")
def test_ingest_statement_publishes_to_pubsub(mock_publish: Mock):
    mock_publish.return_value = {
        "message_id": "mock-message-1",
        "topic": "projects/test/topics/xapi-ingestion-topic",
    }

    response = client.post("/api/xapi/ingest", json=_sample_statement())
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert data["statement_id"]
    assert "mock-message-1" in data["message"]
    mock_publish.assert_called_once()

    status_response = client.get(f"/api/xapi/statements/{data['statement_id']}")
    assert status_response.status_code == 200
    status_data = status_response.json()
    assert status_data["found"] is True
    assert status_data["message_id"] == "mock-message-1"

    recent_response = client.get("/api/xapi/recent", params={"limit": 5})
    assert recent_response.status_code == 200
    recent_data = recent_response.json()
    assert recent_data["statements"]
    assert recent_data["statements"][0]["message_id"] == "mock-message-1"


@patch("app.api.xapi._publish_payload")
def test_batch_ingest_reports_failed_messages(mock_publish: Mock):
    mock_publish.side_effect = [
        {"message_id": "batch-success", "topic": "projects/test/topics/xapi"},
        Exception("publish failed"),
    ]

    batch_payload = [_sample_statement(), _sample_statement("mailto:second@example.com")]
    response = client.post("/api/xapi/ingest/batch", json=batch_payload)
    assert response.status_code == 200

    data = response.json()
    assert data["summary"]["total"] == 2
    assert data["summary"]["successful"] == 1
    assert data["summary"]["failed"] == 1
    assert mock_publish.call_count == 2

    error_entries = [entry for entry in data["batch_results"] if entry.get("success") is False]
    assert error_entries, "Expected at least one failed entry"
    assert "publish failed" in error_entries[0]["error"]


@patch("app.api.xapi.get_gcp_config")
def test_ingestion_status_reports_pubsub_health(mock_get_config: Mock):
    mock_config = Mock()
    mock_config.project_id = "test-project"
    mock_config.pubsub_topic = "xapi-ingestion-topic"
    mock_config.get_topic_path.return_value = "projects/test/topics/xapi-ingestion-topic"
    mock_publisher = Mock()
    mock_publisher.get_topic.return_value = None
    mock_config.pubsub_publisher = mock_publisher
    mock_get_config.return_value = mock_config

    response = client.get("/ui/test-xapi-ingestion")
    assert response.status_code == 200

    data = response.json()
    assert data["publisher_ready"] is True
    assert data["pubsub_topic"] == "xapi-ingestion-topic"
    assert data["project_id"] == "test-project"
    mock_publisher.get_topic.assert_called_once()


@patch("app.api.xapi._publish_payload")
def test_ui_recent_feed_renders(mock_publish: Mock):
    mock_publish.return_value = {
        "message_id": "feed-msg-1",
        "topic": "projects/test/topics/xapi-ingestion-topic",
    }

    client.post("/api/xapi/ingest", json=_sample_statement("mailto:feed@example.com"))

    response = client.get("/ui/recent-pubsub")
    assert response.status_code == 200
    assert "Data Explorer" in response.text or "Recent" in response.text
