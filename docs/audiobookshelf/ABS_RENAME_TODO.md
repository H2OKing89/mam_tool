# abs-rename Implementation TODO

> Work breakdown for implementing `mamfast abs-rename` command.
> Based on design doc: [ABS_RENAME_TOOL.md](./ABS_RENAME_TOOL.md)

---

## Summary of Staged Changes

This branch (`feature/abs-rename-design`) includes:

| File | Type | Description |
|------|------|-------------|
| `docs/audiobookshelf/ABS_RENAME_TOOL.md` | NEW | Full design doc (~1850 lines) |
| `docs/naming/NAMING_FOLDER_FILE_SCHEMAS.md` | MOD | Added Volume Notation section |
| `docs/naming/NAMING_RULES.md` | MOD | Updated `normalize_position()` for parts/ranges |
| `scripts/scan_abs_library.py` | NEW | Library scanner with mediainfo extraction |

---

## Implementation Priority

### Phase 1: Core Infrastructure (Must Have)

- [ ] **1.1 Create `src/mamfast/abs/rename.py`**
  - [ ] `AbsMetadataSchema` - Pydantic model for ABS metadata.json
  - [ ] `AbsMetadata` - Dataclass for parsed metadata
  - [ ] `parse_abs_metadata()` - Parse & validate ABS sidecar
  - [ ] `RenameCandidate` - Pipeline state dataclass
  - [ ] `RenameResult` - Operation result dataclass
  - [ ] `RenameStatus` - Literal type for statuses

- [ ] **1.2 Discovery (Stage 1)**
  - [ ] `has_audio_files()` - Check folder contains audio
  - [ ] `discover_rename_candidates()` - Find leaf folders only

- [ ] **1.3 ASIN Resolution (Stage 2.5 + 3)**
  - [ ] `enrich_candidate_from_abs_metadata()` - Parse ABS metadata.json first
  - [ ] `resolve_asin()` - Full cascade (reuse `abs/asin.py` functions)

### Phase 2: Name Building (Must Have)

- [ ] **2.1 Parse Existing Names (Stage 2)**
  - [ ] Reuse `parse_mam_folder_name()` from `abs/importer.py`
  - [ ] `detect_edition_flags()` - Extract Full-Cast, Dolby Atmos, etc.

- [ ] **2.2 Duplicate Detection (Stage 4)**
  - [ ] `detect_duplicates()` - Group by ASIN, mark conflicts
  - [ ] `detect_similar_titles()` - Use rapidfuzz for fuzzy matching

- [ ] **2.3 Target Name Building (Stage 5)**
  - [ ] `compute_target_name()` - Use `build_mam_folder_name()`
  - [ ] Apply `safe_dirname()` for pathvalidate safety

### Phase 3: Execution (Must Have)

- [ ] **3.1 Rename Execution (Stage 6)**
  - [ ] `rename_folder()` - Execute single rename
  - [ ] Handle `target_exists` conflict
  - [ ] Dry-run support

- [ ] **3.2 CLI Command**
  - [ ] Add `abs-rename` subparser to `cli.py`
  - [ ] Options: `--source`, `--pattern`, `--fetch-metadata`, `--abs-search`
  - [ ] Use global `--dry-run` flag
  - [ ] Rich output with `print_step()`, `print_success()`

### Phase 4: Polish (Nice to Have)

- [ ] **4.1 Interactive Mode**
  - [ ] `--interactive` flag for per-folder confirmation
  - [ ] Use `confirm()` from console.py

- [ ] **4.2 Report Output**
  - [ ] `--report PATH` to output JSON report
  - [ ] Include before/after names, status, ASIN source

- [ ] **4.3 File Renaming**
  - [ ] Optionally rename files inside folder to match folder name
  - [ ] Preserve file extensions

---

## Code Changes Required

### New Files

| File | Purpose | Est. Lines |
|------|---------|------------|
| `src/mamfast/abs/rename.py` | Core rename logic | ~400 |
| `src/mamfast/schemas/abs_metadata.py` | Pydantic schema for ABS metadata.json | ~50 |
| `tests/test_abs_rename.py` | Unit tests | ~300 |

### Modified Files

| File | Changes |
|------|---------|
| `src/mamfast/cli.py` | Add `abs-rename` subcommand (~100 lines) |
| `src/mamfast/abs/__init__.py` | Export rename functions |
| `src/mamfast/utils/naming.py` | May need `normalize_position()` update for parts/ranges |

---

## Naming Doc Updates Needed

