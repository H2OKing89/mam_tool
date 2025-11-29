"""
Metadata fetching from Audnex API and MediaInfo.

Audnex API: https://api.audnex.us
- GET /books/{asin} - Get book metadata by ASIN
- GET /authors/{asin} - Get author info

MediaInfo: Command-line tool for technical metadata
- mediainfo --Output=JSON <file>

MAM JSON: Fast fillout format for MAM uploads
"""

from __future__ import annotations

import json
import logging
import subprocess
from pathlib import Path
from typing import TYPE_CHECKING, Any

import httpx

from mamfast.config import get_settings

if TYPE_CHECKING:
    from mamfast.models import AudiobookRelease

logger = logging.getLogger(__name__)


# =============================================================================
# Audnex API
# =============================================================================


def fetch_audnex_book(asin: str) -> dict[str, Any] | None:
    """
    Fetch book metadata from Audnex API.

    Args:
        asin: Audible ASIN (e.g., "B000SEI1RG")

    Returns:
        Parsed JSON response or None if not found.
    """
    settings = get_settings()
    url = f"{settings.audnex.base_url}/books/{asin}"

    logger.debug(f"Fetching Audnex metadata: {url}")

    try:
        with httpx.Client(timeout=settings.audnex.timeout_seconds) as client:
            response = client.get(url)

            if response.status_code == 404:
                logger.warning(f"ASIN not found in Audnex: {asin}")
                return None

            response.raise_for_status()
            data: dict[str, Any] = response.json()

            logger.info(f"Fetched Audnex metadata for ASIN: {asin}")
            return data

    except httpx.TimeoutException:
        logger.error(f"Timeout fetching Audnex metadata for: {asin}")
        return None

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error from Audnex: {e}")
        return None

    except Exception as e:
        logger.exception(f"Error fetching Audnex metadata: {e}")
        return None


def fetch_audnex_author(asin: str) -> dict[str, Any] | None:
    """
    Fetch author metadata from Audnex API.

    Args:
        asin: Author ASIN

    Returns:
        Parsed JSON response or None if not found.
    """
    settings = get_settings()
    url = f"{settings.audnex.base_url}/authors/{asin}"

    logger.debug(f"Fetching Audnex author: {url}")

    try:
        with httpx.Client(timeout=settings.audnex.timeout_seconds) as client:
            response = client.get(url)

            if response.status_code == 404:
                logger.warning(f"Author ASIN not found: {asin}")
                return None

            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data

    except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
        logger.warning(f"Error fetching author metadata: {e}")
        return None


