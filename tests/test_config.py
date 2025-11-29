"""Tests for config module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from mamfast.config import (
    FiltersConfig,
    MamConfig,
    MkbrrConfig,
    PathsConfig,
    QBittorrentConfig,
    load_yaml_config,
)


class TestPathsConfig:
    """Tests for PathsConfig dataclass."""

    def test_paths_config_creation(self):
        """Test creating PathsConfig with required fields."""
        config = PathsConfig(
            library_root=Path("/tmp/library"),
            torrent_output=Path("/tmp/torrents"),
            seed_root=Path("/tmp/seed"),
            state_file=Path("/tmp/state.json"),
            log_file=Path("/tmp/app.log"),
        )
        assert config.library_root == Path("/tmp/library")
        assert config.torrent_output == Path("/tmp/torrents")
        assert config.seed_root == Path("/tmp/seed")


class TestMamConfig:
    """Tests for MamConfig dataclass."""

    def test_default_values(self):
        """Test default values are set correctly."""
        config = MamConfig()
        assert config.max_filename_length == 225
        assert ".m4b" in config.allowed_extensions
        assert ".jpg" in config.allowed_extensions

    def test_custom_values(self):
        """Test custom values override defaults."""
        config = MamConfig(max_filename_length=200)
        assert config.max_filename_length == 200


class TestFiltersConfig:
    """Tests for FiltersConfig dataclass."""

    def test_default_values(self):
        """Test default values."""
        config = FiltersConfig()
        assert config.remove_phrases == []
        assert config.remove_book_numbers is True
        assert config.author_map == {}
        assert config.transliterate_japanese is True

    def test_custom_phrases(self):
        """Test custom remove phrases."""
        config = FiltersConfig(
            remove_phrases=["Light Novel", "Unabridged"],
            author_map={"猫子": "Necoco"},
        )
        assert "Light Novel" in config.remove_phrases
        assert config.author_map["猫子"] == "Necoco"


class TestMkbrrConfig:
    """Tests for MkbrrConfig dataclass."""

    def test_default_values(self):
        """Test default mkbrr configuration."""
        config = MkbrrConfig()
        assert config.preset == "mam"
        assert "mkbrr" in config.image


class TestQBittorrentConfig:
    """Tests for QBittorrentConfig dataclass."""

    def test_default_values(self):
        """Test default qBittorrent configuration."""
        config = QBittorrentConfig()
        assert config.auto_start is True
        assert "mamfast" in config.tags


class TestLoadYamlConfig:
    """Tests for YAML config loading."""

    def test_load_valid_yaml(self):
        """Test loading a valid YAML config file."""
        yaml_content = """
paths:
  library_root: "/tmp/library"
  torrent_output: "/tmp/torrents"
  seed_root: "/tmp/seed"

mam:
  max_filename_length: 200
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()
            config = load_yaml_config(Path(f.name))

        assert config["paths"]["library_root"] == "/tmp/library"
        assert config["mam"]["max_filename_length"] == 200

    def test_load_missing_file(self):
        """Test that FileNotFoundError is raised for missing file."""
        with pytest.raises(FileNotFoundError):
            load_yaml_config(Path("/nonexistent/config.yaml"))

    def test_load_empty_yaml(self):
        """Test loading empty YAML returns empty dict."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("")
            f.flush()
            config = load_yaml_config(Path(f.name))

        assert config == {} or config is None
