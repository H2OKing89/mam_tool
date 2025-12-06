# MAMFast Naming System

> Quick reference guide for the MAMFast naming system. For detailed documentation, see the related docs.

## Related Documentation

| Document | Description |
|----------|-------------|
| [Audnex Normalization](./NAMING_AUDNEX_NORMALIZATION.md) | How Audible metadata is normalized |
| [Processing Pipeline](./NAMING_PIPELINE.md) | Full cleaning pipeline and order |
| [Folder & File Schemas](./NAMING_FOLDER_FILE_SCHEMAS.md) | Output formats, truncation, MAM JSON |
| [Rules Reference](./NAMING_RULES.md) | Matching rules, phrase removal, author map |
| [Implementation](./NAMING_IMPLEMENTATION.md) | Phases, testing, changelog |

---

## Overview

MAMFast uses a **multi-layer naming system** that transforms raw Libation/Audible data into clean, MAM-compliant folder and file names.

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MAMFast Naming Pipeline                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌──────────────┐    ┌───────────────────┐    ┌──────────────────────────┐ │
│  │   Libation   │───▶│ Audnex Normalize  │───▶│   Phrase/Rule Cleaning   │ │
│  │  Raw Input   │    │ (title/series fix)│    │   (naming.json rules)    │ │
│  └──────────────┘    └───────────────────┘    └──────────────────────────┘ │
│                                                           │                 │
│                                                           ▼                 │
│  ┌──────────────┐    ┌───────────────────┐    ┌──────────────────────────┐ │
│  │ MAM Folder/  │◀───│    Truncation     │◀───│   Author/Year/Series     │ │
│  │ File Output  │    │  (225 char limit) │    │      Formatting          │ │
│  └──────────────┘    └───────────────────┘    └──────────────────────────┘ │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Concepts

| Concept | Description |
|---------|-------------|
| **Audnex Normalization** | Fixes Audible's title/subtitle swaps using `seriesPrimary` |
| **NormalizedBook** | Pydantic model holding corrected title/subtitle/series |
| **MamPath** | Tracks 225-char path compliance with truncation metadata |
| **Phrase Removal** | Regex-based removal of marketing text, editions, etc. |
| **Author Map** | Handles pseudonyms and author name variations |

---

## Quick Reference

### Input → Output Example

**Libation Raw Data:**
```
title: "Project Hail Mary (Unabridged)"
subtitle: null
seriesPrimary: null
authors: ["Andy Weir"]
```

**After Normalization & Cleaning:**
```
folder: "Andy Weir - Project Hail Mary (2021) {ASIN.B08G9PRS1K}"
file:   "Andy Weir - Project Hail Mary.m4b"
```

### Series Example

**Libation Raw Data:**
```
title: "The Martian"
subtitle: null
seriesPrimary: "The Martian, Book 1"
authors: ["Andy Weir"]
```

**After Normalization & Cleaning:**
```
folder: "Andy Weir - The Martian vol_01 - The Martian (2014) {ASIN.B00B5HZGUG}"
file:   "Andy Weir - The Martian vol_01 - The Martian.m4b"
```

---

## Glossary

| Term | Definition |
|------|------------|
| **ASIN** | Amazon Standard Identification Number (10-char alphanumeric) |
| **MAM** | MyAnonaMouse - private audiobook tracker |
| **Audnex** | API service providing normalized Audible metadata |
| **Libation** | Desktop app for downloading Audible audiobooks |
| **pathvalidate** | Library for cross-platform filename sanitization |
| **Golden Test** | Test using pre-computed expected outputs for validation |

---

## File Locations

| File | Purpose |
|------|---------|
| `src/mamfast/utils/naming.py` | Core naming functions (~1900 lines) |
| `src/mamfast/models.py` | `NormalizedBook`, `MamPath` models |
| `config/naming.json` | Phrase removal rules, author map |
| `src/mamfast/schemas/naming.py` | Pydantic validation for naming.json |
| `tests/test_naming.py` | Naming unit tests |
| `tests/test_golden.py` | Golden test framework |
| `tests/golden/` | Golden test fixtures |

---

## See Also

- [CLAUDE.md](/CLAUDE.md) - Full project reference
- [Copilot Instructions](/.github/copilot-instructions.md) - Development guidelines