def save_audnex_json(data: dict[str, Any], output_path: Path) -> None:
    """Write Audnex metadata to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.debug(f"Saved Audnex metadata to: {output_path}")


# =============================================================================
# MediaInfo
# =============================================================================


def run_mediainfo(file_path: Path) -> dict[str, Any] | None:
    """
    Run mediainfo on a file and return parsed JSON output.

    Args:
        file_path: Path to audio file (typically .m4b)

    Returns:
        Parsed MediaInfo JSON or None on error.
    """
    settings = get_settings()
    binary = settings.mediainfo.binary

    if not file_path.exists():
        logger.error(f"File not found for mediainfo: {file_path}")
        return None

    cmd = [
        binary,
        "--Output=JSON",
        str(file_path),
    ]

    logger.debug(f"Running mediainfo: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=True,
        )

        data: dict[str, Any] = json.loads(result.stdout)
        logger.info(f"Got MediaInfo for: {file_path.name}")
        return data

    except FileNotFoundError:
        logger.error(f"mediainfo binary not found: {binary}")
        return None

    except subprocess.CalledProcessError as e:
        logger.error(f"mediainfo failed: {e.stderr}")
        return None

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON from mediainfo: {e}")
        return None


def save_mediainfo_json(data: dict[str, Any], output_path: Path) -> None:
    """Write MediaInfo data to JSON file."""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    logger.debug(f"Saved MediaInfo to: {output_path}")


# =============================================================================
# Combined Operations
# =============================================================================


def fetch_all_metadata(
    asin: str | None,
    m4b_path: Path | None,
    output_dir: Path,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """
    Fetch both Audnex and MediaInfo metadata, saving to output directory.

    Args:
        asin: Audible ASIN (None to skip Audnex)
        m4b_path: Path to m4b file (None to skip MediaInfo)
        output_dir: Directory to save JSON files

    Returns:
        Tuple of (audnex_data, mediainfo_data), either may be None.
    """
    audnex_data = None
    mediainfo_data = None

    output_dir.mkdir(parents=True, exist_ok=True)

    # Audnex
    if asin:
        audnex_data = fetch_audnex_book(asin)
        if audnex_data:
            save_audnex_json(audnex_data, output_dir / "audnex.json")

    # MediaInfo
    if m4b_path and m4b_path.exists():
        mediainfo_data = run_mediainfo(m4b_path)
        if mediainfo_data:
            save_mediainfo_json(mediainfo_data, output_dir / "mediainfo.json")

    return audnex_data, mediainfo_data


# =============================================================================
# MAM JSON Export
# =============================================================================

# MAM category mapping based on Audnex genres
MAM_CATEGORY_MAP: dict[str, int] = {
    # Fiction categories
    "action & adventure": 1,
    "art": 2,
    "biography": 3,
    "business": 4,
    "comedy": 5,
    "computer": 7,
    "contemporary": 59,
    "crime": 9,
    "drama": 60,
    "education": 11,
    "fantasy": 13,
    "food": 14,
    "health": 16,
    "historical": 17,
    "horror": 19,
    "humor": 20,
    "juvenile": 23,
    "language": 24,
    "lgbtq": 25,
    "literary classics": 28,
    "literary fiction": 57,
    "litrpg": 29,
    "math": 30,
    "medicine": 31,
    "music": 32,
    "mystery": 34,
    "nature": 35,
    "paranormal": 36,
    "philosophy": 37,
    "poetry": 38,
    "politics": 39,
    "progression fantasy": 58,
    "reference": 40,
    "religion": 41,
    "romance": 42,
    "science": 44,
    "science fiction": 45,
    "sci-fi": 45,
    "self-help": 46,
    "sports": 49,
    "superheroes": 56,
    "technology": 50,
    "thriller": 51,
    "suspense": 51,
    "travel": 52,
    "urban fantasy": 53,
    "western": 54,
    "young adult": 55,
    "epic": 13,  # Map Epic to Fantasy
    "paranormal & urban": 53,  # Urban Fantasy
}


def _map_genres_to_categories(genres: list[dict[str, Any]]) -> list[int]:
    """
    Map Audnex genres to MAM category IDs.

    Args:
        genres: List of genre dicts from Audnex (with 'name' key)

    Returns:
        List of unique MAM category IDs
    """
    categories: set[int] = set()

    for genre in genres:
        name = genre.get("name", "").lower()
        if name in MAM_CATEGORY_MAP:
            categories.add(MAM_CATEGORY_MAP[name])
        else:
            # Try partial matching
            for key, cat_id in MAM_CATEGORY_MAP.items():
                if key in name or name in key:
                    categories.add(cat_id)
                    break

    return sorted(categories)


def _build_series_list(audnex_data: dict[str, Any]) -> list[dict[str, Any]]:
    """
    Build series list for MAM JSON from Audnex data.

    Args:
        audnex_data: Audnex book metadata

    Returns:
        List of series dicts with 'name' and 'number' keys
    """
    series_list = []

    # Primary series
    primary = audnex_data.get("seriesPrimary")
    if primary:
        series_list.append(
            {
                "name": primary.get("name", ""),
                "number": primary.get("position", ""),
            }
        )

    # Secondary series (if any)
    secondary = audnex_data.get("seriesSecondary")
    if secondary:
        series_list.append(
            {
                "name": secondary.get("name", ""),
                "number": secondary.get("position", ""),
            }
        )

    return series_list


def _clean_html(text: str) -> str:
    """
    Clean HTML tags from description text.

    Simple approach - just strips common HTML tags.
    """
    import re

    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Decode common entities
    text = text.replace("&amp;", "&")
    text = text.replace("&lt;", "<")
    text = text.replace("&gt;", ">")
    text = text.replace("&quot;", '"')
    text = text.replace("&#39;", "'")
    text = text.replace("&nbsp;", " ")
    return text.strip()


def _get_mediainfo_string(mediainfo_data: dict[str, Any] | None) -> str | None:
    """
    Convert mediainfo JSON to a string for MAM.

    MAM expects the mediainfo JSON as a string in the mediaInfo field.
    """
    if not mediainfo_data:
        return None
    return json.dumps(mediainfo_data, ensure_ascii=False)


def build_mam_json(
    release: AudiobookRelease,
    audnex_data: dict[str, Any] | None = None,
    mediainfo_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Build MAM fast-fillout JSON from release metadata.

    Args:
        release: AudiobookRelease object with metadata
        audnex_data: Optional Audnex API response (uses release.audnex_metadata if None)
        mediainfo_data: Optional MediaInfo JSON (uses release.mediainfo_data if None)

    Returns:
        Dict ready to be serialized as MAM JSON
    """
    # Use release metadata if not provided
    audnex = audnex_data or release.audnex_metadata or {}
    mediainfo = mediainfo_data or release.mediainfo_data

    mam_json: dict[str, Any] = {}

    # Title - use Audnex title or fallback to release title
    title = audnex.get("title") or release.title
    if title:
        mam_json["title"] = title

    # Authors
    authors = audnex.get("authors", [])
    if authors:
        mam_json["authors"] = [a.get("name", "") for a in authors if a.get("name")]
    elif release.author:
        mam_json["authors"] = [release.author]

    # Narrators
    narrators = audnex.get("narrators", [])
    if narrators:
        mam_json["narrators"] = [n.get("name", "") for n in narrators if n.get("name")]
    elif release.narrator:
        mam_json["narrators"] = [release.narrator]

    # Description (summary from Audnex, cleaned of HTML)
    summary = audnex.get("summary")
    if summary:
        mam_json["description"] = _clean_html(summary)

    # Series
    series_list = _build_series_list(audnex)
    if series_list:
        mam_json["series"] = series_list
    elif release.series:
        mam_json["series"] = [
            {
                "name": release.series,
                "number": release.series_position or "",
            }
        ]

    # Subtitle
    subtitle = audnex.get("subtitle")
    if subtitle:
        mam_json["subtitle"] = subtitle

    # Thumbnail (cover image URL)
    image = audnex.get("image")
    if image:
        mam_json["thumbnail"] = image

    # Language
    language = audnex.get("language")
    if language:
        # Capitalize first letter
        mam_json["language"] = language.capitalize()

    # Categories - map genres to MAM category IDs
    genres = audnex.get("genres", [])
    if genres:
        categories = _map_genres_to_categories(genres)
        if categories:
            mam_json["categories"] = categories

    # Media type - always Audiobook (1)
    mam_json["mediaType"] = 1

    # Tags - build from genres
    if genres:
        tag_names = [g.get("name", "") for g in genres if g.get("type") == "tag"]
        if tag_names:
            mam_json["tags"] = ", ".join(tag_names)

    # MediaInfo - as JSON string
    mediainfo_str = _get_mediainfo_string(mediainfo)
    if mediainfo_str:
        mam_json["mediaInfo"] = mediainfo_str

    # ISBN (if available)
    isbn = audnex.get("isbn")
    if isbn:
        mam_json["isbn"] = isbn

    # Flags
    flags = []
    if audnex.get("isAdult"):
        flags.append("eSex")
    format_type = audnex.get("formatType", "").lower()
    if format_type == "abridged":
        flags.append("abridged")
    if flags:
        mam_json["flags"] = flags

    # Main category (Fiction=1, Non-Fiction=2)
    lit_type = audnex.get("literatureType", "").lower()
    if lit_type == "fiction":
        mam_json["main_cat"] = 1
    elif lit_type == "non-fiction" or lit_type == "nonfiction":
        mam_json["main_cat"] = 2

    return mam_json


