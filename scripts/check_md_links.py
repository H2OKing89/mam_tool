#!/usr/bin/env python3
"""Check for broken internal markdown links in docs/."""

from __future__ import annotations

import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"\[([^\]]*)\]\(([^)]+)\)")


def is_url(s: str) -> bool:
    """Check if string is an external URL."""
    return s.startswith(("http://", "https://", "mailto:", "#"))


def resolve_target(md_file: Path, target: str) -> Path | None:
    """Resolve a markdown link target to an actual path."""
    if not target or is_url(target):
        return None

    # Split fragment from path
    path_part = target.split("#", 1)[0].strip()
    if not path_part:
        return None

    # Resolve relative to the markdown file's directory
    resolved = (md_file.parent / path_part).resolve()

    # Check if it exists
    if resolved.exists():
        return resolved

    return None


def check_links() -> int:
    """Check all markdown links in docs/ folder."""
    docs_dir = Path("docs")
    if not docs_dir.exists():
        print("ERROR: docs/ not found. Run from repo root.", file=sys.stderr)
        return 2

    broken = []
    checked = 0

    for md_file in sorted(docs_dir.rglob("*.md")):
        text = md_file.read_text(encoding="utf-8", errors="ignore")

        for display, target in LINK_RE.findall(text):
            checked += 1
            resolved = resolve_target(md_file, target)

            if resolved is None and not is_url(target) and target.strip():
                # This might be a broken link
                rel_path = md_file.relative_to(docs_dir)
                broken.append((rel_path, target, display))

    if broken:
        print(f"❌ Found {len(broken)} broken link(s):\n")
        for file_path, target, display in broken:
            print(f"  {file_path}: [{display}]({target})")
        return 1

    print(f"✅ OK: checked {checked} links, all valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(check_links())
