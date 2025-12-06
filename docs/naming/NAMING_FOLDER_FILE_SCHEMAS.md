# Folder & File Naming Schemas

> Output formats, truncation rules, and MAM JSON schema for MAMFast naming.

## Related Documentation

| Document | Description |
|----------|-------------|
| [Naming Overview](./NAMING.md) | Quick reference and architecture |
| [Processing Pipeline](./NAMING_PIPELINE.md) | Full cleaning pipeline |
| [Rules Reference](./NAMING_RULES.md) | Matching rules and phrase removal |

---

## Cleaning & Filtering

> **Important:** The same cleaning/filtering rules apply to **all outputs**: folder names, file names, MAM JSON fields, AND the BBCode description.

### What Gets Cleaned

| Field | Cleaning Applied |
|-------|------------------|
| **Title** | `filter_title()` - removes "(Unabridged)", "A Novel", "Light Novel", format indicators, genre tags |
| **Authors** | `filter_authors()` - removes translators, illustrators, editors; `transliterate_text()` for Japanese names |
| **Narrators** | `transliterate_text()` for Japanese/foreign names |
| **Series** | `filter_series()` - removes format indicators, series suffixes |
| **Subtitle** | `filter_subtitle()` - removes text redundant with title/series (e.g., "Light Novel") |
| **Description Title** | Same as Title - the header in BBCode description is also filtered |

### Example

**Raw Audnex Data:**
```
title: "I'm the Evil Lord of an Intergalactic Empire!, Vol. 5"
subtitle: "Light Novel"
authors: ["Yomu Mishima"]
```

**After Cleaning (folder, JSON, AND description):**
```
title: "I'm the Evil Lord of an Intergalactic Empire!, Vol. 5"
subtitle: (filtered out - redundant)
description header: "I'm the Evil Lord of an Intergalactic Empire!, Vol. 5"
```

See [Rules Reference](./NAMING_RULES.md) for the full list of phrase removal patterns.

---

## Folder Naming Schema

### Standard Format

```
{author} - {series vol_XX - }{title} ({year}) ({narrator}) {ASIN.xxxxxxxxxx}
```

### Components

| Component | Required | Format | Example |
|-----------|----------|--------|---------|
| `author` | Yes | First author, cleaned (see above) | `Andy Weir` |
| `series` | No | Series name + vol_XX | `Stormlight Archive vol_01` |
| `title` | Yes | Cleaned title (see above) | `The Way of Kings` |
| `year` | Yes | 4-digit year in parens | `(2010)` |
| `narrator` | Yes | First narrator in parens | `(Michael Kramer)` |
| `ASIN` | Yes | ASIN tag in braces | `{ASIN.B003ZWFO7E}` |

### Examples

**Standalone Book:**
```
Andy Weir - Project Hail Mary (2021) (Ray Porter) {ASIN.B08G9PRS1K}
```

**Series Book:**
```
Brandon Sanderson - Stormlight Archive vol_01 - The Way of Kings (2010) (Michael Kramer) {ASIN.B003ZWFO7E}
```

**Multi-Author:**
```
Douglas Preston - Relic (1995) (David Colacci) {ASIN.B002V1BRDI}
```
Note: Only first author used; second author (Lincoln Child) omitted.

**Decimal Volume:**
```
John Scalzi - Old Mans War vol_01.5 - Questions for a Soldier (2008) (William Dufris) {ASIN.B001D2XXXX}
```

---

## File Naming Schema

### Standard Format

```
{author} - {series vol_XX - }{title}.m4b
```

### Components

| Component | Required | Format | Example |
|-----------|----------|--------|---------|
| `author` | Yes | First author, cleaned | `Andy Weir` |
| `series` | No | Series name + vol_XX | `Stormlight Archive vol_01` |
| `title` | Yes | Cleaned title | `The Way of Kings` |
| `extension` | Yes | Audio format | `.m4b` |

### Examples

**Standalone Book:**
```
Andy Weir - Project Hail Mary.m4b
```

**Series Book:**
```
Brandon Sanderson - Stormlight Archive vol_01 - The Way of Kings.m4b
```

---

## Character Limits and Truncation

### MAM Path Limit: 225 Characters

