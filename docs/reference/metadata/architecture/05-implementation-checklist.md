# Implementation Checklist

> Part of [Metadata Architecture Documentation](README.md)

---

## Phase 0: Package Scaffolding (Do First!)

> **Critical:** Python won't allow both `metadata.py` and `metadata/` to coexist.

- [ ] Create `src/shelfr/metadata/` directory
- [ ] Move `metadata.py` → `metadata/__init__.py` (contents unchanged)
- [ ] Verify `import shelfr.metadata` still works
- [ ] Run full test suite

**Why separate phase?** This is pure scaffolding — no behavior change, no refactoring, just enabling the package structure. Ship this first before any extraction.

> **Note:** After Phase 0, there is no `metadata.py` — the facade becomes `metadata/__init__.py`.

---

## Phase 1: Extract MediaInfo (Leaf Module)

> MediaInfo is the cleanest extraction: no network, no state, pure functions.

- [ ] Create `metadata/types.py` with shared `Chapter` dataclass
- [ ] Create `metadata/mediainfo/extractor.py` with:
  - `AudioFormat` dataclass (MediaInfo-specific, stays here)
  - `detect_audio_format()`, `detect_audio_format_from_file()`
  - `run_mediainfo()`, `save_mediainfo_json()`
  - `_parse_chapters_from_mediainfo()`, `_extract_audio_info()`
- [ ] Update `metadata/__init__.py` to re-export from new location
- [ ] Run tests

---

## Phase 2: Extract Formatting (Presentation Layer)

- [ ] Create `metadata/formatting/bbcode.py`:
  - `render_bbcode_description()`, `_convert_newlines_for_mam()`
  - `_format_release_date()`, `_format_duration()`, `_format_chapter_time()`
  - Import `Chapter` from `metadata/types.py` (not mediainfo)
- [ ] Create `metadata/formatting/html.py`:
  - `_html_to_bbcode()`, `_clean_html()`
- [ ] Update re-exports

---

## Phase 3: Extract Audnex Client (Network Boundary)

- [ ] Create `metadata/audnex/client.py` with:
  - `fetch_audnex_book()`, `fetch_audnex_author()`
  - `fetch_audnex_chapters()`, `_parse_chapters_from_audnex()`
  - `save_audnex_json()`
  - All `_fetch_audnex_*_region()` helpers
- [ ] Keep chapters with client (shared HTTP/retry/circuit-breaker patterns)
- [ ] Update re-exports

---

## Phase 4: Extract MAM (Depends on Above)

> Do this later — `build_mam_json` touches everything (mediainfo, audnex, formatting).

- [ ] Create `metadata/mam/categories.py`:
  - `FICTION_GENRE_KEYWORDS`, `NONFICTION_GENRE_KEYWORDS`
  - `_infer_fiction_or_nonfiction()`, `_get_audiobook_category()`, `_map_genres_to_categories()`
- [ ] Create `metadata/mam/json_builder.py`:
  - `build_mam_json()`, `save_mam_json()`, `generate_mam_json_for_release()`
  - `_build_series_list()`, `_get_mediainfo_string()`

---

## Phase 5: Schemas + Cleaning + JSON Sidecar

- [ ] Create `metadata/schemas/canonical.py`:
  - `Person`, `Series`, `Genre`, `CanonicalMetadata` (ALL in one file)
  - **Do NOT split into person.py/series.py/genre.py yet** (avoid circular import risk)
- [ ] Create `metadata/cleaning.py` as **facade over existing functions**:
  - Re-export from `shelfr.utils.naming`: `filter_title`, `filter_subtitle`, etc.
  - **Don't duplicate** — wrap existing functions
- [ ] Create `metadata/orchestration.py` (renamed from pipeline.py):
  - `fetch_metadata()`, `fetch_all_metadata()`, `save_metadata_files()`
- [ ] Create `metadata/json/generator.py` (JSON sidecar feature)
- [ ] Define `MetadataProvider` protocol in `metadata/providers/base.py`
- [ ] Define `MetadataExporter` protocol in `metadata/exporters/base.py`

---

## Phase 6: Move OPF + Deprecations

- [ ] Move `src/shelfr/opf/` → `metadata/opf/`
- [ ] Create deprecation shim at old location (env-var gated)
- [ ] Create JSON exporter → `metadata/exporters/json.py`

---

## Phase 7: Infrastructure (As Needed)

- [ ] Implement `MetadataCache` with `FileCache` default
- [ ] Implement `MetadataEvents` hook system
- [ ] Add schema versioning to `CanonicalMetadata`
- [ ] Per-provider rate limiting
- [ ] Circuit breaker integration
- [ ] Implement `MetadataAggregator` with deterministic precedence

---

## Future (As Needed)

- [ ] Hardcover provider
- [ ] Goodreads provider
- [ ] NFO exporter
- [ ] Batch operations
- [ ] Custom user fields

---

## Progress Tracking

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 0 | ⏳ Not Started | Package scaffolding |
| Phase 1 | ⏳ Not Started | MediaInfo (leaf module) |
| Phase 2 | ⏳ Not Started | Formatting (presentation) |
| Phase 3 | ⏳ Not Started | Audnex client |
| Phase 4 | ⏳ Not Started | MAM (depends on above) |
| Phase 5 | ⏳ Not Started | Schemas + Cleaning + JSON |
| Phase 6 | ⏳ Not Started | OPF move + deprecations |
| Phase 7 | ⏳ Not Started | Infrastructure |
| Future | ⏳ Not Started | As needed |

---

## Dependencies

```bash
Phase 0 (Scaffolding) ← MUST BE FIRST
    │
    ▼
Phase 1 (MediaInfo) ──→ Phase 2 (Formatting) ──→ Phase 3 (Audnex)
    │                                                   │
    │                                                   ▼
    │                                            Phase 4 (MAM)
    │                                                   │
    ▼                                                   ▼
Phase 5 (Schemas/Cleaning/JSON) ←───────────────────────┘
    │
    ▼
Phase 6 (OPF + Deprecations)
    │
    ▼
Phase 7 (Infrastructure)
```

**Critical Path for JSON sidecar:** Phase 0 → Phase 1 → Phase 5 (schemas) → Phase 6 (JSON exporter)

---

## Testing Strategy

### Per-Phase Testing

| Phase | Test Focus |
|-------|------------|
| Phase 0 | Import smoke test, full test suite passes |
| Phase 1 | MediaInfo parsing, AudioFormat detection |
| Phase 2 | BBCode output, HTML conversion |
| Phase 3 | Mock HTTP responses, circuit breaker |
| Phase 4 | Category mapping, MAM JSON golden tests |
| Phase 5 | Schema validation, cleaning idempotence |
| Phase 6 | OPF output, JSON sidecar golden tests |
| Phase 7 | Cache hit/miss, event emission |

### Integration Tests

- [ ] Full pipeline: Provider → CanonicalMetadata → Exporter
- [ ] Fallback chain: Primary fails → Secondary succeeds
- [ ] Cache integration: Cached vs fresh data
- [ ] Error handling: All providers fail gracefully
