# Plugin Architecture for Metadata Providers

> Part of [Metadata Architecture Documentation](README.md)

---

## Overview

To support future metadata sources (Hardcover, Goodreads, OpenLibrary, private databases), we should design a **pluggable provider system** from the start.

**Core principles:**

- Providers emit partial canonical fields → Aggregator merges deterministically
- Per-field provenance tracking (`sources[field] = provider`) for debugging
- Config-driven enable/priority + aggregation strategy
- Private DB can override any field (killer feature for power users)

---

## 1. Current Sources

| Source | Type | Strengths | Weaknesses |
|--------|------|-----------|------------|
| **Audnex** | API | ASIN, chapters, accurate narrator/author | US-centric, no reviews |
| **MediaInfo** | Local (sync) | Bitrate, codec, duration, embedded tags | No book metadata |
| **Libation** | Local | Folder structure, series heuristics | Limited fields |
| **ABS metadata.json** | Local | User-corrected data | May be stale |

---

## 2. Potential Future Sources

| Source | What It Offers | Use Case |
|--------|----------------|----------|
| **Hardcover** | Better series data, edition tracking, reviews | Series-heavy libraries |
| **Goodreads** | Reviews, ratings, popularity | Social metadata |
| **OpenLibrary** | ISBN data, covers, open data | Fallback, legal covers |
| **Google Books** | ISBN → metadata lookup | ISBN-based discovery |
| **Private DB** | Personal corrections, custom fields | Power users |
| **MAM API** | Existing uploads, group data | Dupe checking |

---

## 3. Provider Protocol Design

```python
# metadata/providers/base.py
from abc import ABC, abstractmethod
from typing import Protocol

class MetadataProvider(Protocol):
    """Protocol for pluggable metadata providers."""
    
    name: str  # "audnex", "hardcover", "goodreads"
    priority: int  # Lower = higher priority (0 = primary)
    
    def can_lookup(self, identifier: str, id_type: str) -> bool:
        """Check if provider can handle this identifier type.
        
        Args:
            identifier: The ID value (e.g., "B0CJ1234", "978-0-123456-78-9")
            id_type: Type of ID ("asin", "isbn", "goodreads_id", "hardcover_id")
        """
        ...
    
    async def fetch(self, identifier: str, id_type: str) -> ProviderResult:
        """Fetch metadata from this provider.
        
        Returns:
            ProviderResult with partial CanonicalMetadata fields
        """
        ...
    
    def get_confidence(self, field: str) -> float:
        """Confidence score for a specific field (0.0-1.0).
        
        Example: Audnex has high confidence for ASIN, low for reviews.
        """
        ...


@dataclass
class ProviderResult:
    """Result from a metadata provider lookup."""
    
    provider: str  # Which provider returned this
    success: bool
    data: dict[str, Any]  # Partial metadata fields
    confidence: dict[str, float]  # Per-field confidence scores
    error: str | None = None
    cached: bool = False
    cache_age_seconds: int | None = None
```

---

## 4. Provider Registry

```python
# metadata/providers/registry.py
class ProviderRegistry:
    """Central registry for metadata providers."""
    
    _providers: dict[str, MetadataProvider] = {}
    _priority_order: list[str] = []
    
    @classmethod
    def register(cls, provider: MetadataProvider) -> None:
        """Register a provider."""
        cls._providers[provider.name] = provider
        cls._recompute_priority()
    
    @classmethod
    def get(cls, name: str) -> MetadataProvider | None:
        """Get provider by name."""
        return cls._providers.get(name)
    
    @classmethod
    def get_for_identifier(cls, identifier: str, id_type: str) -> list[MetadataProvider]:
        """Get all providers that can handle this identifier, in priority order."""
        return [
            p for p in cls._priority_order 
            if p.can_lookup(identifier, id_type)
        ]
    
    @classmethod
    def all(cls) -> list[MetadataProvider]:
        """All registered providers in priority order."""
        return list(cls._priority_order)
```

---

## 5. Metadata Aggregator (Merge Strategy)

```python
# metadata/providers/aggregator.py
class MetadataAggregator:
    """Aggregate metadata from multiple providers with conflict resolution."""
    
    def __init__(self, merge_strategy: str = "priority"):
        """
        Args:
            merge_strategy: How to resolve conflicts
                - "priority": Use highest-priority provider's value
                - "confidence": Use highest-confidence value per field
                - "vote": Use most common value (requires 3+ sources)
        """
        self.merge_strategy = merge_strategy
    
    async def fetch_all(
        self,
        identifier: str,
        id_type: str,
        *,
        providers: list[str] | None = None,
        stop_on_complete: bool = True,
    ) -> AggregatedResult:
        """Fetch from multiple providers and merge results.
        
        Args:
            identifier: The lookup ID
            id_type: Type of ID
            providers: Specific providers to use (None = all)
            stop_on_complete: Stop when all required fields are filled
        """
        ...
    
    def merge(self, results: list[ProviderResult]) -> CanonicalMetadata:
        """Merge multiple provider results into canonical metadata."""
        ...


@dataclass  
class AggregatedResult:
    """Aggregated metadata from multiple providers."""
    
    metadata: CanonicalMetadata
    sources: dict[str, str]  # field -> provider that provided it
    conflicts: list[FieldConflict]  # Fields where providers disagreed
    missing: list[str]  # Fields no provider had


@dataclass
class FieldConflict:
    """Record of a field conflict between providers."""
    
    field: str
    values: dict[str, Any]  # provider -> value
    resolved_value: Any
    resolution_reason: str  # "priority", "confidence", "vote"
```

