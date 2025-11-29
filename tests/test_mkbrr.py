"""Tests for mkbrr module."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from mamfast.mkbrr import (
    MkbrrResult,
    check_docker_available,
    create_torrent,
    load_presets,
)


class TestMkbrrResult:
    """Tests for MkbrrResult dataclass."""

    def test_success_result(self):
        """Test successful result."""
        result = MkbrrResult(
            success=True,
            return_code=0,
            torrent_path=Path("/tmp/test.torrent"),
        )
        assert result.success is True
        assert result.return_code == 0
        assert result.torrent_path == Path("/tmp/test.torrent")
        assert result.error is None

    def test_failure_result(self):
        """Test failed result."""
        result = MkbrrResult(
            success=False,
            return_code=1,
            error="Docker command failed",
        )
        assert result.success is False
        assert result.return_code == 1
        assert result.error == "Docker command failed"
        assert result.torrent_path is None


class TestCheckDockerAvailable:
    """Tests for Docker availability check."""

    def test_docker_available(self):
        """Test when docker is available."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        mock_settings = MagicMock()
        mock_settings.docker_bin = "/usr/bin/docker"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("mamfast.mkbrr.get_settings", return_value=mock_settings),
        ):
            assert check_docker_available() is True

    def test_docker_not_available(self):
        """Test when docker is not available."""
        mock_settings = MagicMock()
        mock_settings.docker_bin = "/usr/bin/docker"

        with (
            patch("subprocess.run", side_effect=FileNotFoundError),
            patch("mamfast.mkbrr.get_settings", return_value=mock_settings),
        ):
            assert check_docker_available() is False


class TestLoadPresets:
    """Tests for load_presets function."""

    def test_load_presets_success(self, tmp_path: Path):
        """Test loading presets from yaml file."""
        presets_file = tmp_path / "presets.yaml"
        presets_file.write_text(
            """
presets:
  mam:
    announce: https://example.com/announce
  other:
    announce: https://other.com/announce
"""
        )

        mock_settings = MagicMock()
        mock_settings.mkbrr.host_config_dir = str(tmp_path)
        mock_settings.mkbrr.preset = "mam"

        with patch("mamfast.mkbrr.get_settings", return_value=mock_settings):
            presets = load_presets()

        assert "mam" in presets
        assert "other" in presets
        # Default preset should be first
        assert presets[0] == "mam"

    def test_load_presets_file_not_found(self, tmp_path: Path):
        """Test fallback when presets file doesn't exist."""
        mock_settings = MagicMock()
        mock_settings.mkbrr.host_config_dir = str(tmp_path)
        mock_settings.mkbrr.preset = "default"

        with patch("mamfast.mkbrr.get_settings", return_value=mock_settings):
            presets = load_presets()

        assert presets == ["default"]


class TestCreateTorrent:
    """Tests for torrent creation."""

    def test_create_torrent_success(self, tmp_path: Path):
        """Test successful torrent creation."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()
        (content_dir / "audio.m4b").write_bytes(b"audio data")

        output_dir = tmp_path / "torrents"
        output_dir.mkdir()

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Torrent created"
        mock_result.stderr = ""

        mock_settings = MagicMock()
        mock_settings.docker_bin = "/usr/bin/docker"
        mock_settings.mkbrr.preset = "mam"
        mock_settings.mkbrr.host_output_dir = str(output_dir)
        mock_settings.mkbrr.host_data_root = "/data"
        mock_settings.mkbrr.container_data_root = "/data"
        mock_settings.mkbrr.host_config_dir = str(tmp_path)
        mock_settings.mkbrr.container_config_dir = "/config"
        mock_settings.mkbrr.container_output_dir = "/torrents"
        mock_settings.mkbrr.image = "ghcr.io/autobrr/mkbrr:latest"
        mock_settings.target_uid = 99
        mock_settings.target_gid = 100

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("mamfast.mkbrr.get_settings", return_value=mock_settings),
            patch("mamfast.mkbrr.host_to_container_data_path", return_value="/data/content"),
            patch("mamfast.mkbrr.host_to_container_torrent_path", return_value="/torrents"),
        ):
            result = create_torrent(content_dir, output_dir)

        assert result.success is True
        assert result.return_code == 0

    def test_create_torrent_failure(self, tmp_path: Path):
        """Test failed torrent creation."""
        content_dir = tmp_path / "content"
        content_dir.mkdir()

        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error creating torrent"

        mock_settings = MagicMock()
        mock_settings.docker_bin = "/usr/bin/docker"
        mock_settings.mkbrr.preset = "mam"
        mock_settings.mkbrr.host_output_dir = str(tmp_path)
        mock_settings.mkbrr.host_data_root = "/data"
        mock_settings.mkbrr.container_data_root = "/data"
        mock_settings.mkbrr.host_config_dir = str(tmp_path)
        mock_settings.mkbrr.container_config_dir = "/config"
        mock_settings.mkbrr.container_output_dir = "/torrents"
        mock_settings.mkbrr.image = "ghcr.io/autobrr/mkbrr:latest"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("mamfast.mkbrr.get_settings", return_value=mock_settings),
            patch("mamfast.mkbrr.host_to_container_data_path", return_value="/data/content"),
            patch("mamfast.mkbrr.host_to_container_torrent_path", return_value="/torrents"),
        ):
            result = create_torrent(content_dir)

        assert result.success is False
        assert result.return_code == 1
        assert "exited with code" in (result.error or "")
