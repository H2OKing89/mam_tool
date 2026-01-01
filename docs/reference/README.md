# Reference Documentation

Static reference materials: API docs, naming systems, system architecture, and troubleshooting guides.

## Quick Start

- **Metadata system?** → `metadata/` folder (naming + architecture)
- **File naming system?** → `metadata/naming/` folder
- **Metadata architecture?** → `metadata/architecture/` folder
- **Audiobookshelf API?** → `audiobookshelf/` folder
- **MAM torrenting?** → `mam/` folder
- **External APIs?** → `audnex/`, `hardcover/` folders

## Folders

| Folder | Purpose |
| --- | --- |
| `metadata/` | Unified metadata docs: naming rules, architecture, providers, exporters |
| `metadata/naming/` | File naming rules, conventions, golden tests, edge cases |
| `metadata/architecture/` | Provider/exporter plugin system, refactoring plan |
| `audiobookshelf/` | ABS API reference, import workflows, rename logic, trumping |
| `audnex/` | Audnex API schemas and integration notes |
| `hardcover/` | Hardcover GraphQL API reference and query examples |
| `mam/` | MAM torrent system reference and fast-fill guide |
| `tracking/` | Issue tracking and known bugs (if present) |

## Notes

These docs are **rarely edited** — they document stable systems and external APIs. For active work, see `/implementation/`.