MAM enforces a 225-character limit on the full path (folder + file).

### Truncation Strategy

When the combined path exceeds 225 characters:

1. **Priority Preservation** (never truncated):
   - Author name
   - ASIN tag
   - Series prefix (if present)
   - Year
   - File extension

2. **Truncation Target**: Title is truncated first

3. **Hash Suffix**: 6-character hash added for uniqueness

### Truncation Format

```
{truncated_title}...[{hash}]
```

### Example

**Original (280 chars):**
```
Folder: Some Author - A Very Long Series Name vol_01 - An Extremely Long Title That Contains Many Words And Just Keeps Going (2021) (Narrator) {ASIN.B0123456789}
File: Some Author - A Very Long Series Name vol_01 - An Extremely Long Title That Contains Many Words And Just Keeps Going.m4b
```

**Truncated (under 225 chars):**
```
Folder: Some Author - A Very Long Series Name vol_01 - An Extremely Long Title...[a1b2c3] (2021) (Narrator) {ASIN.B0123456789}
File: Some Author - A Very Long Series Name vol_01 - An Extremely Long Title...[a1b2c3].m4b
```

### MamPath Model

```python
class MamPath(BaseModel):
    """Tracks path with truncation metadata."""

    folder_name: str
    file_name: str
    was_truncated: bool = False
    original_length: int = 0
    truncation_hash: str | None = None

    @property
    def full_path(self) -> str:
        """Full path for limit checking."""
        return f"{self.folder_name}/{self.file_name}"

    @property
    def path_length(self) -> int:
        """Total path length."""
        return len(self.full_path)
```

---

## MAM JSON Schema (Fast Fillout)

