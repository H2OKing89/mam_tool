"""Tests for metadata module."""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from mamfast.metadata import (
    fetch_audnex_book,
    run_mediainfo,
)


class TestFetchAudnexBook:
    """Tests for Audnex API integration."""

    def test_fetch_success(self):
        """Test successful metadata fetch."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "asin": "B09TEST123",
            "title": "Test Book",
            "authors": [{"name": "Test Author"}],
        }

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_settings = MagicMock()
        mock_settings.audnex.base_url = "https://api.audnex.us"
        mock_settings.audnex.timeout_seconds = 30

        with (
            patch("httpx.Client", return_value=mock_client),
            patch("mamfast.metadata.get_settings", return_value=mock_settings),
        ):
            result = fetch_audnex_book("B09TEST123")

        assert result is not None
        assert result["asin"] == "B09TEST123"
        assert result["title"] == "Test Book"

    def test_fetch_not_found(self):
        """Test handling 404 response."""
        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)

        mock_settings = MagicMock()
        mock_settings.audnex.base_url = "https://api.audnex.us"
        mock_settings.audnex.timeout_seconds = 30

        with (
            patch("httpx.Client", return_value=mock_client),
            patch("mamfast.metadata.get_settings", return_value=mock_settings),
        ):
            result = fetch_audnex_book("INVALID_ASIN")

        assert result is None


class TestRunMediainfo:
    """Tests for mediainfo integration."""

    def test_run_mediainfo_file_not_found(self):
        """Test handling missing file."""
        mock_settings = MagicMock()
        mock_settings.mediainfo.binary = "mediainfo"

        with patch("mamfast.metadata.get_settings", return_value=mock_settings):
            result = run_mediainfo(Path("/nonexistent/file.m4b"))

        assert result is None

    def test_run_mediainfo_success(self):
        """Test successful mediainfo extraction."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = '{"media": {"track": [{"@type": "Audio"}]}}'

        mock_settings = MagicMock()
        mock_settings.mediainfo.binary = "mediainfo"

        # Create a temp file
        with tempfile.NamedTemporaryFile(suffix=".m4b", delete=False) as f:
            f.write(b"fake audio data")
            temp_path = Path(f.name)

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("mamfast.metadata.get_settings", return_value=mock_settings),
        ):
            result = run_mediainfo(temp_path)

        assert result is not None
        assert "media" in result
