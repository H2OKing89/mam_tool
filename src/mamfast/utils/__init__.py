"""Utility modules for MAMFast."""

from mamfast.utils.fuzzy import (
    ChangeAnalysis,
    DuplicatePair,
    analyze_change,
    find_best_match,
    find_duplicates,
    find_matches,
    is_suspicious_change,
    similarity_ratio,
)
from mamfast.utils.paths import safe_dirname, safe_filename, safe_filepath

__all__ = [
    "safe_dirname",
    "safe_filename",
    "safe_filepath",
    # Fuzzy matching utilities
    "ChangeAnalysis",
    "DuplicatePair",
    "analyze_change",
    "find_best_match",
    "find_duplicates",
    "find_matches",
    "is_suspicious_change",
    "similarity_ratio",
]
