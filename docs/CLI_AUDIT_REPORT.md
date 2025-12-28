# CLI Audit Report — MAMFast

**Date**: December 2025
**Scope**: Comprehensive audit of `mamfast` CLI structure, consistency, and usability
**Status**: ✅ Typer/Rich migration complete, P0-P1 fixes implemented

---

## Executive Summary

The MAMFast CLI has been **migrated from argparse to Typer** with full Rich integration for a modern, beautiful command-line experience. The audit identified several consistency issues that have been addressed.

### Major Changes ✓

1. **Typer Migration** — CLI rebuilt with [Typer](https://typer.tiangolo.com/) for modern CLI UX
2. **Rich Integration** — Beautiful formatted output with emojis, panels, and organized help groups
3. **Shell Completion** — Built-in `--install-completion` and `--show-completion` support
4. **ASIN Validation** — Validated via Typer callbacks on all `--asin` arguments
5. **Short Flags** — Added `-a`, `-n`, `-j`, `-t` for common options
6. **Shared Validation Module** — Created `utils/validation.py`
7. **Backwards Compatibility** — argparse CLI preserved in `cli_argparse.py` for tests

---

## Issues by Priority

### P0 - Critical (Blocks Users) — ✅ FIXED

#### 1. ASIN Validation Not Applied Consistently

**Problem**: The `validate_asin` function existed in `commands/libation.py` but was only applied to libation subcommands.

**Solution Implemented**:
- Created `src/mamfast/utils/validation.py` with shared ASIN validation
- Typer CLI uses `validate_asin_callback()` for all `--asin` options
- argparse CLI (preserved for tests) uses `type=validate_asin`
- Updated `commands/libation.py` to import from shared module

**Commands Now Validated**:
| Command | ASIN Arg | Status |
|---------|----------|--------|
| `prepare` | `-a/--asin` | ✅ Typer callback |
| `metadata` | `-a/--asin` | ✅ Typer callback |
| `torrent` | `-a/--asin` | ✅ Typer callback |
| `validate` | `-a/--asin` | ✅ Typer callback |
| `dry-run` | `-a/--asin` | ✅ Typer callback |
| `check-suspicious` | `-a/--asin` | ✅ Typer callback |
| `abs-restore` | `-a/--asin` | ✅ Typer callback |
| `libation liberate` | `--asin` | ✅ Typer callback |
| `libation redownload` | positional | ✅ argparse validation |
| `libation set-status` | positional | ✅ argparse validation |

---

### P1 - High Priority (Usability Issues) — ✅ FIXED

#### 2. --limit Default Inconsistency

**Solution**: Standardized all `--limit` defaults to 20.

| Command | Before | After |
|---------|--------|-------|
| `dry-run` | 10 | 20 |
| `check-duplicates` | 20 | 20 ✓ |
| `state list` | None | 20 |

#### 3. Short Flags Added

| Flag | Short Form |
|------|------------|
| `--asin` | `-a` |
| `--limit` | `-n` |
| `--json` | `-j` |
| `--threshold` | `-t` |

#### 4. --json Output Coverage

**Status**: Available on validate, check-suspicious, state list. Other commands remain as future enhancement.

---

### P2 - Medium Priority (Polish)

#### 5. Epilog Inconsistency

**Problem**: Some commands have helpful epilogs, others don't:

| Command | Has Epilog | Content |
|---------|-----------|---------|
| `validate` | ✓ | "Runs validation checks without processing releases." |
| `validate-config` | ✓ | "Validates JSON structure, regex patterns, and required fields." |
| `dry-run` | ✓ | "Shows before/after for title filtering and folder renaming." |
| `check-duplicates` | ✓ | "Uses RapidFuzz to find near-duplicate titles." |
| `prepare` | ✗ | — |
| `metadata` | ✗ | — |
| `torrent` | ✗ | — |
| `upload` | ✗ | — |
| `discover` | ✗ | — |

**Recommendation**: Add brief, useful epilogs to all commands explaining what they do in more detail.

#### 6. Help Text Quality Varies

**Examples of Good Help**:
```
abs-orphans:
  --cleanup             Remove orphaned folders (only those with matching audio folder)
  --cleanup-all         Remove ALL orphaned folders (even without matches - DANGEROUS)
```

**Examples Needing Improvement**:
```
prepare:
  --asin ASIN  Process specific release by ASIN only

# Better:
  --asin ASIN  Process only the release with this ASIN (format: B0XXXXXXXXX)
```

#### 7. Positional vs Optional Arg Inconsistency

**Problem**: Some commands use positional args, others use `--asin` for the same concept:

| Command | ASIN Specification |
|---------|-------------------|
| `abs-check-duplicate` | positional `asin` |
| `state retry` | positional `asin` |
| `state clear` | positional `asin` |
| `prepare` | optional `--asin` |
| `validate` | optional `--asin` |

**Observation**: This makes sense contextually (required vs optional), but should be documented.

#### 8. Missing Metavar for Clearer Help

**Problem**: Some arguments show `ASIN` but others show `asin`:

```
# Shows as:
abs-check-duplicate asin        # lowercase
state retry asin                # lowercase
prepare --asin ASIN             # uppercase

# Better consistency: always uppercase for metavar
```

---

### P3 - Low Priority (Nice to Have)

#### 9. ~~No Bash/Zsh Completion Support~~ — ✅ FIXED

**Solution**: Typer provides built-in shell completion:
```bash
mamfast --install-completion  # Install for current shell
mamfast --show-completion     # Show completion script
```

#### 10. No Command Aliases

**Observation**: Some commands have long names that could benefit from aliases:

| Command | Potential Alias |
|---------|----------------|
| `check-duplicates` | `dupes` |
| `check-suspicious` | `suspicious` |
| `abs-check-duplicate` | `abs-dup` |
| `abs-import` | `import` |
| `validate-config` | `lint` |

#### 11. Global --dry-run Placement

**Good**: Global `--dry-run` is documented to go BEFORE subcommand.

**Concern**: New users may try `mamfast run --dry-run` (wrong) instead of `mamfast --dry-run run` (correct).

**Current Mitigation**: Epilog on `run` command says "Tip: Use 'mamfast --dry-run run' to preview without making changes."

**Enhancement**: Consider also accepting `--dry-run` as a subcommand arg that prints a warning and suggests correct syntax.

---

## Structural Observations

### Command Organization ✓

The CLI is well-organized into logical groups:
- **Core Pipeline**: scan, discover, prepare, metadata, torrent, upload, run
- **State Management**: state {list, prune, retry, clear, export}
- **ABS Integration**: abs-init, abs-import, abs-check-duplicate, abs-trump-check, etc.
- **Diagnostics**: check, validate, validate-config, dry-run, check-duplicates, check-suspicious
- **Libation Wrapper**: libation {scan, liberate, status, search, export, settings, books, redownload, set-status, convert, guide}

### Exit Code Handling ✓

Commands consistently return:
- `0` for success
- `1` for errors/failures
- argparse returns `2` for invalid arguments

### Help System ✓

- `-h` and `--help` work consistently
- `--version` / `-V` works
- Main help shows examples
- Subcommand help is available

---

## Recommended Implementation Order

### Phase 1 - ASIN Validation (P0)
1. Create `src/mamfast/utils/validation.py` with shared `validate_asin()`
2. Apply to all `--asin` arguments in `cli.py`
3. Apply to positional `asin` arguments where format matters

### Phase 2 - Consistency Fixes (P1)
1. Standardize `--limit` defaults to 20
2. Add short flags: `-a/--asin`, `-n/--limit`, `-j/--json`
3. Add `--json` to missing commands

### Phase 3 - Polish (P2)
1. Add epilogs to commands missing them
2. Improve help text descriptions
3. Add metavar consistency

### Phase 4 - Enhancements (P3)
1. Consider argcomplete for shell completion
2. Document command organization in README

---

## Appendix: Full Command Tree

```
mamfast
├── Global Options:
│   ├── -h, --help
│   ├── -V, --version
│   ├── -v, --verbose
│   ├── -c, --config CONFIG
│   └── --dry-run
│
├── Core Pipeline:
│   ├── scan
│   ├── discover [--all]
│   ├── prepare [--asin]
│   ├── metadata [path] [--asin]
│   ├── torrent [path] [--preset] [--asin]
│   ├── upload [--paused]
│   └── run [--skip-scan] [--skip-metadata] [--no-run-lock]
│
├── Status & Config:
│   ├── status
│   ├── config
│   └── check [--quick]
│
├── Validation & Diagnostics:
│   ├── validate [--asin] [--json]
│   ├── validate-config
│   ├── dry-run [--limit] [--asin]
│   ├── check-duplicates [--threshold] [--limit] [--include-processed]
│   └── check-suspicious [--threshold] [--asin] [--include-processed] [--json]
│
├── State Management:
│   └── state
│       ├── list [--processed] [--failed] [--limit] [--json]
│       ├── prune
│       ├── retry <asin>
│       ├── clear <asin>
│       └── export <output_file>
│
├── Audiobookshelf:
│   ├── abs-init
│   ├── abs-import [paths...] [-d POLICY] [--no-scan] [--no-abs-search]
│   │             [--confidence] [--no-trump] [--trump-aggressiveness]
│   │             [--cleanup-strategy] [--cleanup-path] [--no-cleanup] [--no-metadata]
│   ├── abs-check-duplicate <asin>
│   ├── abs-trump-check [paths...] [--detailed]
│   ├── abs-restore [archive_path] [--asin] [--list]
│   ├── abs-cleanup [paths...] [--strategy] [--cleanup-path] [--no-verify-seed] [--min-age-days]
│   ├── abs-rename [--source] [--pattern] [--fetch-metadata] [--abs-search]
│   │             [--abs-search-confidence] [--interactive] [--force] [--report]
│   ├── abs-orphans [--source] [--cleanup] [--cleanup-all] [--min-match-score] [--report]
│   └── abs-resolve-asins [--path] [--confidence] [--write-sidecar]
│
└── Libation:
    └── libation
        ├── scan [--liberate]
        ├── liberate [--asin] [--yes]
        ├── status [--refresh]
        ├── search <query> [--limit] [--format]
        ├── export [-o OUTPUT] [-f FORMAT]
        ├── settings [--raw]
        ├── books [--status STATUS] [--format FORMAT] [--limit LIMIT]
        ├── redownload <asin> [--yes]
        ├── set-status <asin> <status> [--yes]
        ├── convert [--asin] [--quality] [--yes]
        └── guide [--section SECTION]
```

---

## Files Modified

| File | Changes |
|------|---------|
| `src/mamfast/cli.py` | **New Typer CLI** with Rich markup, organized command groups, ASIN callbacks |
| `src/mamfast/cli_argparse.py` | **Preserved argparse CLI** for backwards compatibility and tests |
| `src/mamfast/utils/validation.py` | Shared `validate_asin()` + `is_valid_asin()` |
| `src/mamfast/commands/libation.py` | Import validation from shared module, UX improvements |
| `pyproject.toml` | Added `typer>=0.12.0` dependency |
| `tests/test_cli_typer.py` | **New tests** for Typer CLI using CliRunner |
| `tests/test_input_validation.py` | **New tests** for ASIN validation module |

---

## Architecture After Migration

```
mamfast (entrypoint)
    │
    ├── cli.py (Typer)          ← Main CLI, beautiful Rich output
    │   ├── app                  ← Typer app instance
    │   ├── state_app            ← Sub-app for state commands
    │   ├── libation_app         ← Sub-app for libation commands
    │   └── Re-exports           ← build_parser, cmd_abs_* for compat
    │
    ├── cli_argparse.py          ← Preserved argparse CLI for tests
    │   └── build_parser()       ← Used by test_cli_abs.py etc.
    │
    └── utils/validation.py      ← Shared ASIN validation
        ├── validate_asin()      ← For argparse type=
        └── is_valid_asin()      ← Boolean helper
```
