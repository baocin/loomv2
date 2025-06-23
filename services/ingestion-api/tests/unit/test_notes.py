"""Unit tests for notes ingestion endpoints."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.models import NoteData


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def mock_kafka_producer():
    """Mock Kafka producer."""
    with patch("app.routers.notes.kafka_producer") as mock:
        mock.send_message = AsyncMock()
        yield mock


@pytest.fixture
def sample_note_data():
    """Sample note data for testing."""
    from ..test_helpers import create_note_test_data

    return create_note_test_data()


class TestNotesUpload:
    """Test notes upload endpoint."""

    def test_upload_note_success(self, client, mock_kafka_producer, sample_note_data):
        """Test successful note upload."""
        response = client.post("/notes/upload", json=sample_note_data)

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["topic"] == "device.text.notes.raw"
        assert "message_id" in data

        # Verify Kafka producer was called
        mock_kafka_producer.send_message.assert_called_once()

    def test_upload_note_empty_content(
        self,
        client,
        mock_kafka_producer,
        sample_note_data,
    ):
        """Test note upload with empty content fails."""
        sample_note_data["content"] = ""

        response = client.post("/notes/upload", json=sample_note_data)
        assert response.status_code == 422

    def test_upload_note_missing_content(
        self,
        client,
        mock_kafka_producer,
        sample_note_data,
    ):
        """Test note upload without content fails."""
        del sample_note_data["content"]

        response = client.post("/notes/upload", json=sample_note_data)
        assert response.status_code == 422

    def test_upload_note_word_count_calculated(
        self,
        client,
        mock_kafka_producer,
        sample_note_data,
    ):
        """Test that word count is automatically calculated."""
        sample_note_data["content"] = "This is a test note with exactly nine words."

        response = client.post("/notes/upload", json=sample_note_data)
        assert response.status_code == 200

        # Verify the note was processed with correct word count
        call_args = mock_kafka_producer.send_message.call_args
        note_message = call_args[1]["message"]
        assert note_message.word_count == 9

    def test_upload_note_kafka_failure(
        self,
        client,
        mock_kafka_producer,
        sample_note_data,
    ):
        """Test note upload when Kafka fails."""
        mock_kafka_producer.send_message.side_effect = Exception(
            "Kafka connection error",
        )

        response = client.post("/notes/upload", json=sample_note_data)
        assert response.status_code == 500
        assert "Failed to upload note" in response.json()["detail"]

    def test_upload_note_minimal_data(self, client, mock_kafka_producer):
        """Test note upload with minimal required data."""
        minimal_note = {"device_id": "12345678-1234-8234-1234-123456789012", "recorded_at": datetime.now(UTC).isoformat(), "content": "Minimal note content"}

        response = client.post("/notes/upload", json=minimal_note)
        assert response.status_code == 200


class TestNotesBatch:
    """Test notes batch upload endpoint."""

    def test_batch_upload_success(self, client, mock_kafka_producer, sample_note_data):
        """Test successful batch note upload."""
        notes = [sample_note_data.copy() for _ in range(3)]
        for i, note in enumerate(notes):
            note["title"] = f"Test Note {i + 1}"

        response = client.post("/notes/batch", json=notes)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "success"
        assert data["topic"] == "device.text.notes.raw"

        # Verify Kafka producer was called for each note
        assert mock_kafka_producer.send_message.call_count == 3

    def test_batch_upload_too_large(
        self,
        client,
        mock_kafka_producer,
        sample_note_data,
    ):
        """Test batch upload with too many notes fails."""
        notes = [sample_note_data.copy() for _ in range(101)]  # Over limit

        response = client.post("/notes/batch", json=notes)
        assert response.status_code == 400
        assert "Batch size too large" in response.json()["detail"]

    def test_batch_upload_partial_failure(
        self,
        client,
        mock_kafka_producer,
        sample_note_data,
    ):
        """Test batch upload with partial failures."""
        notes = [sample_note_data.copy() for _ in range(3)]

        # Mock Kafka to fail on second call
        mock_kafka_producer.send_message.side_effect = [
            None,  # Success
            Exception("Kafka error"),  # Failure
            None,  # Success
        ]

        response = client.post("/notes/batch", json=notes)
        assert response.status_code == 200

        data = response.json()
        assert data["status"] == "partial"


class TestNoteDataModel:
    """Test NoteData model validation."""

    def test_note_data_validation(self, sample_note_data):
        """Test valid note data model creation."""
        note = NoteData(**sample_note_data)
        assert note.content == "This is a test note with some content."
        assert note.title == "Test Note"
        assert note.word_count == 8  # Calculated automatically
        assert note.note_type == "text"
        assert len(note.tags) == 2

    def test_note_data_content_stripped(self):
        """Test that note content is stripped of whitespace."""
        note_data = {
            "device_id": "12345678-1234-8234-1234-123456789012",
            "recorded_at": datetime.now(UTC),
            "content": "  This is a test note.  ",
        }

        note = NoteData(**note_data)
        assert note.content == "This is a test note."

    def test_note_data_empty_content_validation(self):
        """Test that empty content raises validation error."""
        note_data = {
            "device_id": "12345678-1234-8234-1234-123456789012",
            "recorded_at": datetime.now(UTC),
            "content": "",
        }

        with pytest.raises(ValueError, match="Note content cannot be empty"):
            NoteData(**note_data)

    def test_note_data_whitespace_only_content_validation(self):
        """Test that whitespace-only content raises validation error."""
        note_data = {
            "device_id": "12345678-1234-8234-1234-123456789012",
            "recorded_at": datetime.now(UTC),
            "content": "   ",
        }

        with pytest.raises(ValueError, match="Note content cannot be empty"):
            NoteData(**note_data)

    def test_note_data_defaults(self):
        """Test default values for optional fields."""
        from ..test_helpers import create_base_test_data

        note_data = create_base_test_data()
        note_data.update(
            {
                "content": "Test content",
            },
        )

        note = NoteData(**note_data)
        assert note.note_type == "text"
        assert note.tags == []
        assert note.title is None
        assert note.language is None
        assert note.word_count == 2
