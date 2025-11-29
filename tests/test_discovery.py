"""Tests for discovery module."""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from mamfast.discovery import (
    ASIN_PATTERN,
    build_release_from_dir,
    extract_asin_from_name,
    find_audiobook_dirs,
    get_new_releases,
    get_release_by_asin,
    is_audiobook_dir,
    load_metadata_json,
    parse_folder_name,
    print_release_summary,
    scan_library,
)
from mamfast.models import AudiobookRelease


class TestExtractAsin:
    """Tests for ASIN extraction from folder names."""

    def test_standard_asin(self):
        """Test extracting standard ASIN format."""
        name = "He Who Fights with Monsters vol_01 (2021) (Shirtaloon) {ASIN.1774248182}"
        assert extract_asin_from_name(name) == "1774248182"

    def test_b_prefix_asin(self):
        """Test extracting B-prefix ASIN format."""
        name = "Some Book (2022) (Author) {ASIN.B09GHD1R2R}"
        assert extract_asin_from_name(name) == "B09GHD1R2R"

    def test_with_source_tag(self):
        """Test extracting ASIN when source tag is present."""
        name = "Book Title (2021) (Author) {ASIN.1234567890} [H2OKing]"
        assert extract_asin_from_name(name) == "1234567890"

    def test_no_asin(self):
        """Test when no ASIN is present."""
        name = "Some Book Without ASIN"
        assert extract_asin_from_name(name) is None


class TestParseFolderName:
    """Tests for folder name parsing."""

    def test_full_format(self):
        """Test parsing complete folder name format."""
        name = "He Who Fights with Monsters vol_01 (2021) (Shirtaloon) {ASIN.1774248182} [H2OKing]"
        result = parse_folder_name(name)

        assert result["title"] == "He Who Fights with Monsters"
        # volume goes into volume2 group when not preceded by " - "
        assert result["volume2"] == "01" or result["volume"] == "01"
        assert result["year"] == "2021"
        assert result["author"] == "Shirtaloon"
        assert result["asin"] == "1774248182"
        assert result["source"] == "H2OKing"

    def test_no_source_tag(self):
        """Test parsing without source tag."""
        name = "Some Book vol_03 (2020) (Jane Doe) {ASIN.B001234567}"
        result = parse_folder_name(name)

        assert result["title"] == "Some Book"
        # volume goes into volume2 group when not preceded by " - "
        assert result["volume2"] == "03" or result["volume"] == "03"
        assert result["year"] == "2020"
        assert result["author"] == "Jane Doe"
        assert result["asin"] == "B001234567"
        assert result["source"] is None

    def test_decimal_volume(self):
        """Test parsing decimal volume number."""
        name = "Book vol_10.5 (2023) (Author) {ASIN.1234}"
        result = parse_folder_name(name)

        # volume goes into volume2 group when not preceded by " - "
        assert result["volume2"] == "10.5" or result["volume"] == "10.5"


class TestAsinPattern:
    """Tests for the ASIN regex pattern."""

    def test_pattern_matches_both_bracket_styles(self):
        """Verify pattern matches both curly and square brackets."""
        # Should match curly braces
        assert ASIN_PATTERN.search("{ASIN.1234567890}")
        assert ASIN_PATTERN.search("{ASIN.B09ABCDEFG}")

        # Should also match square brackets (Libation uses both)
        assert ASIN_PATTERN.search("[ASIN.1234567890]")
        assert ASIN_PATTERN.search("[ASIN.B09ABCDEFG]")

        # Should not match without brackets
        assert ASIN_PATTERN.search("ASIN.1234567890") is None


