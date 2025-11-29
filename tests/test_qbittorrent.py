"""Tests for qbittorrent module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from mamfast.qbittorrent import (
    check_torrent_exists,
    get_client,
    get_torrent_info,
    upload_torrent,
)
from mamfast.qbittorrent import (
    test_connection as qb_test_connection,
)


class TestGetClient:
    """Tests for getting qBittorrent client."""

    def test_get_client_connects_successfully(self):
        """Test successful client connection."""
        mock_client = MagicMock()
        mock_settings = MagicMock()
        mock_settings.qbittorrent.host = "http://localhost:8080"
        mock_settings.qbittorrent.username = "admin"
        mock_settings.qbittorrent.password = "admin"

        with (
            patch("mamfast.qbittorrent.qbittorrentapi.Client", return_value=mock_client),
            patch("mamfast.qbittorrent.get_settings", return_value=mock_settings),
        ):
            client = get_client()

        mock_client.auth_log_in.assert_called_once()
        assert client is mock_client


class TestTestConnection:
    """Tests for test_connection function."""

    def test_connection_success(self):
        """Test successful connection check."""
        mock_client = MagicMock()
        mock_client.app.version = "4.5.0"

        with patch("mamfast.qbittorrent.get_client", return_value=mock_client):
            assert qb_test_connection() is True

    def test_connection_failure(self):
        """Test failed connection check."""
        with patch("mamfast.qbittorrent.get_client", side_effect=Exception("Connection failed")):
            assert qb_test_connection() is False


class TestCheckTorrentExists:
    """Tests for check_torrent_exists function."""

    def test_torrent_exists(self):
        """Test when torrent exists."""
        mock_client = MagicMock()
        mock_client.torrents_info.return_value = [MagicMock()]

        with patch("mamfast.qbittorrent.get_client", return_value=mock_client):
            result = check_torrent_exists("abc123")

        assert result is True
        mock_client.torrents_info.assert_called_once_with(hashes="abc123")

    def test_torrent_not_exists(self):
        """Test when torrent does not exist."""
        mock_client = MagicMock()
        mock_client.torrents_info.return_value = []

        with patch("mamfast.qbittorrent.get_client", return_value=mock_client):
            result = check_torrent_exists("abc123")

        assert result is False


class TestGetTorrentInfo:
    """Tests for get_torrent_info function."""

    def test_get_info_success(self):
        """Test getting torrent info."""
        mock_torrent = MagicMock()
        mock_torrent.info = {"name": "test", "size": 1000}
        mock_client = MagicMock()
        mock_client.torrents_info.return_value = [mock_torrent]

        with patch("mamfast.qbittorrent.get_client", return_value=mock_client):
            result = get_torrent_info("abc123")

        assert result == {"name": "test", "size": 1000}

    def test_get_info_not_found(self):
        """Test when torrent not found."""
        mock_client = MagicMock()
        mock_client.torrents_info.return_value = []

        with patch("mamfast.qbittorrent.get_client", return_value=mock_client):
            result = get_torrent_info("abc123")

        assert result is None


class TestUploadTorrent:
    """Tests for upload_torrent function."""

    def test_upload_torrent_file_not_found(self, tmp_path: Path):
        """Test upload with missing torrent file."""
        mock_settings = MagicMock()
        mock_settings.qbittorrent.category = "audiobooks"
        mock_settings.qbittorrent.tags = ["mam"]
        mock_settings.qbittorrent.auto_start = True

        with patch("mamfast.qbittorrent.get_settings", return_value=mock_settings):
            result = upload_torrent(
                torrent_path=tmp_path / "nonexistent.torrent",
                save_path=tmp_path,
            )
        assert result is False

    def test_upload_torrent_success(self, tmp_path: Path):
        """Test successful torrent upload."""
        torrent_file = tmp_path / "test.torrent"
        torrent_file.write_bytes(b"torrent data")

        mock_client = MagicMock()
        mock_client.torrents_add.return_value = "Ok."
        mock_settings = MagicMock()
        mock_settings.qbittorrent.category = "audiobooks"
        mock_settings.qbittorrent.tags = ["mam"]
        mock_settings.qbittorrent.auto_start = True

        with (
            patch("mamfast.qbittorrent.get_client", return_value=mock_client),
            patch("mamfast.qbittorrent.get_settings", return_value=mock_settings),
        ):
            result = upload_torrent(
                torrent_path=torrent_file,
                save_path=tmp_path,
            )

        assert result is True
        mock_client.torrents_add.assert_called_once()
