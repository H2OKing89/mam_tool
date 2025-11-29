"""Tests for discovery module."""

from mamfast.discovery import (
    ASIN_PATTERN,
    extract_asin_from_name,
    parse_folder_name,
)


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
