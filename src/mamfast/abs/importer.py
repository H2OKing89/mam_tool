"""Import audiobooks from staging to Audiobookshelf library.

Handles the final step of the MAM workflow: moving staged audiobooks
to the ABS library structure while preserving hardlinks to seed folder.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from mamfast.abs.asin import extract_asin

if TYPE_CHECKING:
    from mamfast.abs.client import AbsClient
    from mamfast.abs.indexer import AbsIndex

logger = logging.getLogger(__name__)


class ImportError(Exception):
    """Error during import operation."""


class FilesystemMismatchError(ImportError):
    """Staging and library are on different filesystems."""


class IndexNotFoundError(ImportError):
    """ABS index database not found."""


class DuplicateError(ImportError):
    """Book already exists in library."""

    def __init__(self, asin: str, existing_path: str) -> None:
        self.asin = asin
        self.existing_path = existing_path
        super().__init__(f"ASIN {asin} already exists at {existing_path}")


@dataclass
class ImportResult:
    """Result of a single import operation."""

    staging_path: Path
    target_path: Path | None
    asin: str | None
    status: str  # "success", "skipped", "failed", "duplicate"
    error: str | None = None


@dataclass
class BatchImportResult:
    """Result of a batch import operation."""

    results: list[ImportResult] = field(default_factory=list)
    success_count: int = 0
    skipped_count: int = 0
    duplicate_count: int = 0
    failed_count: int = 0

    def add(self, result: ImportResult) -> None:
        """Add a result and update counts."""
        self.results.append(result)
        if result.status == "success":
            self.success_count += 1
        elif result.status == "skipped":
            self.skipped_count += 1
        elif result.status == "duplicate":
            self.duplicate_count += 1
        elif result.status == "failed":
            self.failed_count += 1


@dataclass
class ParsedFolderName:
    """Parsed components from MAM-style folder name."""

    author: str
    title: str
    series: str | None
    series_position: str | None
    asin: str | None
    year: str | None
    narrator: str | None
    ripper_tag: str | None
    is_standalone: bool  # True if no series info


def parse_mam_folder_name(folder_name: str) -> ParsedFolderName:
    """Parse MAM-compliant folder name into components.

    Expected formats:
    - Series: "Author - Series vol_NN - Title (YYYY) (Narrator) {ripper_tag} [ASIN.B0xxx]"
    - Standalone: "Author - Title (YYYY) (Narrator) {ripper_tag} [ASIN.B0xxx]"

    Args:
        folder_name: Folder name to parse

    Returns:
        ParsedFolderName with extracted components

    Raises:
        ValueError: If folder name doesn't match expected format
    """
    # Try to extract ASIN first (multiple formats supported)
    asin = extract_asin(folder_name)

    # Extract components using patterns
    # Pattern parts:
    # - Author at start (before first " - ")
    # - Optional series with vol_XX or #XX
    # - Title
    # - Optional year in parentheses
    # - Optional narrator in parentheses
    # - Optional ripper tag in braces
    # - Optional ASIN in brackets

    # Strip ASIN markers from end for cleaner parsing
    clean_name = re.sub(r"\s*\{ASIN\.[A-Z0-9]+\}\s*$", "", folder_name)
    clean_name = re.sub(r"\s*\[ASIN\.[A-Z0-9]+\]\s*$", "", clean_name)
    clean_name = re.sub(r"\s*\[B0[A-Z0-9]{8,9}\]\s*$", "", clean_name)

    # Extract ripper tag if present (e.g., {H2OKing})
    ripper_match = re.search(r"\{([^}]+)\}\s*$", clean_name)
    ripper_tag = ripper_match.group(1) if ripper_match else None
    if ripper_match:
        clean_name = clean_name[: ripper_match.start()].strip()

    # Extract narrator if present (e.g., (Narrator Name))
    # This is typically the last parenthetical that's not a year
    narrator = None
    year = None

    # Find all parentheticals from the end
    paren_matches = list(re.finditer(r"\(([^)]+)\)", clean_name))
    for match in reversed(paren_matches):
        content = match.group(1)
        if re.match(r"^\d{4}$", content):
            year = content
        elif narrator is None and not re.match(r"^\d{4}$", content):
            narrator = content
        if year and narrator:
            break

    # Remove found parentheticals for further parsing
    if narrator:
        clean_name = clean_name.replace(f"({narrator})", "").strip()
    if year:
        clean_name = clean_name.replace(f"({year})", "").strip()

    # Split by " - " to get author and rest
    parts = clean_name.split(" - ", 1)
    if len(parts) < 2:
        # No separator found - treat whole thing as title
        return ParsedFolderName(
            author="Unknown",
            title=clean_name,
            series=None,
            series_position=None,
            asin=asin,
            year=year,
            narrator=narrator,
            ripper_tag=ripper_tag,
            is_standalone=True,
        )

    author = parts[0].strip()
    rest = parts[1].strip()

    # Check for series pattern: "Series vol_XX - Title" or "Series #XX - Title"
    series_match = re.match(
        r"^(.+?)\s+(?:vol[_.]?|#)\s*(\d+(?:\.\d+)?)\s+-\s+(.+)$",
        rest,
        re.IGNORECASE,
    )

    if series_match:
        series = series_match.group(1).strip()
        series_position = series_match.group(2)
        title = series_match.group(3).strip()
        is_standalone = False
    else:
        # No series pattern - treat rest as title
        series = None
        series_position = None
        title = rest
        is_standalone = True

    return ParsedFolderName(
        author=author,
        title=title,
        series=series,
        series_position=series_position,
        asin=asin,
        year=year,
        narrator=narrator,
        ripper_tag=ripper_tag,
        is_standalone=is_standalone,
    )


def _same_filesystem(path1: Path, path2: Path) -> bool:
    """Check if two paths are on the same filesystem.

    Args:
        path1: First path (must exist)
        path2: Second path (must exist)

    Returns:
        True if same filesystem (same st_dev)
    """
    try:
        stat1 = path1.stat()
        stat2 = path2.stat()
        return stat1.st_dev == stat2.st_dev
    except OSError:
        return False


def validate_import_prerequisites(
    staging_root: Path,
    library_root: Path,
    index_db_path: Path,
) -> list[str]:
    """Validate prerequisites for import operations.

    Checks:
    1. Staging directory exists and is accessible
    2. Library root exists and is writable
    3. Both are on the same filesystem (for atomic moves)
    4. Index database exists

    Args:
        staging_root: Staging directory (seed_root)
        library_root: ABS library root
        index_db_path: Path to abs_index.db

    Returns:
        List of error messages (empty if all checks pass)
    """
    errors: list[str] = []

    # Check staging exists
    if not staging_root.exists():
        errors.append(f"Staging directory does not exist: {staging_root}")
    elif not staging_root.is_dir():
        errors.append(f"Staging path is not a directory: {staging_root}")

    # Check library root exists and is writable
    if not library_root.exists():
        errors.append(f"Library root does not exist: {library_root}")
    elif not library_root.is_dir():
        errors.append(f"Library path is not a directory: {library_root}")
    elif not os.access(library_root, os.W_OK):
        errors.append(f"Library root is not writable: {library_root}")

    # Check same filesystem (only if both exist)
    if (
        staging_root.exists()
        and library_root.exists()
        and not _same_filesystem(staging_root, library_root)
    ):
        errors.append(
            f"Staging ({staging_root}) and library ({library_root}) "
            "are on different filesystems. Atomic move requires same filesystem "
            "to preserve hardlinks."
        )

    # Check index exists
    if not index_db_path.exists():
        errors.append(
            f"Index database not found: {index_db_path}. "
            "Run 'mamfast abs-index' first to build the library index."
        )

    return errors


def build_target_path(
    library_root: Path,
    parsed: ParsedFolderName,
    staging_folder: Path,
) -> Path:
    """Build the target path in ABS library structure.

    Structure:
    - Series: Library/Author/Series/FolderName/
    - Standalone: Library/Author/FolderName/

    Args:
        library_root: ABS library root path
        parsed: Parsed folder name components
        staging_folder: Original staging folder (for folder name)

    Returns:
        Target path for the audiobook
    """
    author_folder = parsed.author

    if parsed.series and not parsed.is_standalone:
        # Series book: Author/Series/Book
        return library_root / author_folder / parsed.series / staging_folder.name
    else:
        # Standalone: Author/Title (using full folder name)
        return library_root / author_folder / staging_folder.name


def import_single(
    staging_folder: Path,
    library_root: Path,
    index: AbsIndex,
    library_id: str,
    *,
    duplicate_policy: str = "skip",
    dry_run: bool = False,
) -> ImportResult:
    """Import a single audiobook from staging to library.

    Args:
        staging_folder: Path to staged audiobook folder
        library_root: ABS library root
        index: AbsIndex for duplicate checking
        library_id: Target ABS library ID (for logging)
        duplicate_policy: "skip", "warn", or "overwrite"
        dry_run: If True, don't actually move files

    Returns:
        ImportResult with status and details
    """
    from mamfast.abs.indexer import ImportStatus

    folder_name = staging_folder.name

    # Parse folder name
    try:
        parsed = parse_mam_folder_name(folder_name)
    except ValueError as e:
        return ImportResult(
            staging_path=staging_folder,
            target_path=None,
            asin=None,
            status="failed",
            error=f"Failed to parse folder name: {e}",
        )

    asin = parsed.asin

    # Check for duplicates if we have an ASIN
    if asin:
        is_dup, existing_path = index.check_duplicate(asin)
        if is_dup:
            if duplicate_policy == "skip":
                return ImportResult(
                    staging_path=staging_folder,
                    target_path=None,
                    asin=asin,
                    status="duplicate",
                    error=f"Already exists at {existing_path}",
                )
            elif duplicate_policy == "warn":
                logger.warning("Duplicate ASIN %s exists at %s, skipping", asin, existing_path)
                return ImportResult(
                    staging_path=staging_folder,
                    target_path=None,
                    asin=asin,
                    status="duplicate",
                    error=f"Already exists at {existing_path}",
                )
            elif duplicate_policy == "overwrite":
                # For overwrite, we proceed but note the existing path
                logger.info("Duplicate ASIN %s, will overwrite at %s", asin, existing_path)
    else:
        logger.warning("No ASIN found in folder name: %s", folder_name)

    # Build target path
    target_path = build_target_path(library_root, parsed, staging_folder)

    # Check if target already exists on disk
    if target_path.exists():
        if duplicate_policy == "overwrite":
            if not dry_run:
                import shutil

                shutil.rmtree(target_path)
                logger.info("Removed existing target: %s", target_path)
        else:
            return ImportResult(
                staging_path=staging_folder,
                target_path=target_path,
                asin=asin,
                status="duplicate",
                error=f"Target path already exists: {target_path}",
            )

    if dry_run:
        logger.info("[DRY RUN] Would move %s → %s", staging_folder, target_path)
        return ImportResult(
            staging_path=staging_folder,
            target_path=target_path,
            asin=asin,
            status="success",
        )

    # Create parent directories
    try:
        target_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return ImportResult(
            staging_path=staging_folder,
            target_path=target_path,
            asin=asin,
            status="failed",
            error=f"Failed to create directories: {e}",
        )

    # Atomic move (rename) - preserves hardlinks
    try:
        staging_folder.rename(target_path)
        logger.info("Moved: %s → %s", staging_folder.name, target_path)
    except OSError as e:
        return ImportResult(
            staging_path=staging_folder,
            target_path=target_path,
            asin=asin,
            status="failed",
            error=f"Move failed: {e}",
        )

    # Log import to database
    if asin:
        try:
            index.log_import(
                asin=asin,
                source_path=str(staging_folder),
                target_path=str(target_path),
                library_id=library_id,
                status=ImportStatus.SUCCESS,
            )
        except Exception as e:
            # Don't fail import for logging errors
            logger.warning("Failed to log import: %s", e)

    return ImportResult(
        staging_path=staging_folder,
        target_path=target_path,
        asin=asin,
        status="success",
    )


def import_batch(
    staging_folders: list[Path],
    library_root: Path,
    index: AbsIndex,
    library_id: str,
    *,
    duplicate_policy: str = "skip",
    dry_run: bool = False,
) -> BatchImportResult:
    """Import multiple audiobooks from staging to library.

    Args:
        staging_folders: List of staging folders to import
        library_root: ABS library root
        index: AbsIndex for duplicate checking
        library_id: Target ABS library ID
        duplicate_policy: "skip", "warn", or "overwrite"
        dry_run: If True, don't actually move files

    Returns:
        BatchImportResult with all results and counts
    """
    batch_result = BatchImportResult()

    for folder in staging_folders:
        result = import_single(
            staging_folder=folder,
            library_root=library_root,
            index=index,
            library_id=library_id,
            duplicate_policy=duplicate_policy,
            dry_run=dry_run,
        )
        batch_result.add(result)

    return batch_result


def trigger_scan_safe(client: AbsClient, library_id: str) -> bool:
    """Trigger ABS library scan, returning False on failure.

    Safe wrapper that doesn't raise on errors - import already succeeded,
    ABS will pick up files on its next scheduled scan anyway.

    Args:
        client: AbsClient instance
        library_id: Library to scan

    Returns:
        True if scan triggered, False if failed
    """
    try:
        client.scan_library(library_id)
        logger.info("Triggered ABS scan for library %s", library_id)
        return True
    except Exception as e:
        logger.warning("Failed to trigger ABS scan: %s", e)
        return False


def discover_staged_books(staging_root: Path) -> list[Path]:
    """Discover audiobook folders in staging directory.

    Looks for directories that contain audio files.

    Args:
        staging_root: Root staging directory

    Returns:
        List of audiobook folder paths
    """
    if not staging_root.exists() or not staging_root.is_dir():
        return []

    staged: list[Path] = []

    # Audio extensions to look for
    audio_exts = {".m4b", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".wav"}

    for item in staging_root.iterdir():
        if not item.is_dir():
            continue

        # Check if directory contains audio files
        has_audio = False
        for child in item.iterdir():
            if child.suffix.lower() in audio_exts:
                has_audio = True
                break

        # Also check subdirectories (nested structure)
        if not has_audio:
            for subdir in item.iterdir():
                if subdir.is_dir():
                    for child in subdir.iterdir():
                        if child.suffix.lower() in audio_exts:
                            has_audio = True
                            break
                if has_audio:
                    break

        if has_audio:
            staged.append(item)

    return sorted(staged)