class TestLoadMetadataJson:
    """Tests for metadata.json loading."""

    def test_loads_valid_json(self):
        """Test loading valid metadata.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = Path(tmpdir) / "metadata.json"
            meta_path.write_text(
                json.dumps(
                    {
                        "asin": "B09TEST123",
                        "title": "Test Book",
                        "authors": ["John Smith"],
                        "narrators": ["Jane Doe"],
                        "series": "Epic Series",
                        "year": "2023",
                        "publisher": "Test Publisher",
                        "language": "English",
                    }
                )
            )

            result = load_metadata_json(meta_path)

            assert result is not None
            assert result.asin == "B09TEST123"
            assert result.title == "Test Book"
            assert result.authors == ["John Smith"]
            assert result.narrators == ["Jane Doe"]
            assert result.year == "2023"

    def test_handles_author_dicts(self):
        """Test handling authors as list of dicts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = Path(tmpdir) / "metadata.json"
            meta_path.write_text(
                json.dumps(
                    {
                        "authors": [{"name": "John Smith"}, {"name": "Jane Doe"}],
                    }
                )
            )

            result = load_metadata_json(meta_path)

            assert result is not None
            assert result.authors == ["John Smith", "Jane Doe"]

    def test_handles_series_as_dict(self):
        """Test handling series as dict."""
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = Path(tmpdir) / "metadata.json"
            meta_path.write_text(
                json.dumps(
                    {
                        "series": {"name": "Epic Series", "position": 3},
                    }
                )
            )

            result = load_metadata_json(meta_path)

            assert result is not None
            assert result.series_name == "Epic Series"
            assert result.series_position == "3"

    def test_handles_series_as_list(self):
        """Test handling series as list of dicts."""
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = Path(tmpdir) / "metadata.json"
            meta_path.write_text(
                json.dumps(
                    {
                        "series": [{"name": "Series 1", "position": 1}],
                    }
                )
            )

            result = load_metadata_json(meta_path)

            assert result is not None
            assert result.series_name == "Series 1"
            assert result.series_position == "1"

    def test_returns_none_for_missing_file(self):
        """Test returning None for missing file."""
        result = load_metadata_json(Path("/nonexistent/metadata.json"))
        assert result is None

    def test_returns_none_for_invalid_json(self):
        """Test returning None for invalid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = Path(tmpdir) / "metadata.json"
            meta_path.write_text("not valid json {{{")

            result = load_metadata_json(meta_path)
            assert result is None

    def test_handles_runtime_minutes(self):
        """Test parsing runtime minutes."""
        with tempfile.TemporaryDirectory() as tmpdir:
            meta_path = Path(tmpdir) / "metadata.json"
            meta_path.write_text(json.dumps({"runtimeLengthMin": 420}))

            result = load_metadata_json(meta_path)

            assert result is not None
            assert result.runtime_minutes == 420


class TestIsAudiobookDir:
    """Tests for audiobook directory detection."""

    def test_directory_with_m4b(self):
        """Test directory containing m4b file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "book.m4b").touch()

            assert is_audiobook_dir(path) is True

    def test_directory_without_m4b(self):
        """Test directory without m4b file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "book.mp3").touch()

            assert is_audiobook_dir(path) is False

    def test_not_a_directory(self):
        """Test non-directory path."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "file.txt"
            path.touch()

            assert is_audiobook_dir(path) is False

    def test_case_insensitive_extension(self):
        """Test case-insensitive .M4B extension."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "book.M4B").touch()

            assert is_audiobook_dir(path) is True


class TestFindAudiobookDirs:
    """Tests for finding audiobook directories."""

    def test_finds_audiobooks_in_tree(self):
        """Test finding audiobooks in library structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create: Author1/Series1/Book1/
            book1 = root / "Author1" / "Series1" / "Book1 {ASIN.B001}"
            book1.mkdir(parents=True)
            (book1 / "book.m4b").touch()

            # Create: Author2/Book2/
            book2 = root / "Author2" / "Book2 {ASIN.B002}"
            book2.mkdir(parents=True)
            (book2 / "book.m4b").touch()

            dirs = find_audiobook_dirs(root)

            assert len(dirs) == 2
            assert book1 in dirs
            assert book2 in dirs

    def test_nonexistent_library(self):
        """Test handling non-existent library."""
        dirs = find_audiobook_dirs(Path("/nonexistent/library"))
        assert dirs == []

    def test_empty_library(self):
        """Test empty library."""
        with tempfile.TemporaryDirectory() as tmpdir:
            dirs = find_audiobook_dirs(Path(tmpdir))
            assert dirs == []


class TestBuildReleaseFromDir:
    """Tests for building release from directory."""

    def test_builds_release_from_folder_name(self):
        """Test building release from folder name."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create settings mock
            mock_settings = MagicMock()
            mock_settings.paths.library_root = Path(tmpdir)
            mock_settings.mam.allowed_extensions = [".m4b", ".cue", ".pdf"]

            root = Path(tmpdir)
            book_dir = root / "Author" / "Book Title (2023) {ASIN.B09TEST123} [Source]"
            book_dir.mkdir(parents=True)
            (book_dir / "book.m4b").touch()
            (book_dir / "cover.jpg").touch()

            with patch("mamfast.discovery.get_settings", return_value=mock_settings):
                release = build_release_from_dir(book_dir)

            assert release.asin == "B09TEST123"
            assert release.source_dir == book_dir
            assert len(release.files) >= 1

    def test_builds_release_from_metadata_json(self):
        """Test building release preferring metadata.json."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.paths.library_root = Path(tmpdir)
            mock_settings.mam.allowed_extensions = [".m4b"]

            root = Path(tmpdir)
            book_dir = root / "Author" / "Book"
            book_dir.mkdir(parents=True)
            (book_dir / "book.m4b").touch()

            # Add metadata.json
            meta = {
                "asin": "B09META123",
                "title": "Metadata Title",
                "authors": ["Meta Author"],
                "narrators": ["Meta Narrator"],
            }
            (book_dir / "metadata.json").write_text(json.dumps(meta))

            with patch("mamfast.discovery.get_settings", return_value=mock_settings):
                release = build_release_from_dir(book_dir)

            assert release.asin == "B09META123"
            assert release.title == "Metadata Title"
            assert release.author == "Meta Author"
            assert release.narrator == "Meta Narrator"


