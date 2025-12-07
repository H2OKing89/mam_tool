#!/usr/bin/env python3
"""Test script to investigate ABS search API behavior.

Compare our search implementation with what ABS GUI does.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import httpx
from dotenv import load_dotenv

load_dotenv("config/.env")

HOST = os.getenv("AUDIOBOOKSHELF_HOST")
API_KEY = os.getenv("AUDIOBOOKSHELF_API_KEY")
LIBRARY_ID = "d00f643c-7973-42dd-9139-2708e68e0b4e"

if not HOST or not API_KEY:
    print("Missing AUDIOBOOKSHELF_HOST or AUDIOBOOKSHELF_API_KEY in .env")
    sys.exit(1)

headers = {"Authorization": f"Bearer {API_KEY}"}


def test_search_endpoint(query: str) -> None:
    """Test the library search endpoint."""
    print(f"\n{'='*60}")
    print(f"Testing search: '{query}'")
    print(f"{'='*60}")

    # Method 1: Library search (what we currently use)
    print("\n--- Method 1: /api/libraries/{id}/search ---")
    r = httpx.get(
        f"{HOST}/api/libraries/{LIBRARY_ID}/search",
        params={"q": query, "limit": 10},
        headers=headers,
        timeout=30,
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Response keys: {data.keys()}")
        books = data.get("book", [])
        print(f"Books found: {len(books)}")
        for item in books[:5]:
            match_key = item.get("matchKey", "?")
            match_text = item.get("matchText", "?")
            lib_item = item.get("libraryItem", {})
            media = lib_item.get("media", {})
            meta = media.get("metadata", {})
            print(f"  - {meta.get('title', 'N/A')}")
            print(f"    ASIN: {meta.get('asin', 'NO ASIN')}")
            print(f"    Match: {match_key}={match_text}")
    else:
        print(f"Error: {r.text[:200]}")

    # Method 2: Global search
    print("\n--- Method 2: /api/search ---")
    r = httpx.get(
        f"{HOST}/api/search", params={"q": query, "limit": 10}, headers=headers, timeout=30
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Response keys: {data.keys()}")
        # Global search has different structure
        for key in data:
            items = data.get(key, [])
            if items:
                print(f"  {key}: {len(items)} results")

    # Method 3: Library items with filter
    print("\n--- Method 3: /api/libraries/{id}/items (filtered) ---")
    r = httpx.get(
        f"{HOST}/api/libraries/{LIBRARY_ID}/items",
        params={"filter": f"search={query}", "limit": 10},
        headers=headers,
        timeout=30,
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        results = data.get("results", [])
        print(f"Results: {len(results)}")
        for item in results[:5]:
            media = item.get("media", {})
            meta = media.get("metadata", {})
            print(f"  - {meta.get('title', 'N/A')} [ASIN: {meta.get('asin', 'N/A')}]")


def test_match_endpoint(title: str, author: str) -> None:
    """Test the match endpoint (used for metadata matching)."""
    print(f"\n{'='*60}")
    print(f"Testing match: title='{title}', author='{author}'")
    print(f"{'='*60}")

    # Method 4: Match endpoint (what ABS uses for matching)
    print("\n--- Method 4: /api/search/books (match) ---")
    r = httpx.get(
        f"{HOST}/api/search/books",
        params={
            "title": title,
            "author": author,
            "provider": "audible",
        },
        headers=headers,
        timeout=30,
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Results: {len(data)} matches")
        for item in data[:5]:
            print(f"  - {item.get('title', 'N/A')}")
            print(f"    ASIN: {item.get('asin', 'N/A')}")
            print(f"    Author: {item.get('author', 'N/A')}")
    else:
        print(f"Error: {r.text[:200]}")


def test_audible_search(query: str) -> None:
    """Test ABS's Audible provider search."""
    print(f"\n{'='*60}")
    print(f"Testing Audible provider search: '{query}'")
    print(f"{'='*60}")

    # This is what ABS GUI likely uses for external searches
    print("\n--- Method 5: /api/search/covers (Audible) ---")
    r = httpx.get(
        f"{HOST}/api/search/covers",
        params={
            "title": query,
            "provider": "audible",
        },
        headers=headers,
        timeout=30,
    )
    print(f"Status: {r.status_code}")
    if r.status_code == 200:
        data = r.json()
        print(f"Results: {len(data)} covers")
        for item in data[:3]:
            print(f"  - {item}")


if __name__ == "__main__":
    # Test with the problematic titles
    test_queries = [
        "Primal Imperative",
        "Primal Imperative Quentin Kilgore",
        "Adachi Shimamura",
        "Adachi and Shimamura Vol 7",
    ]

    for q in test_queries:
        test_search_endpoint(q)

    # Test match endpoint
    test_match_endpoint("Primal Imperative", "Quentin Kilgore")
    test_match_endpoint("Adachi and Shimamura Vol 7", "Hitoma Iruma")

    # Test Audible search
    test_audible_search("Primal Imperative Quentin Kilgore")
