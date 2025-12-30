# Implementation Plans

This folder contains active work items: features being developed, improvements planned, and migration tasks deferred to future phases.

## Quick Start

**"What are we doing next?"** → Check [Priority Matrix](#priority-matrix) below
**"What's blocking progress?"** → See [MIGRATION_BACKLOG.md](MIGRATION_BACKLOG.md) (P2 deferrals)
**"What features are planned?"** → Browse files by phase below

## Files

| File | Phase | Purpose | Priority |
| --- | --- | --- | --- |
| [IMPROVEMENTS_PLAN.md](IMPROVEMENTS_PLAN.md) | P1+ | Feature roadmap: search, filtering, metadata, workflows | Future |
| [VALIDATION_PLAN.md](VALIDATION_PLAN.md) | P1 | Input validation hardening and error handling | P1 |
| [STATE_HARDENING_PLAN.md](STATE_HARDENING_PLAN.md) | P1 | State management and persistence improvements | P1 |
| [PACKAGE_UPGRADE_PLAN.md](PACKAGE_UPGRADE_PLAN.md) | P2 | Dependency upgrades (tenacity, platformdirs, etc.) | P2 |
| [MIGRATION_BACKLOG.md](MIGRATION_BACKLOG.md) | P2+ | Deferred migrations: subprocess hardening, typing | P2+ |

## Priority Matrix

### P0 (Shipped ✅)

- CLI refactoring (6 phases) — **COMPLETE**
- Package upgrades (tenacity, platformdirs) — **COMPLETE**
- sh library integration — **COMPLETE**

### P1 (Next)

- **Validation hardening** — PLANNED
  - Input validation pipeline
  - Error messages
  - Field constraints

- **State management** — PLANNED
  - Persistence layer
  - Recovery patterns
  - Corruption detection

### P2+ (Backlog)

- Subprocess migrations (sh → more granular calls)
- Advanced typing (Protocol, TypeVar)
- Performance optimizations

## How to Contribute

1. Pick a P1 plan file above
2. Review acceptance criteria
3. Check blockers section
4. Start implementing
5. Link PRs to this doc

## Status Dashboard

| Initiative | Status | ETA | Owner |
| --- | --- | --- | --- |
| CLI Refactoring | ✅ COMPLETE | 2025-12-30 | @team |
| Validation Plan | 📋 PLANNING | 2026-01-15 | TBD |
| State Hardening | 📋 PLANNING | 2026-01-20 | TBD |
| P2 Migrations | ⏸️ BACKLOG | Q1 2026 | TBD |
