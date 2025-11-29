"""Tests for models module."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mamfast.models import AudiobookRelease, ReleaseStatus


class TestReleaseStatus:
    """Tests for ReleaseStatus enum."""

    def test_status_values(self):
        """Test that all expected statuses exist."""
        assert ReleaseStatus.DISCOVERED
        assert ReleaseStatus.STAGED
        assert ReleaseStatus.METADATA_FETCHED
        assert ReleaseStatus.TORRENT_CREATED
        assert ReleaseStatus.UPLOADED
        assert ReleaseStatus.COMPLETE
        assert ReleaseStatus.FAILED


class TestAudiobookRelease:
    """Tests for AudiobookRelease dataclass."""

    def test_minimal_creation(self):
        """Test creating release with minimal data."""
        release = AudiobookRelease(title="Test Book")
        assert release.title == "Test Book"
        assert release.author == ""
        assert release.asin is None
        assert release.status == ReleaseStatus.DISCOVERED

    def test_full_creation(self):
        """Test creating release with all fields."""
        release = AudiobookRelease(
            asin="B09ABCD123",
            title="Epic Fantasy",
            author="Jane Author",
            narrator="John Narrator",
            series="Fantasy Series",
            series_position="1",
            year="2024",
            source_dir=Path("/tmp/source"),
            staging_dir=Path("/tmp/staging"),
        )
        assert release.asin == "B09ABCD123"
        assert release.title == "Epic Fantasy"
        assert release.author == "Jane Author"
        assert release.narrator == "John Narrator"
        assert release.series == "Fantasy Series"
        assert release.series_position == "1"
        assert release.year == "2024"

    def test_display_name_author_and_title(self):
        """Test display_name with author and title."""
        release = AudiobookRelease(title="Test Book", author="Test Author")
        assert release.display_name == "Test Author - Test Book"

    def test_display_name_title_only(self):
        """Test display_name with only title."""
        release = AudiobookRelease(title="Test Book")
        assert release.display_name == "Test Book"

    def test_display_name_no_title(self):
        """Test display_name with no title falls back to ASIN or unknown."""
        release = AudiobookRelease(asin="B09TEST123")
        assert "B09TEST123" in release.display_name or "Unknown" in release.display_name

    def test_default_status(self):
        """Test default status is DISCOVERED."""
        release = AudiobookRelease(title="Test")
        assert release.status == ReleaseStatus.DISCOVERED

    def test_status_can_be_changed(self):
        """Test status can be updated."""
        release = AudiobookRelease(title="Test")
        release.status = ReleaseStatus.STAGED
        assert release.status == ReleaseStatus.STAGED

    def test_files_default_empty_list(self):
        """Test files defaults to empty list."""
        release = AudiobookRelease(title="Test")
        assert release.files == []
        assert isinstance(release.files, list)

    def test_files_can_be_populated(self):
        """Test files list can be populated."""
        release = AudiobookRelease(title="Test")
        release.files = [Path("/tmp/book.m4b"), Path("/tmp/cover.jpg")]
        assert len(release.files) == 2

    def test_error_field(self):
        """Test error field for failed releases."""
        release = AudiobookRelease(
            title="Failed Book",
            status=ReleaseStatus.FAILED,
            error="Connection timeout",
        )
        assert release.status == ReleaseStatus.FAILED
        assert release.error == "Connection timeout"

    def test_metadata_fields(self):
        """Test metadata fields can store dicts."""
        release = AudiobookRelease(title="Test")
        release.audnex_metadata = {"title": "Test", "runtime": 3600}
        release.mediainfo_data = {"bitrate": "128kbps"}

        assert release.audnex_metadata["runtime"] == 3600
        assert release.mediainfo_data["bitrate"] == "128kbps"

    def test_timestamps(self):
        """Test timestamp fields."""
        now = datetime.now()
        release = AudiobookRelease(
            title="Test",
            discovered_at=now,
        )
        assert release.discovered_at == now
        assert release.processed_at is None
