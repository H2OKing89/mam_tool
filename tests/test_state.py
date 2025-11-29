"""Tests for state management module."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from mamfast.models import AudiobookRelease
from mamfast.utils.state import (
    get_processed_identifiers,
    is_processed,
    load_state,
    mark_processed,
    save_state,
)


@pytest.fixture
def temp_state_file():
    """Create a temporary state file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"version": 1, "processed": {}, "failed": {}}, f)
        return Path(f.name)


@pytest.fixture
def mock_settings(temp_state_file):
    """Mock settings with temp state file."""
    settings = MagicMock()
    settings.paths.state_file = temp_state_file
    return settings


class TestLoadState:
    """Tests for load_state function."""

    def test_load_empty_state(self, mock_settings):
        """Test loading when no state file exists."""
        mock_settings.paths.state_file = Path("/nonexistent/state.json")
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