The staged changes to naming docs document the **spec**, but code implementation is still needed:

### `NAMING_FOLDER_FILE_SCHEMAS.md` Changes
- ✅ Added Volume Notation section with regex pattern
- ✅ Documented `vol_NNpN` for parts, `vol_NN-NN` for ranges
- ⚠️ **TODO**: Implement regex in `utils/naming.py`

### `NAMING_RULES.md` Changes
- ✅ Updated `normalize_position()` pseudocode for parts/ranges
- ✅ Added examples table with parts and ranges
- ⚠️ **TODO**: Implement actual code changes in `utils/naming.py`

### Implementation Tasks for Naming

- [ ] **Update `extract_volume_number()` in `utils/naming.py`**
  - Handle `1p1` → `vol_01p1` (part notation)
  - Handle `1-3` → `vol_01-03` (range notation)
  - Keep `1.5` → `vol_01.5` (novella notation)

- [ ] **Update `format_volume_number()` in `utils/naming.py`**
  - Support `VolumeInfo` TypedDict with `base`, `range_end`, `part` fields
  - Format consistently for all notation types

- [ ] **Add golden tests for volume notation**
  - `tests/golden/naming_inputs.json` - Add part/range examples
  - `tests/golden/naming_expected.json` - Expected outputs

---

## Testing Checklist

### Unit Tests (`test_abs_rename.py`)

- [ ] `test_parse_abs_metadata_valid` - Parse sample metadata.json
- [ ] `test_parse_abs_metadata_missing` - Handle missing file
- [ ] `test_parse_abs_metadata_malformed` - Handle bad JSON
- [ ] `test_discover_candidates_leaf_only` - Only leaf folders
- [ ] `test_detect_edition_flags` - Extract GA, Full-Cast, etc.
- [ ] `test_detect_duplicates_by_asin` - Mark duplicates
- [ ] `test_compute_target_name_series` - Series book naming
- [ ] `test_compute_target_name_standalone` - Standalone naming
- [ ] `test_rename_folder_dry_run` - Dry run doesn't rename
- [ ] `test_rename_folder_success` - Actual rename works

### Integration Tests

- [ ] `test_abs_rename_full_pipeline` - End-to-end with mock library
- [ ] `test_abs_rename_with_abs_search` - ABS search fallback

### Golden Tests for Volume Notation

- [ ] Add to `tests/fixtures/golden_samples_generated.json`:
  - Part examples: `vol_01p1`, `vol_01p2`
  - Range examples: `vol_01-03`, `vol_04-06`
  - Novella examples: `vol_01.5`, `vol_02.5`

---

## Dependencies

All packages already in codebase - no new deps needed:

| Package | Usage | Status |
|---------|-------|--------|
| `pydantic` | `AbsMetadataSchema` validation | ✅ Available |
| `pathvalidate` | `safe_dirname()` | ✅ Available |
| `rapidfuzz` | `similarity_ratio()`, `find_duplicates()` | ✅ Available |
| `rich` | CLI output | ✅ Available |

---

## Suggested Work Order

1. **Start with naming code** - Implement volume notation in `utils/naming.py`
2. **Create `abs/rename.py`** - Core module with dataclasses and discovery
3. **Add ASIN resolution** - Wire up ABS metadata.json + cascade
4. **Add target name building** - Use existing `build_mam_folder_name()`
5. **Add CLI command** - `abs-rename` with dry-run support
6. **Write tests** - Unit tests for each stage
7. **Polish** - Interactive mode, report output

---

## Open Questions

1. **Should we rename files inside folders too?**
   - Design doc says optional - implement in Phase 4?

2. **How to handle Unknown/ folder books?**
   - These have no ASIN - mark as `missing_asin` and skip?

3. **ABS metadata.json vs folder parse conflict?**
   - If both have different ASINs, which wins?
   - Proposal: ABS metadata.json wins (authoritative)

4. **Trigger ABS library scan after rename?**
   - Reuse `trigger_scan_safe()` from importer?

---

## Related Documentation

- [ABS_RENAME_TOOL.md](./ABS_RENAME_TOOL.md) - Full design doc
- [NAMING_FOLDER_FILE_SCHEMAS.md](../naming/NAMING_FOLDER_FILE_SCHEMAS.md) - Volume notation spec
- [NAMING_RULES.md](../naming/NAMING_RULES.md) - normalize_position() pseudocode
- [IMPROVEMENTS_PLAN.md](../IMPROVEMENTS_PLAN.md) - Enhanced packages reference
