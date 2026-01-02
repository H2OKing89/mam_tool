"""
JSON exporter for Audiobookshelf metadata.json sidecar.

This exporter converts aggregated metadata to the ABS metadata.json format,
which is read by Audiobookshelf during library scans.

The output matches the AbsMetadataJson schema in schemas/abs_metadata.py.
All writes go through write_abs_metadata_json() to enforce title validation.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

from shelfr.abs.metadata_builder import write_abs_metadata_json
from shelfr.exceptions import ExportError
from shelfr.schemas.abs_metadata import AbsChapter, AbsMetadataJson

if TYPE_CHECKING:
    from shelfr.metadata.aggregator import AggregatedResult

logger = logging.getLogger(__name__)


class JsonExporter:
    """Exporter for ABS metadata.json sidecar format.

    Converts aggregated metadata fields to the format expected by
    Audiobookshelf during library scans.

    Field mappings (canonical -> ABS):
    - title -> title
    - subtitle -> subtitle
    - authors -> authors (list of names, not Person objects)
    - narrators -> narrators (list of names)
    - series_name -> series (formatted as "Name #Position")
    - genres -> genres
    - description -> description
    - release_date -> publishedDate
    - publisher -> publisher
    - isbn -> isbn
    - language -> language
    - is_adult -> explicit
    - chapters -> chapters
    """

    name: str = "json"
    file_extension: str = ".json"
    description: str = "Audiobookshelf metadata.json sidecar"

    async def export(
        self,
        result: AggregatedResult,
        output_dir: Path,
        *,
        strict: bool = True,
    ) -> Path:
        """Export aggregated metadata to metadata.json.

        Uses write_abs_metadata_json() as the single write gate to ensure
        consistent validation across all export paths.

        Args:
            result: Aggregated metadata from MetadataAggregator
            output_dir: Directory to write metadata.json
            strict: If True (default), require non-empty title.
                Set to False only for debug/partial workflows.

        Returns:
            Path to the written file

        Raises:
            ExportError: If file write fails (permission denied, disk full, etc.)
            ValueError: If strict=True and title is missing/empty
        """
        # Convert aggregated fields to AbsMetadataJson model
        abs_model = self._convert_to_abs_model(result)

        # Write through the validated write gate
        try:
            output_path = write_abs_metadata_json(output_dir, abs_model, strict=strict)
        except OSError as e:
            raise ExportError(
                f"Failed to write metadata.json: {e}",
                format_name=self.name,
                output_path=output_dir / "metadata.json",
            ) from e

        if output_path is None:
            # Should not happen without dry_run, but handle gracefully
            raise ExportError(
                "write_abs_metadata_json returned None unexpectedly",
                format_name=self.name,
                output_path=output_dir / "metadata.json",
            )

        logger.debug("Exported metadata to %s", output_path)
        return output_path

    def _convert_to_abs_model(self, result: AggregatedResult) -> AbsMetadataJson:
        """Convert aggregated result to AbsMetadataJson model.

        Args:
            result: Aggregated metadata

        Returns:
            AbsMetadataJson model ready for write_abs_metadata_json()
        """
        fields = result.fields

        # Title - pass through as-is, let validation handle missing titles
        # In strict mode, write_abs_metadata_json() will raise ValueError
        # In non-strict mode, None/empty title will be written
        title = fields.get("title")
        if not title:
            logger.warning("Missing title in aggregated metadata")

        # Optional simple fields
        subtitle = fields.get("subtitle")
        publisher = fields.get("publisher")
        description = fields.get("description")
        isbn = fields.get("isbn")
        language = fields.get("language")
        asin = fields.get("asin")

        # Boolean fields
        explicit = bool(fields.get("is_adult"))

        # People lists - extract names from Person objects or use strings directly
        authors = self._extract_names(fields.get("authors", []))
        narrators = self._extract_names(fields.get("narrators", []))

        # Series - format as "Name #Position"
        series: list[str] = []
        series_name = fields.get("series_name")
        series_position = fields.get("series_position")
        if series_name:
            series_str = series_name
            if series_position:
                series_str = f"{series_name} #{series_position}"
            series.append(series_str)

        # Genres - extract names from Genre objects or use strings directly
        genres = self._extract_names(fields.get("genres", []))

        # Tags - populate with Adult flag (matches OPF pattern)
        tags: list[str] = []
        if fields.get("is_adult"):
            tags.append("Adult")

        # Date fields - ABS uses publishedYear and publishedDate
        published_year: str | None = None
        published_date: str | None = None
        release_date = fields.get("release_date")
        if release_date:
            year = self._extract_year(release_date)
            if year:
                published_year = str(year)
            if isinstance(release_date, str) and len(release_date) >= 10:
                published_date = release_date[:10]

        # Chapters
        chapters = self._convert_chapters(fields.get("chapters", []))

        return AbsMetadataJson(
            title=title,
            subtitle=subtitle,
            authors=authors,  # Empty list is fine, default_factory handles it
            narrators=narrators,
            series=series,
            genres=genres,
            tags=tags,
            publisher=publisher,
            description=description,
            isbn=isbn,
            asin=asin,
            language=language,
            explicit=explicit,
            published_year=published_year,
            published_date=published_date,
            chapters=chapters,  # Empty list is fine
        )

    def _extract_names(self, items: list[Any]) -> list[str]:
        """Extract names from Person/Genre objects or return strings as-is.

        Args:
            items: List of Person/Genre objects or strings

        Returns:
            List of name strings
        """
        names = []
        for item in items:
            if isinstance(item, str):
                names.append(item)
            elif hasattr(item, "name"):
                names.append(item.name)
            elif isinstance(item, dict) and "name" in item:
                names.append(item["name"])
        return names

    def _extract_year(self, date_value: Any) -> int | None:
        """Extract year from various date formats.

        Args:
            date_value: Date as string, datetime, or other format

        Returns:
            Year as int, or None if extraction fails
        """
        if date_value is None:
            return None

        # Handle datetime objects
        if hasattr(date_value, "year"):
            year: int = date_value.year
            return year

        # Handle string dates (ISO format: YYYY-MM-DD or YYYY)
        if isinstance(date_value, str) and len(date_value) >= 4:
            try:
                return int(date_value[:4])
            except ValueError:
                pass

        return None

    def _convert_chapters(self, chapters: list[Any]) -> list[AbsChapter]:
        """Convert chapter data to AbsChapter models.

        Args:
            chapters: List of Chapter objects or dicts

        Returns:
            List of AbsChapter models
        """
        abs_chapters: list[AbsChapter] = []
        for i, chapter in enumerate(chapters):
            if isinstance(chapter, dict):
                start_val = chapter.get("start") or chapter.get("start_time") or 0
                end_val = chapter.get("end") or chapter.get("end_time") or 0
                abs_chapters.append(
                    AbsChapter(
                        id=chapter.get("id", i),
                        start=float(start_val),
                        end=float(end_val),
                        title=chapter.get("title", f"Chapter {i + 1}"),
                    )
                )
            elif hasattr(chapter, "title"):
                # Chapter dataclass or similar
                start_val = getattr(chapter, "start_time", None)
                if start_val is None:
                    start_val = getattr(chapter, "start", 0)
                end_val = getattr(chapter, "end_time", None)
                if end_val is None:
                    end_val = getattr(chapter, "end", 0)
                abs_chapters.append(
                    AbsChapter(
                        id=getattr(chapter, "id", i),
                        start=float(start_val or 0),
                        end=float(end_val or 0),
                        title=chapter.title,
                    )
                )
        return abs_chapters
