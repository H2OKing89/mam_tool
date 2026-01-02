"""Tests for ABS metadata.json write validation.

Ensures that write paths enforce title requirements and that
the strict validation cannot be accidentally bypassed.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from shelfr.abs.metadata_builder import write_abs_metadata_json
from shelfr.schemas.abs_metadata import (
    AbsMetadataJson,
    validate_abs_metadata_for_write,
)


class TestValidateAbsMetadataForWrite:
    """Tests for validate_abs_metadata_for_write()."""

    def test_valid_title_passes(self) -> None:
        """Valid title passes validation."""
        model = AbsMetadataJson(title="Mark of the Founder")
        result = validate_abs_metadata_for_write(model)
        assert result.title == "Mark of the Founder"

    def test_title_none_raises(self) -> None:
        """title=None raises ValueError."""
        model = AbsMetadataJson(title=None)
        with pytest.raises(ValueError, match="non-empty title"):
            validate_abs_metadata_for_write(model)

    def test_title_empty_string_raises(self) -> None:
        """title="" raises ValueError."""
        model = AbsMetadataJson(title="")
        with pytest.raises(ValueError, match="non-empty title"):
            validate_abs_metadata_for_write(model)

    def test_title_whitespace_only_raises(self) -> None:
        """title="   " raises ValueError."""
        model = AbsMetadataJson(title="   ")
        with pytest.raises(ValueError, match="non-empty title"):
            validate_abs_metadata_for_write(model)

    def test_title_with_whitespace_padding_passes(self) -> None:
        """title="  Real Title  " passes (has non-whitespace content)."""
        model = AbsMetadataJson(title="  Real Title  ")
        result = validate_abs_metadata_for_write(model)
        assert result.title == "  Real Title  "

    def test_accepts_dict_input(self) -> None:
        """Function accepts dict input and validates."""
        data = {"title": "Test Book"}
        result = validate_abs_metadata_for_write(data)
        assert result.title == "Test Book"

    def test_dict_with_missing_title_raises(self) -> None:
        """Dict with missing title raises ValueError."""
        data: dict[str, str] = {}
        with pytest.raises(ValueError, match="non-empty title"):
            validate_abs_metadata_for_write(data)

    def test_dict_with_invalid_type_raises_pydantic_error(self) -> None:
        """Dict with invalid types raises pydantic.ValidationError."""
        from pydantic import ValidationError

        # title should be str, not int - triggers Pydantic validation
        data = {"title": 123, "authors": "not a list"}
        with pytest.raises(ValidationError):
            validate_abs_metadata_for_write(data)


class TestWriteAbsMetadataJsonStrict:
    """Tests for write_abs_metadata_json() strict mode enforcement."""

    def test_strict_true_valid_title_writes(self, tmp_path: Path) -> None:
        """strict=True with valid title writes successfully."""
        model = AbsMetadataJson(title="Valid Title", authors=["Author One"])
        result = write_abs_metadata_json(tmp_path, model, strict=True)

        assert result is not None
        assert result.exists()
        assert "Valid Title" in result.read_text()

    def test_strict_true_missing_title_raises(self, tmp_path: Path) -> None:
        """strict=True with missing title raises ValueError before writing."""
        model = AbsMetadataJson(title=None)

        with pytest.raises(ValueError, match="non-empty title"):
            write_abs_metadata_json(tmp_path, model, strict=True)

        # File should NOT be created
        assert not (tmp_path / "metadata.json").exists()

    def test_strict_true_empty_title_raises(self, tmp_path: Path) -> None:
        """strict=True with empty title raises ValueError."""
        model = AbsMetadataJson(title="")

        with pytest.raises(ValueError, match="non-empty title"):
            write_abs_metadata_json(tmp_path, model, strict=True)

        assert not (tmp_path / "metadata.json").exists()

    def test_strict_true_whitespace_title_raises(self, tmp_path: Path) -> None:
        """strict=True with whitespace-only title raises ValueError."""
        model = AbsMetadataJson(title="   \t\n")

        with pytest.raises(ValueError, match="non-empty title"):
            write_abs_metadata_json(tmp_path, model, strict=True)

        assert not (tmp_path / "metadata.json").exists()

    def test_strict_false_allows_missing_title(self, tmp_path: Path) -> None:
        """strict=False allows writing without title (escape hatch)."""
        model = AbsMetadataJson(title=None, authors=["Author"])
        result = write_abs_metadata_json(tmp_path, model, strict=False)

        assert result is not None
        assert result.exists()

    def test_strict_false_allows_empty_title(self, tmp_path: Path) -> None:
        """strict=False allows writing with empty title."""
        model = AbsMetadataJson(title="", authors=["Author"])
        result = write_abs_metadata_json(tmp_path, model, strict=False)

        assert result is not None
        assert result.exists()

    def test_strict_default_is_true(self, tmp_path: Path) -> None:
        """Default behavior is strict=True."""
        model = AbsMetadataJson(title=None)

        # Without explicit strict=False, should raise
        with pytest.raises(ValueError, match="non-empty title"):
            write_abs_metadata_json(tmp_path, model)

    def test_dry_run_with_valid_title(self, tmp_path: Path) -> None:
        """dry_run=True with valid title returns None without writing."""
        model = AbsMetadataJson(title="Valid Title")
        result = write_abs_metadata_json(tmp_path, model, dry_run=True, strict=True)

        assert result is None
        assert not (tmp_path / "metadata.json").exists()

    def test_dry_run_still_validates(self, tmp_path: Path) -> None:
        """dry_run=True still validates (catches invalid data before committing)."""
        model = AbsMetadataJson(title=None)

        # Validation happens before dry_run check - this is correct behavior
        # You want to know your metadata is invalid even in dry-run mode
        with pytest.raises(ValueError, match="non-empty title"):
            write_abs_metadata_json(tmp_path, model, dry_run=True, strict=True)

    def test_pydantic_validation_error_propagates(self, tmp_path: Path) -> None:
        """Pydantic ValidationError propagates when dict has invalid types."""
        from pydantic import ValidationError

        # Pass dict with invalid types directly to validate_abs_metadata_for_write
        # (write_abs_metadata_json expects AbsMetadataJson, not dict)
        data = {"title": 123}  # title should be str
        with pytest.raises(ValidationError):
            validate_abs_metadata_for_write(data)

        # File should not be created
        assert not (tmp_path / "metadata.json").exists()


class TestJsonExporterUsesStrictWrite:
    """Tests that JsonExporter uses strict write validation."""

    @pytest.mark.asyncio
    async def test_export_with_missing_title_raises(self, tmp_path: Path) -> None:
        """JsonExporter.export() raises when title is missing (strict by default)."""
        from shelfr.metadata.aggregator import AggregatedResult
        from shelfr.metadata.exporters.json import JsonExporter

        # Create a minimal AggregatedResult with missing title
        result = AggregatedResult(
            fields={"authors": ["Test Author"]},  # No title
            sources={},
        )

        exporter = JsonExporter()

        with pytest.raises(ValueError, match="non-empty title"):
            await exporter.export(result, tmp_path, strict=True)

        assert not (tmp_path / "metadata.json").exists()

    @pytest.mark.asyncio
    async def test_export_with_valid_title_succeeds(self, tmp_path: Path) -> None:
        """JsonExporter.export() succeeds with valid title."""
        from shelfr.metadata.aggregator import AggregatedResult
        from shelfr.metadata.exporters.json import JsonExporter

        result = AggregatedResult(
            fields={"title": "Valid Book Title", "authors": ["Test Author"]},
            sources={},
        )

        exporter = JsonExporter()
        output_path = await exporter.export(result, tmp_path)

        assert output_path.exists()
        assert "Valid Book Title" in output_path.read_text()

    @pytest.mark.asyncio
    async def test_export_strict_false_allows_missing_title(self, tmp_path: Path) -> None:
        """JsonExporter.export(strict=False) allows missing title."""
        from shelfr.metadata.aggregator import AggregatedResult
        from shelfr.metadata.exporters.json import JsonExporter

        result = AggregatedResult(
            fields={"authors": ["Test Author"]},  # No title
            sources={},
        )

        exporter = JsonExporter()
        # With strict=False, missing title should be allowed
        output_path = await exporter.export(result, tmp_path, strict=False)

        assert output_path.exists()
        # File is written (title will be null/missing in JSON)
