# CLI Documentation

This folder contains documentation about the shelfr CLI architecture, refactoring efforts, and audit results.

## Quick Start

- **New to the CLI?** Start with [CLI_ARCHITECTURE.md](CLI_ARCHITECTURE.md) for current structure and future plans
- **Refactoring history?** See [REFACTORING_PLAN.md](REFACTORING_PLAN.md) for the original 6-phase plan
- **Want proof it works?** See [AUDIT_REPORT.md](AUDIT_REPORT.md) for test results + usage findings
- **Detailed verification?** Check [AUDIT_VERIFICATION.md](AUDIT_VERIFICATION.md) for phase-by-phase evidence

## Files

| File | Purpose |
| --- | --- |
| [CLI_ARCHITECTURE.md](CLI_ARCHITECTURE.md) | **Current CLI structure**, sub-apps, implementation status, and future plans |
| [REFACTORING_PLAN.md](REFACTORING_PLAN.md) | 6-phase CLI architecture refactoring plan, acceptance criteria, and completion status |
| [AUDIT_REPORT.md](AUDIT_REPORT.md) | Audit findings: usage patterns, deprecation status, test coverage (2,132 tests passing) |
| [AUDIT_VERIFICATION.md](AUDIT_VERIFICATION.md) | Detailed verification of all 6 refactoring phases with code evidence and line counts |

## Current Sub-Apps

| Sub-App | Status | Commands |
|---------|--------|----------|
| `abs` | ✅ Complete | init, import, cleanup, rename, orphans, ... |
| `libation` | ✅ Complete | scan, liberate, convert, status, books, ... |
| `state` | ✅ Complete | list, prune, retry, clear, export |
| `mam` | ✅ Complete | bbcode, render |
| `edit` | ✅ Tier 1+2 | config, presets, file, inline, preview, diff, yaml-tree |
| `mkbrr` | 🔲 Planned | create, inspect, check, modify |
| `doctor` | 🔲 Planned | check, validate, config, dupes, suspicious |
| `meta` | 🔲 Planned | preview, enrich, audit |

## Related Documentation

- [../SHELFR_REBRAND_PLAN.md](../SHELFR_REBRAND_PLAN.md) - Overall rebrand plan
- [../implementation/MKBRR_WRAPPER_PLAN.md](../implementation/MKBRR_WRAPPER_PLAN.md) - mkbrr CLI details
- [../implementation/TEXT_EDITOR_PLAN.md](../implementation/TEXT_EDITOR_PLAN.md) - Editor tiers (1-3)

## Key Accomplishments

✅ **Phase 1A**: RuntimeContext foundation (typed context object)
✅ **Phase 1B**: Split monolithic cli.py → 10 focused modules (2,488 lines, all under 400 lines)
✅ **Phase 2**: Promote ABS to sub-app (`shelfr abs <verb>`)
✅ **Phase 3**: Deprecate argparse CLI (frozen, showing warnings)
✅ **Phase 4**: Split large handlers into commands/ packages
✅ **UX Polish**: Added `--yes`/`-y` flags and command aliases

## Status

**Complete as of December 30, 2025**

All acceptance criteria met. Ready for production. See [AUDIT_VERIFICATION.md](AUDIT_VERIFICATION.md) for complete verification report.