def save_mam_json(
    mam_data: dict[str, Any],
    output_path: Path,
) -> None:
    """
    Write MAM JSON to file.

    Args:
        mam_data: MAM JSON dict
        output_path: Where to write the JSON file
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mam_data, f, indent=2, ensure_ascii=False)

    logger.info(f"Saved MAM JSON: {output_path}")


def generate_mam_json_for_release(
    release: AudiobookRelease,
    output_dir: Path | None = None,
) -> Path | None:
    """
    Generate MAM JSON file for a release.

    Uses release.audnex_metadata and release.mediainfo_data if available,
    or fetches them if not.

    Args:
        release: AudiobookRelease with metadata populated
        output_dir: Directory to write JSON (defaults to torrent_output from config)

    Returns:
        Path to generated JSON file, or None on failure
    """
    settings = get_settings()

    # Determine output directory
    if output_dir is None:
        output_dir = settings.paths.torrent_output

    # Build filename: same as torrent but .json extension
    # Format: "Author - Title.json"
    if release.staging_dir:
        json_name = f"{release.staging_dir.name}.json"
    else:
        json_name = f"{release.display_name}.json"

    output_path = Path(output_dir) / json_name

    # Build and save
    mam_data = build_mam_json(release)

    if not mam_data.get("title"):
        logger.warning(f"No title for MAM JSON: {release.display_name}")
        return None

    save_mam_json(mam_data, output_path)
    return output_path
