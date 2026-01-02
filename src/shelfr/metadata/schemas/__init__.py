"""
Metadata schemas for audiobook processing.

This package contains Pydantic schemas for internal metadata representation.

Exports:
    - Person: Author/narrator with optional ASIN
    - Genre: Genre/tag classification
    - Series: Series with position info
    - CanonicalMetadata: Full audiobook metadata (single source of truth)
"""

from __future__ import annotations

from shelfr.metadata.schemas.canonical import (
    CanonicalMetadata,
    Genre,
    Person,
    Series,
)

__all__ = [
    "CanonicalMetadata",
    "Genre",
    "Person",
    "Series",
]