MAM accepts a JSON object for fast form filling on upload/request pages. This is the official schema from the [MAM API Wiki](https://www.myanonamouse.net/).

> **Note:** Leave off any fields you don't need/want to fill out.

### Field Reference

| Field | Type | Description |
|-------|------|-------------|
| `title` | string | Title of the item |
| `subtitle` | string | Subtitle of the book |
| `authors` | list of strings | Author names |
| `narrators` | list of strings | Narrator names |
| `series` | list of objects | Series info (see below) |
| `description` | string | Book description (supports BBCode) |
| `thumbnail` | string | URL for poster image |
| `language` | string or int | Language name or ID |
| `category` | string or int | Category name or ID (single) |
| `categories` | list of ints | Category IDs (multi-category) |
| `main_cat` | int | 1 = Fiction, 2 = Non-Fiction |
| `mediaType` | int | Media type ID (1 = Audiobook) |
| `mediaInfo` | string | MediaInfo output for audio |
| `tags` | string | Tags/labels string |
| `isbn` | string | ISBN field (MAMFast uses `ASIN:<asin>`) |
| `flags` | list of strings | Content flags (see below) |

### Series Object

```json
{
  "name": "Series Name",
  "number": "1"  // Can be int, string, or range like "1-3"
}
```

### Flags

| Flag | Meaning |
|------|---------|
| `cLang` | Crude Language |
| `vio` | Violence |
| `sSex` | Some Explicit Sexual Content |
| `eSex` | Explicit Sexual Content |
| `abridged` | Abridged content |
| `lgbt` | LGBTQ+ themed content |

### MAMFast Output Example

```json
{
  "title": "The Way of Kings",
  "subtitle": "A Stormlight Archive Novel",
  "authors": ["Brandon Sanderson"],
  "narrators": ["Michael Kramer", "Kate Reading"],
  "series": [
    {
      "name": "The Stormlight Archive",
      "number": "1"
    }
  ],
  "description": "[center][size=6][b][color=#3aa6ff]The Way of Kings[/color]...",
  "thumbnail": "https://m.media-amazon.com/images/I/...",
  "language": "English",
  "categories": [44],
  "mediaType": 1,
  "tags": "Length: 45h 29m | Release date: 08-31-10 | Format: M4B, AAC LC | Chapterized |",
  "mediaInfo": "General\\nComplete name: ...",
  "isbn": "ASIN:B003ZWFO7E",
  "flags": []
}
```

### Category Mapping

MAM uses numeric category IDs. See the full list at:
- https://www.myanonamouse.net/tor/json/categories.php?new

Common audiobook categories in `config/audiobook_categories.json`:

| Genre | Category ID |
|-------|-------------|
| Science Fiction | 39 |
| Fantasy | 44 |
| Mystery | 50 |
| Romance | 54 |
| Thriller | 60 |
| Horror | 47 |
| Non-Fiction | 69 |
| Biography | 70 |
| History | 72 |

---

## pathvalidate Integration

All filenames go through `pathvalidate` for cross-platform safety:

### Sanitization Rules

1. **Forbidden Characters**: `< > : " / \ | ? *` removed
2. **Reserved Names**: `CON`, `PRN`, `NUL`, etc. (Windows)
3. **Trailing Dots/Spaces**: Stripped
4. **Length Limits**: Enforced per-platform

### Usage

```python
from pathvalidate import sanitize_filename

def safe_filename(name: str) -> str:
    """Create cross-platform safe filename."""
    return sanitize_filename(
        name,
        platform="universal",
        replacement_text="_"
    )
```

---

## Special Cases

### Multi-Narrator Handling

```python
# Input
narrators = ["Michael Kramer", "Kate Reading"]

# Folder (first narrator only)
"...(Michael Kramer)..."

# MAM JSON (all narrators)
"narrator": "Michael Kramer, Kate Reading"
```

### Unknown Year

```python
# When year is None or unknown
"Author - Title (Unknown) (Narrator) {ASIN.xxx}"
```

### No Series

Series component is omitted entirely:

```python
# With series
"Author - Series vol_01 - Title (Year) (Narrator) {ASIN.xxx}"

# Without series
"Author - Title (Year) (Narrator) {ASIN.xxx}"
```

### Non-Standard Volumes

```python
# Prequel
"Author - Series vol_00 - Title..."

# Decimal (novella)
"Author - Series vol_01.5 - Title..."

# Named position (converted)
"Prequel" → "vol_00"
"Prologue" → "vol_00"
```

---

## Series Resolution Strategy

Series info is resolved from multiple sources to handle incomplete metadata gracefully.

### Resolution Order

| Priority | Source | Description | Confidence |
|----------|--------|-------------|------------|
| 1 | **Audnex** | `seriesPrimary` from API (authoritative) | 1.0 |
| 2 | **Libation Path** | Parse from folder structure | 0.9 |
| 3 | **Title Heuristic** | Regex extract from title | 0.5 |

If no source provides reliable series data, the book is treated as **standalone** and marked for future backfill.

### When All Sources Miss

New audiobook releases (especially from publishers like Seven Seas Siren) may have incomplete metadata in Audnex for the first 1-2 weeks. When this happens:

1. **Standalone treatment:** Book is processed without series info
2. **Automatic backfill:** When Audnex later adds series metadata, `mamfast series-refresh` can update the internal cache and regenerate MAM JSON
3. **No torrent changes:** Live torrents and seeding files are not affected by metadata updates

**Example - New Release Without Series:**
```
/audiobook-import/Yomu Mishima/Im the Evil Lord of an Intergalactic Empire Vol. 5 (2025) (Yomu Mishima) {ASIN.B0G59SMBCH} [H2OKing]/
```

Note: No series folder or `vol_XX` suffix. This is expected for brand-new releases.

**Example - After Audnex Updates:**
```
/audiobook-import/Yomu Mishima/Im the Evil Lord.../Im the Evil Lord... vol_05 (2025) ...
```

The series info appears once Audnex aggregation catches up (typically 1-2 weeks).

---

## SeriesInfo Model

> **Status:** Planned implementation. See [GitHub Issue #23](https://github.com/H2OKing89/mam_tool/issues/23) for tracking.

```python
from dataclasses import dataclass
from typing import Literal

@dataclass
class SeriesInfo:
    """Resolved series information from multiple sources."""
    name: str              # "I'm the Evil Lord of an Intergalactic Empire!"
    number: str | None     # "5", "01.5", "0" for prequel
    source: Literal["audnex", "libation", "title_heuristic"]
    confidence: float = 1.0  # 1.0 = authoritative, 0.5 = heuristic
```

### Resolution Function

```python
def resolve_series(
    audnex_data: dict | None,
    libation_path: Path | None,
    title: str,
) -> SeriesInfo | None:
    """Resolve series from multiple sources."""

    # 1. Audnex (authoritative when present)
    if audnex_data and audnex_data.get("seriesPrimary"):
        sp = audnex_data["seriesPrimary"]
        return SeriesInfo(
            name=filter_series(sp["name"]),
            number=str(sp.get("position", "")),
            source="audnex",
            confidence=1.0,
        )

    # 2. Libation folder structure
    if libation_path:
        series = parse_series_from_libation_path(libation_path)
        if series:
            return series

    # 3. Title heuristics (last resort)
    return parse_series_from_title(title)
```

### Title Heuristic Patterns

Extract series from titles like:
- `"I'm the Evil Lord of an Intergalactic Empire!, Vol. 5"` → series: base, number: 5
- `"Black Summoner, Vol. 4"` → series: "Black Summoner", number: 4
- `"Some Light Novel: Volume 3.5"` → series: "Some Light Novel", number: 3.5

```python
VOL_PATTERN = re.compile(
    r"^(?P<base>.+?)[,:]?\s+(?:Vol(?:ume)?|Book)\s+(?P<num>\d+(?:\.\d+)?)$",
    re.IGNORECASE,
)
```

### Benefits

1. **New releases get series info** from Libation's embedded metadata or title parsing
2. **Consistent naming** even before Audnex catches up
3. **MAM JSON has series data** for proper categorization
4. **No manual intervention** required for most cases

---

## Libation Integration

### Recommended Templates

MAMFast expects specific folder/file naming from Libation. Use these templates in Libation settings:

**Folder Template:**
```
<first author>/<if series><series>/<end if><audible title><if series> vol_<series#[00.##]><end if> (<year>) (<first author>) {ASIN.<id>} [YourTag]
```

**File Template:**
```
<audible title><if series> vol_<series#[00.##]><end if> (<year>) (<first author>) {ASIN.<id>}
```

### Template Breakdown

| Token | Description | Example Output |
|-------|-------------|----------------|
| `<first author>` | First author name | `Brandon Sanderson` |
| `<audible title>` | Book title from Audible | `The Way of Kings` |
| `<series>` | Series name | `The Stormlight Archive` |
| `<series#[00.##]>` | Volume number (zero-padded) | `01`, `01.5`, `12` |
| `<year>` | Release year | `2010` |
| `<id>` | ASIN | `B003ZWFO7E` |
| `<if series>...<end if>` | Conditional - only if series exists | |

### Example Outputs

**With Series:**
```
Folder: Brandon Sanderson/The Stormlight Archive/The Way of Kings vol_01 (2010) (Brandon Sanderson) {ASIN.B003ZWFO7E} [H2OKing]
File:   The Way of Kings vol_01 (2010) (Brandon Sanderson) {ASIN.B003ZWFO7E}.m4b
```

**Without Series:**
```
Folder: Andy Weir/Project Hail Mary (2021) (Andy Weir) {ASIN.B08G9PRS1K} [H2OKing]
File:   Project Hail Mary (2021) (Andy Weir) {ASIN.B08G9PRS1K}.m4b
```

### Why This Matters

Libation uses **embedded metadata** from the audio file, which may have series info even when Audnex doesn't. This provides a fallback when the API is incomplete.

---

## Validation

### Path Length Validation

```python
def validate_mam_path(path: MamPath) -> list[str]:
    """Validate path meets MAM requirements."""
    errors = []

    if path.path_length > 225:
        errors.append(f"Path too long: {path.path_length} > 225")

    if not path.folder_name:
        errors.append("Folder name is empty")

    if not path.file_name.endswith(".m4b"):
        errors.append("File must have .m4b extension")

    return errors
```

### ASIN Validation

```python
import re

ASIN_PATTERN = re.compile(r"^B[A-Z0-9]{9}$")

def validate_asin(asin: str) -> bool:
    """Validate ASIN format."""
    return bool(ASIN_PATTERN.match(asin))
```

---

## See Also

- [Processing Pipeline](NAMING_PIPELINE.md) - How names are built
- [Rules Reference](NAMING_RULES.md) - Cleaning rules
- [config/audiobook_categories.json](/config/audiobook_categories.json) - Category mappings
