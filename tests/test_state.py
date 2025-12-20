"""Tests for state management module."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mamfast.models import AudiobookRelease
from mamfast.utils.state import (
    clear_failed,
    get_failed_identifiers,
    get_processed_identifiers,
    get_stats,
    is_failed,
    is_processed,
    load_state,
    mark_failed,
    mark_processed,
    save_state,
)


@pytest.fixture
def temp_state_file(tmp_path: Path):
    """Create a temporary state file using pytest's tmp_path fixture."""
    state_file = tmp_path / "state.json"
    state_file.write_text(json.dumps({"version": 1, "processed": {}, "failed": {}}))
    return state_file


@pytest.fixture
def mock_settings(temp_state_file):
    """Mock settings with temp state file."""
    settings = MagicMock()
    settings.paths.state_file = temp_state_file
    return settings


class TestLoadState:
    """Tests for load_state function."""

    def test_load_empty_state(self, mock_settings, tmp_path):
        """Test loading when no state file exists."""
        # Use a valid temp directory but non-existent file
        mock_settings.paths.state_file = tmp_path / "nonexistent_state.json"
        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            state = load_state()

        assert state["version"] == 1
        assert state["processed"] == {}
        assert state["failed"] == {}

    def test_load_existing_state(self, mock_settings, temp_state_file):
        """Test loading existing state file."""
        # Write some state
        state_data = {
            "version": 1,
            "processed": {"B09TEST123": {"title": "Test Book"}},
            "failed": {},
        }
        with open(temp_state_file, "w") as f:
            json.dump(state_data, f)

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            state = load_state()

        assert "B09TEST123" in state["processed"]


class TestSaveState:
    """Tests for save_state function."""

    def test_save_state(self, mock_settings, temp_state_file):
        """Test saving state to file."""
        state = {
            "version": 1,
            "processed": {"B09NEW123": {"title": "New Book"}},
            "failed": {},
        }

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            save_state(state)

        with open(temp_state_file) as f:
            saved = json.load(f)

        assert "B09NEW123" in saved["processed"]


class TestIsProcessed:
    """Tests for is_processed function."""

    def test_not_processed(self, mock_settings, temp_state_file):
        """Test checking unprocessed release."""
        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            assert is_processed("B09UNKNOWN") is False

    def test_is_processed(self, mock_settings, temp_state_file):
        """Test checking processed release."""
        state_data = {
            "version": 1,
            "processed": {"B09DONE123": {"title": "Done Book"}},
            "failed": {},
        }
        with open(temp_state_file, "w") as f:
            json.dump(state_data, f)

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            assert is_processed("B09DONE123") is True


class TestMarkProcessed:
    """Tests for mark_processed function."""

    def test_mark_processed_with_asin(self, mock_settings, temp_state_file):
        """Test marking release as processed using ASIN."""
        release = AudiobookRelease(
            asin="B09MARK123",
            title="Marked Book",
            author="Test Author",
        )

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            mark_processed(release)
            assert is_processed("B09MARK123") is True

    def test_mark_processed_without_asin(self, mock_settings, temp_state_file):
        """Test marking release without ASIN uses path."""
        release = AudiobookRelease(
            title="No ASIN Book",
            source_dir=Path("/tmp/audiobooks/test"),
        )

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            mark_processed(release)
            assert is_processed("/tmp/audiobooks/test") is True


class TestGetProcessedIdentifiers:
    """Tests for get_processed_identifiers function."""

    def test_get_processed_identifiers(self, mock_settings, temp_state_file):
        """Test getting set of processed identifiers."""
        state_data = {
            "version": 1,
            "processed": {
                "B09ONE123": {},
                "B09TWO456": {},
            },
            "failed": {},
        }
        with open(temp_state_file, "w") as f:
            json.dump(state_data, f)

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            identifiers = get_processed_identifiers()

        assert "B09ONE123" in identifiers
        assert "B09TWO456" in identifiers
        assert len(identifiers) == 2


class TestIsFailed:
    """Tests for is_failed function."""

    def test_not_failed(self, mock_settings, temp_state_file):
        """Test checking non-failed release."""
        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            assert is_failed("B09UNKNOWN") is False

    def test_is_failed(self, mock_settings, temp_state_file):
        """Test checking failed release."""
        state_data = {
            "version": 1,
            "processed": {},
            "failed": {"B09FAIL123": {"error": "Some error"}},
        }
        with open(temp_state_file, "w") as f:
            json.dump(state_data, f)

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            assert is_failed("B09FAIL123") is True