---

## 6. Example Provider Implementation

```python
# metadata/providers/hardcover.py
class HardcoverProvider:
    """Hardcover.app metadata provider."""
    
    name = "hardcover"
    priority = 10  # Secondary to Audnex
    
    SUPPORTED_IDS = {"isbn", "hardcover_id", "asin"}  # Can search by ASIN
    
    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.getenv("HARDCOVER_API_KEY")
        self.client = httpx.AsyncClient(base_url="https://api.hardcover.app")
    
    def can_lookup(self, identifier: str, id_type: str) -> bool:
        return id_type in self.SUPPORTED_IDS
    
    async def fetch(self, identifier: str, id_type: str) -> ProviderResult:
        try:
            resp = await self.client.get(f"/books/search", params={id_type: identifier})
            data = resp.json()
            return ProviderResult(
                provider=self.name,
                success=True,
                data=self._normalize(data),
                confidence={"series": 0.95, "title": 0.8, "author": 0.8},
            )
        except Exception as e:
            return ProviderResult(provider=self.name, success=False, error=str(e))
    
    def _normalize(self, raw: dict) -> dict:
        """Convert Hardcover response to canonical field names."""
        return {
            "title": raw.get("title"),
            "series_name": raw.get("series", {}).get("name"),
            "series_position": raw.get("series", {}).get("position"),
            # ... map other fields
        }
```

---

## 7. Configuration for Providers

```yaml
# config/config.yaml
metadata:
  providers:
    audnex:
      enabled: true
      priority: 0  # Primary
      regions: ["us", "uk", "au"]
    
    hardcover:
      enabled: true
      priority: 10
      api_key: ${HARDCOVER_API_KEY}  # From env
    
    goodreads:
      enabled: false  # Disabled by default (scraping issues)
      priority: 20
    
    private_db:
      enabled: false
      priority: 5  # High priority when enabled (user corrections)
      connection_string: ${PRIVATE_DB_URL}
  
  aggregation:
    strategy: "confidence"  # priority | confidence | vote
    required_fields: ["title", "asin"]
    stop_on_complete: true
    cache_ttl_hours: 24
```

---

## 8. Directory Structure with Providers

```bash
src/shelfr/metadata/
├── __init__.py
├── canonical.py          # CanonicalMetadata (single source of truth)
├── cleaning.py           # Shared cleaners
├── aggregator.py         # Multi-provider merge logic
│
├── providers/            # Pluggable providers
│   ├── __init__.py       # Registry, base protocol
│   ├── base.py           # MetadataProvider protocol
│   ├── audnex.py         # Audnex provider (current metadata.py code)
│   ├── mediainfo.py      # MediaInfo provider
│   ├── hardcover.py      # Hardcover provider (future)
│   ├── goodreads.py      # Goodreads provider (future)
│   ├── openlib.py        # OpenLibrary provider (future)
│   └── private_db.py     # Private database provider (future)
│
├── opf/                  # OPF sidecar generation
├── json/                 # JSON sidecar generation
└── mam/                  # MAM-specific formatting
```

---

## 9. Usage Example

```python
from shelfr.metadata import MetadataAggregator, ProviderRegistry
from shelfr.metadata.providers import AudnexProvider, HardcoverProvider

# Register providers (usually done at startup)
ProviderRegistry.register(AudnexProvider())
ProviderRegistry.register(HardcoverProvider(api_key="..."))

# Fetch with aggregation
aggregator = MetadataAggregator(merge_strategy="confidence")
result = await aggregator.fetch_all(
    identifier="B0CJ1234",
    id_type="asin",
)

# Use the merged metadata
print(result.metadata.title)
print(result.sources)  # {"title": "audnex", "series": "hardcover"}
print(result.conflicts)  # Any disagreements
```

---

## 10. Benefits of Plugin Architecture

| Benefit | Description |
|---------|-------------|
| **Extensibility** | Add new sources without touching core code |
| **Fallback chain** | If Audnex fails, try Hardcover, then OpenLibrary |
| **Field-level sourcing** | Use best source for each field |
| **User corrections** | Private DB can override any field |
| **Testing** | Mock providers for unit tests |
| **Caching** | Each provider can have its own cache strategy |
| **Rate limiting** | Per-provider rate limits |

---

## 11. Implementation Priority

| Phase | What to Build |
|-------|---------------|
| **Now** | Define `MetadataProvider` protocol, extract Audnex to provider |
| **Phase 2** | Add `ProviderRegistry`, basic aggregation |
| **Phase 3** | Add Hardcover provider |
| **Later** | Goodreads, OpenLibrary, private DB |
