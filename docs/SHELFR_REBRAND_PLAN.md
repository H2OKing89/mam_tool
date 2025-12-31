# Shelfr Rebrand Plan

**Date**: December 2025
**Status**: ✅ Phase 1 Complete
**Scope**: Rebrand `mamfast` → `shelfr` + future CLI restructure

---

## Executive Summary

The project has evolved from a simple MAM upload script (`mam_tool`) into a comprehensive audiobook management suite. The rebrand to **shelfr** reflects this growth and positions the tool for future expansion.

**Rebrand happens in two phases:**

1. **Phase 1: Simple Rebrand** — ✅ COMPLETE - Renamed `mamfast` → `shelfr`
2. **Phase 2: Suite Restructure** — Reorganize commands into domain-focused sub-apps (future)

---

## Phase 1: Simple Rebrand (✅ COMPLETE)

### What Changed

| Before | After |
|--------|-------|
| `mamfast` | `shelfr` |
| `src/mamfast/` | `src/shelfr/` |
| `from mamfast import ...` | `from shelfr import ...` |

### What Stayed the Same

- All command names and structure
- All functionality
- Config file format (`config/config.yaml`)
- State file format (`data/processed.json`)
- Config keys like `mamfast_managed` (backward compat)

### Rebrand Checklist

#### Repository

- [ ] Rename GitHub repo `mam_tool` → `shelfr` (manual step)
- [x] Update repo description in README
- [ ] Update topics/tags (after rename)

#### Package

- [x] Rename `src/mamfast/` → `src/shelfr/`
- [x] Update `pyproject.toml`:
  - [x] `name = "shelfr"`
  - [x] `[project.scripts]` entry point
  - [x] Update all internal references
- [x] Update all internal imports (`from mamfast.` → `from shelfr.`)
- [x] Update Jinja2 PackageLoader reference

#### CLI

- [x] Update CLI app name in `cli/_app.py`
- [x] Update help text and epilogs
- [x] Update version display
- [x] Add `mamfast` as deprecated alias (entry point in pyproject.toml)

#### Documentation

- [x] Update README.md
- [x] Update copilot-instructions.md
- [ ] Update all docs references
- [ ] Update example commands in other docs
- [ ] Update CHANGELOG.md

#### Tests

- [x] Update test imports
- [x] Update mock patch strings referencing "mamfast"
- [x] Verify all 2,124 tests pass

#### Config

- [x] Keep `config/config.yaml` format (no changes needed)
- [x] Keep backward compat config keys (`mamfast_managed`, etc.)
- [ ] Update example config comments if they mention "mamfast"

---

## Phase 2: Suite Restructure (In Progress)

After the rebrand stabilizes, reorganize commands into a domain-focused suite.

### Proposed Command Structure

```bash
shelfr
├── status              # Quick status overview (top-level convenience)
├── config              # Show loaded configuration
│
├── mam                 # 📤 MAM tracker workflows (✅ IMPLEMENTED)
│   ├── bbcode          # Output raw BBCode (copyable)
│   ├── render          # Preview BBCode visually
│   ├── run             # Full upload pipeline (future)
│   └── ff              # Generate MAM FastFill JSON (future)
│
├── lib                 # 📚 Libation integration
│   ├── scan            # Check Audible for new purchases
│   ├── liberate        # Download pending audiobooks
│   ├── status          # Show Libation library status
│   ├── books           # List books in library
│   ├── search          # Search library
│   ├── export          # Export library data
│   ├── settings        # Show Libation settings
│   ├── redownload      # Re-download specific books
│   ├── set-status      # Change book download status
│   ├── convert         # Convert audio formats
│   └── guide           # Libation setup guide
│
├── abs                 # 📚 Audiobookshelf management
│   ├── init            # Test ABS connection
│   ├── import          # Import staged books to library
│   ├── check-asin      # Check if ASIN exists in library
│   ├── trump-preview   # Preview trumping decisions
│   ├── restore         # Restore archived books
│   ├── cleanup         # Clean up source files after import
│   ├── rename          # Rename folders to MAM schema
│   ├── orphans         # Find orphaned folders
│   └── resolve-asins   # Resolve missing ASINs
│
├── mkbrr               # 🔧 Torrent tooling (mkbrr wrapper)
│   ├── create          # Create torrent file
│   └── verify          # Verify torrent (future)
│
├── meta                # 🏷️ Metadata operations (future)
│   ├── preview         # Preview naming transformations
│   ├── enrich          # Enrich metadata from Hardcover/Audnex
│   └── audit           # Audit metadata quality
│
├── doctor              # 🩺 Health & diagnostics
│   ├── check           # Run all health checks
│   ├── validate        # Validate discovered releases
│   ├── config          # Validate configuration files
│   ├── dupes           # Find duplicate releases
│   └── suspicious      # Check for naming issues
│
└── state               # 📋 State management
    ├── list            # List state entries
    ├── prune           # Remove stale entries
    ├── retry           # Retry failed entries
    ├── clear           # Clear specific entry
    └── export          # Export state to file
```