class TestScanLibrary:
    """Tests for library scanning."""

    def test_scans_library(self):
        """Test scanning library for audiobooks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.paths.library_root = Path(tmpdir)
            mock_settings.mam.allowed_extensions = [".m4b"]

            root = Path(tmpdir)

            # Create books
            book1 = root / "Author" / "Book1 {ASIN.B001}"
            book1.mkdir(parents=True)
            (book1 / "book.m4b").touch()

            book2 = root / "Author" / "Book2 {ASIN.B002}"
            book2.mkdir(parents=True)
            (book2 / "book.m4b").touch()

            with patch("mamfast.discovery.get_settings", return_value=mock_settings):
                releases = scan_library(root)

            assert len(releases) == 2


class TestGetNewReleases:
    """Tests for getting new (unprocessed) releases."""

    def test_filters_processed_releases(self):
        """Test filtering out already processed releases."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.paths.library_root = Path(tmpdir)
            mock_settings.mam.allowed_extensions = [".m4b"]

            root = Path(tmpdir)

            # Create two books
            book1 = root / "Author" / "Book1 {ASIN.B001}"
            book1.mkdir(parents=True)
            (book1 / "book.m4b").touch()

            book2 = root / "Author" / "Book2 {ASIN.B002}"
            book2.mkdir(parents=True)
            (book2 / "book.m4b").touch()

            # Mock processed identifiers (B001 already processed)
            with (
                patch("mamfast.discovery.get_settings", return_value=mock_settings),
                patch("mamfast.discovery.get_processed_identifiers", return_value={"B001"}),
            ):
                new_releases = get_new_releases(root)

            assert len(new_releases) == 1
            assert new_releases[0].asin == "B002"


class TestGetReleaseByAsin:
    """Tests for finding release by ASIN."""

    def test_finds_release_by_asin(self):
        """Test finding specific release by ASIN."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.paths.library_root = Path(tmpdir)
            mock_settings.mam.allowed_extensions = [".m4b"]

            root = Path(tmpdir)
            book = root / "Author" / "Book {ASIN.B09TARGET}"
            book.mkdir(parents=True)
            (book / "book.m4b").touch()

            with patch("mamfast.discovery.get_settings", return_value=mock_settings):
                release = get_release_by_asin("B09TARGET", root)

            assert release is not None
            assert release.asin == "B09TARGET"

    def test_returns_none_for_not_found(self):
        """Test returning None when ASIN not found."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mock_settings = MagicMock()
            mock_settings.paths.library_root = Path(tmpdir)
            mock_settings.mam.allowed_extensions = [".m4b"]

            with patch("mamfast.discovery.get_settings", return_value=mock_settings):
                release = get_release_by_asin("NOTFOUND", Path(tmpdir))

            assert release is None


class TestPrintReleaseSummary:
    """Tests for release summary printing."""

    def test_prints_summary(self, capsys):
        """Test printing release summary."""
        releases = [
            AudiobookRelease(
                title="Book 1",
                author="Author",
                asin="B001",
                series="Series",
                series_position="1",
            ),
            AudiobookRelease(
                title="Book 2",
                author="Author",
                asin=None,  # No ASIN
            ),
        ]
        releases[0].files = [Path("/fake/book.m4b")]
        releases[1].files = []

        print_release_summary(releases)

        captured = capsys.readouterr()
        assert "2 release(s)" in captured.out
        assert "Book 1" in captured.out
        assert "Book 2" in captured.out
        assert "B001" in captured.out
        assert "Series #1" in captured.out
        assert "NO ASIN" in captured.out

    def test_prints_no_releases(self, capsys):
        """Test printing when no releases."""
        print_release_summary([])

        captured = capsys.readouterr()
        assert "No releases found" in captured.out