class TestMarkFailed:
    """Tests for mark_failed function."""

    def test_mark_failed_with_asin(self, mock_settings, temp_state_file):
        """Test marking release as failed using ASIN."""
        release = AudiobookRelease(
            asin="B09FAIL123",
            title="Failed Book",
            author="Test Author",
        )

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            mark_failed(release, "Test error message")
            assert is_failed("B09FAIL123") is True

    def test_mark_failed_without_asin(self, mock_settings, temp_state_file):
        """Test marking release without ASIN uses path."""
        release = AudiobookRelease(
            title="No ASIN Book",
            source_dir=Path("/tmp/audiobooks/failed"),
        )

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            mark_failed(release, "Error occurred")
            assert is_failed("/tmp/audiobooks/failed") is True

    def test_mark_failed_no_identifier(self, mock_settings, temp_state_file):
        """Test marking fails without identifier."""
        release = AudiobookRelease(title="No ID Book")

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            # Should not raise, just log warning
            mark_failed(release, "Error")


class TestMarkProcessedRemovesFailed:
    """Test that mark_processed removes from failed."""

    def test_removes_from_failed(self, mock_settings, temp_state_file):
        """Test marking processed removes from failed state."""
        # First mark as failed
        state_data = {
            "version": 1,
            "processed": {},
            "failed": {"B09RETRY123": {"error": "Previous error"}},
        }
        with open(temp_state_file, "w") as f:
            json.dump(state_data, f)

        release = AudiobookRelease(asin="B09RETRY123", title="Retry Book")

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            mark_processed(release)
            assert is_processed("B09RETRY123") is True
            assert is_failed("B09RETRY123") is False

    def test_mark_processed_no_identifier(self, mock_settings, temp_state_file):
        """Test marking processed fails without identifier."""
        release = AudiobookRelease(title="No ID Book")

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            # Should not raise, just log warning
            mark_processed(release)


class TestClearFailed:
    """Tests for clear_failed function."""

    def test_clear_failed_success(self, mock_settings, temp_state_file):
        """Test clearing failed state."""
        state_data = {
            "version": 1,
            "processed": {},
            "failed": {"B09CLEAR123": {"error": "Some error"}},
        }
        with open(temp_state_file, "w") as f:
            json.dump(state_data, f)

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            result = clear_failed("B09CLEAR123")
            assert result is True
            assert is_failed("B09CLEAR123") is False

    def test_clear_failed_not_found(self, mock_settings, temp_state_file):
        """Test clearing non-existent failed entry."""
        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            result = clear_failed("B09NOTFOUND")
            assert result is False


class TestGetFailedIdentifiers:
    """Tests for get_failed_identifiers function."""

    def test_get_failed_identifiers(self, mock_settings, temp_state_file):
        """Test getting set of failed identifiers."""
        state_data = {
            "version": 1,
            "processed": {},
            "failed": {
                "B09FAIL1": {"error": "Error 1"},
                "B09FAIL2": {"error": "Error 2"},
            },
        }
        with open(temp_state_file, "w") as f:
            json.dump(state_data, f)

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            identifiers = get_failed_identifiers()

        assert "B09FAIL1" in identifiers
        assert "B09FAIL2" in identifiers
        assert len(identifiers) == 2


class TestGetStats:
    """Tests for get_stats function."""

    def test_get_stats(self, mock_settings, temp_state_file):
        """Test getting state statistics."""
        state_data = {
            "version": 1,
            "processed": {"B001": {}, "B002": {}, "B003": {}},
            "failed": {"B004": {}, "B005": {}},
        }
        with open(temp_state_file, "w") as f:
            json.dump(state_data, f)

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            stats = get_stats()

        assert stats["processed"] == 3
        assert stats["failed"] == 2


class TestLoadStateCorruptedFile:
    """Tests for handling corrupted state file."""

    def test_handles_corrupted_json(self, mock_settings, temp_state_file):
        """Test handling corrupted JSON file."""
        # Write invalid JSON
        with open(temp_state_file, "w") as f:
            f.write("not valid json {{{")

        with patch("mamfast.utils.state.get_settings", return_value=mock_settings):
            state = load_state()

        # Should return fresh state
        assert state["version"] == 1
        assert state["processed"] == {}
        assert state["failed"] == {}

        # Backup file should exist
        backup = temp_state_file.with_suffix(".json.bak")
        assert backup.exists()