### Command Mapping (Current → Future)

| Current (`shelfr` after Phase 1) | Future (`shelfr` Phase 2) | Status |
|----------------------------------|---------------------------|--------|
| `shelfr run` | `shelfr mam run` | Planned |
| `shelfr status` | `shelfr status` | Implemented (stays top-level) |
| `shelfr config` | `shelfr config` | Implemented (stays top-level) |
| `shelfr tools mamff` | `shelfr mam ff` | Planned |
| `shelfr tools bbcode` | `shelfr mam bbcode` | ✅ Implemented |
| — | `shelfr mam render` | ✅ Implemented (NEW) |
| `shelfr libation *` | `shelfr lib *` | Implemented |
| `shelfr abs *` | `shelfr abs *` | Implemented (no change) |
| `shelfr check` | `shelfr doctor check` | Implemented |
| `shelfr validate` | `shelfr doctor validate` | Implemented |
| `shelfr validate-config` | `shelfr doctor config` | Implemented |
| `shelfr check-duplicates` | `shelfr doctor dupes` | Implemented |
| `shelfr check-suspicious` | `shelfr doctor suspicious` | Implemented |
| `shelfr preview-naming` | `shelfr meta preview` | Implemented |
| `shelfr state *` | `shelfr state *` | Implemented (no change) |
| — | `shelfr mkbrr create` | Future |
| — | `shelfr mkbrr verify` | Future |
| — | `shelfr meta enrich` | Future |
| — | `shelfr meta audit` | Future |

### Sub-App Descriptions

| Sub-App | Emoji | Help Text | Notes |
|---------|-------|-----------|-------|
| `mam` | 📤 | MAM tracker upload workflows | Core upload pipeline |
| `lib` | 📚 | Libation audiobook manager | Short for "libation" |
| `abs` | 📚 | Audiobookshelf library management | Keep existing |
| `mkbrr` | 🔧 | Torrent creation and verification | Full mkbrr wrapper |
| `meta` | 🏷️ | Metadata operations and enrichment | Future expansion |
| `doctor` | 🩺 | Health checks and diagnostics | Library health |
| `state` | 📋 | State and tracking management | Keep existing |

### Top-Level Convenience Commands

These stay at root level for quick access:

```bash
shelfr status    # Quick status overview
shelfr config    # Show configuration
```

### Backward Compatibility (Phase 2)

When restructuring, add hidden aliases with deprecation warnings:

```python
# Old command still works but warns
@app.command("check", hidden=True)
def check_deprecated(ctx: typer.Context) -> None:
    print_warning("'shelfr check' is now 'shelfr doctor check'. Please update your scripts.")
    return doctor_check(ctx)
```

---

## Implementation Timeline

### Phase 1: Rebrand (Target: January 2025)

1. **Week 1**: Package rename (`mamfast` → `shelfr`)
2. **Week 2**: Update all imports and references
3. **Week 3**: Documentation and README updates
4. **Week 4**: Testing and release

### Phase 2: Restructure (Target: Q1 2025)

1. Create `mam` sub-app, move pipeline commands
2. Rename `libation` → `lib` sub-app
3. Create `doctor` sub-app, move diagnostics
4. Create `mkbrr` sub-app (new functionality)
5. Create `meta` sub-app (future features)
6. Add backward-compat aliases
7. Update documentation

---

## Design Principles

### Naming

- **Sub-apps are nouns** (`mam`, `lib`, `abs`, `doctor`)
- **Commands are verbs** (`run`, `scan`, `import`, `check`)
- **Short names for frequent commands** (`lib` not `libation`, `ff` not `fastfill`)
- **Descriptive help text** with full names in tooltips

### UX

- **Top-level shortcuts** for common tasks (`status`, `config`)
- **Consistent flags** across all commands (`--dry-run`, `--yes`, `--json`)
- **Rich output** with colors, emojis, and panels
- **Helpful errors** with suggestions

### Architecture

- **Lazy imports** — Heavy dependencies load only when needed
- **Shared context** — `RuntimeContext` passed through all commands
- **Modular handlers** — Each command has focused handler module

---

## Questions to Resolve

1. **`mam` sub-app name** — Is `mam` too short/cryptic? Alternatives: `upload`, `tracker`
2. **`lib` vs `libation`** — Decision made: use `lib` ✓
3. **GitHub repo rename timing** — Before or after package rename?
4. **PyPI package name** — Is `shelfr` available?

---

## Notes

- This document focuses on planning. Implementation happens in separate PRs.
- Phase 1 (rebrand) is the immediate priority.
- Phase 2 (restructure) can happen incrementally after Phase 1 stabilizes.
- Backward compatibility is important — deprecation warnings before removal.
