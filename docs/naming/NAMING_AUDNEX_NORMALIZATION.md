# Audnex Normalization Layer

> How MAMFast normalizes Audible metadata using the Audnex API.

## Related Documentation

| Document | Description |
|----------|-------------|
| [Naming Overview](./NAMING.md) | Quick reference and architecture |
| [Processing Pipeline](./NAMING_PIPELINE.md) | Full cleaning pipeline |
| [Folder & File Schemas](./NAMING_FOLDER_FILE_SCHEMAS.md) | Output formats |

---

## The Problem: Audible's Inconsistent Metadata

Audible stores metadata inconsistently, particularly for series books:

### Pattern 1: Series in Title
```json
{
  "title": "The Way of Kings",
  "subtitle": "The Stormlight Archive, Book 1",
  "seriesPrimary": null
}
```
The series info is in `subtitle`, not `seriesPrimary`.

### Pattern 2: Swapped Title/Subtitle
```json
{
  "title": "The Stormlight Archive, Book 1",
  "subtitle": "The Way of Kings",
  "seriesPrimary": {
    "name": "The Stormlight Archive",
    "position": "1"
  }
}
```
The actual book title is in `subtitle`, series info is in `title`.

### Pattern 3: Correct Format
```json
{
  "title": "The Way of Kings",
  "subtitle": "A Stormlight Archive Novel",
  "seriesPrimary": {
    "name": "The Stormlight Archive",
    "position": "1"
  }
}
```
This is the correct format, but rare.

---

## The Solution: NormalizedBook

The `NormalizedBook` Pydantic model in `models.py` provides corrected metadata:

```python
class NormalizedBook(BaseModel):
    """Normalized book metadata from Audnex API."""

    title: str           # Always the actual book title
    subtitle: str | None # Always the subtitle (if any)
    series_name: str | None
    series_position: str | None

    @classmethod
    def from_audnex(cls, audnex_data: dict) -> "NormalizedBook":
        """Build from Audnex API response with normalization."""
        ...
```

### Normalization Rules

1. **If `seriesPrimary` exists:**
   - Check if `title` contains series pattern (e.g., "Series Name, Book N")
   - If yes: swap `title` and `subtitle`
   - Extract series from `seriesPrimary`

2. **If `seriesPrimary` is null:**
   - Check `subtitle` for series pattern
   - If found: extract series info from subtitle
   - Keep `title` as-is

3. **Series Position Normalization:**
   - "1" → "01" (zero-pad single digits)
   - "1.5" → "01.5" (preserve decimals)
   - "Book 1" → "01" (extract number)

---

## Detection Logic

### Series Pattern Detection

```python
SERIES_PATTERN = re.compile(
    r"^(?P<series>.+?),?\s*(?:Book|Volume|Vol\.?|Part|#)\s*(?P<position>[\d.]+)$",
    re.IGNORECASE
)
```

Matches:
- "The Stormlight Archive, Book 1"
- "Mistborn Volume 2"
- "Red Rising #3"
- "The Expanse, Part 1.5"

### Title/Subtitle Swap Detection

```python
def _needs_swap(title: str, subtitle: str | None, series_primary: dict | None) -> bool:
    """Detect if title and subtitle are swapped."""
    if not series_primary or not subtitle:
        return False

    # Check if title matches series pattern
    series_match = SERIES_PATTERN.match(title)
    if not series_match:
        return False

    # Check if extracted series matches seriesPrimary
    extracted_series = series_match.group("series")
    primary_series = series_primary.get("name", "")

    return _fuzzy_match(extracted_series, primary_series)
```

---

## Examples

### Example 1: Swap Required

**Input (Audnex Response):**
```json
{
  "title": "The Stormlight Archive, Book 1",
  "subtitle": "The Way of Kings",
  "seriesPrimary": {
    "name": "The Stormlight Archive",
    "position": "1"
  }
}
```

**Output (NormalizedBook):**
```python
NormalizedBook(
    title="The Way of Kings",
    subtitle=None,  # Original subtitle was the real title
    series_name="The Stormlight Archive",
    series_position="01"
)
```

### Example 2: No Swap Needed

**Input:**
```json
{
  "title": "Project Hail Mary",
  "subtitle": "A Novel",
  "seriesPrimary": null
}
```

**Output:**
```python
NormalizedBook(
    title="Project Hail Mary",
    subtitle="A Novel",
    series_name=None,
    series_position=None
)
```

### Example 3: Series in Subtitle

**Input:**
```json
{
  "title": "The Final Empire",
  "subtitle": "Mistborn, Book 1",
  "seriesPrimary": null
}
```

**Output:**
```python
NormalizedBook(
    title="The Final Empire",
    subtitle=None,  # Series info extracted
    series_name="Mistborn",
    series_position="01"
)
```

---

## Implementation Notes

### Fuzzy Matching

Series name matching uses fuzzy comparison to handle variations:
- "The Stormlight Archive" ≈ "Stormlight Archive"
- "A Song of Ice and Fire" ≈ "Song of Ice & Fire"

```python
from mamfast.utils.fuzzy import fuzzy_match

# 80% similarity threshold
if fuzzy_match(extracted, expected, threshold=0.8):
    # Names are considered matching
```

### Edge Cases

1. **Decimal positions:** "1.5" preserved as "01.5"
2. **Multi-word positions:** "Prequel" → kept as-is
3. **Roman numerals:** "Book II" → "02"
4. **Missing position:** Series name without number → position = None

---

## Testing

### Unit Tests

```python
# tests/test_normalization.py

def test_swap_detection():
    """Title/subtitle swap is detected correctly."""
    data = {
        "title": "Series, Book 1",
        "subtitle": "Actual Title",
        "seriesPrimary": {"name": "Series", "position": "1"}
    }
    book = NormalizedBook.from_audnex(data)
    assert book.title == "Actual Title"
    assert book.series_name == "Series"

def test_no_swap_when_correct():
    """Correct format is not modified."""
    data = {
        "title": "Actual Title",
        "subtitle": "A Subtitle",
        "seriesPrimary": {"name": "Series", "position": "1"}
    }
    book = NormalizedBook.from_audnex(data)
    assert book.title == "Actual Title"
```

### Golden Tests

See `tests/fixtures/audnex_normalization_samples.json` for comprehensive test cases.

---

## See Also

- [schemas/audnex.py](/src/mamfast/schemas/audnex.py) - Audnex response validation
- [models.py](/src/mamfast/models.py) - NormalizedBook implementation
- [test_normalization.py](/tests/test_normalization.py) - Normalization tests
