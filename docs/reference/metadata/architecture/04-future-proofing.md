# Future-Proofing Considerations

> Part of [Metadata Architecture Documentation](README.md)

---

## 1. Output Exporters (Inverse of Providers)

Providers fetch metadata **in**, but we also need pluggable **exporters** for output formats:

```python
# metadata/exporters/base.py
from typing import Protocol
from pathlib import Path

class MetadataExporter(Protocol):
    """Protocol for pluggable output formats.
    
    Mirrors provider architecture with registry pattern.
    """
    
    name: str  # "opf", "json", "nfo", "cue"
    file_extension: str  # ".opf", ".json", ".nfo"
    
    def render(self, metadata: CanonicalMetadata, **options) -> str | bytes:
        """Generate output content from canonical metadata.
        
        Returns str for text formats (OPF, JSON, NFO, MD),
        bytes for binary formats (future: zip, images).
        """
        ...
    
    def output_path(self, base_dir: Path, **options) -> Path:
        """Compute default output path for this exporter.
        
        Different exporters may use different naming conventions:
        - OPF: {asin}.opf
        - JSON: metadata.json
        - NFO: {title}.nfo
        """
        ...
    
    def write(self, metadata: CanonicalMetadata, base_dir: Path, **options) -> Path:
        """Write to file with atomic write + proper encoding, return final path.
        
        Implementation note: use a shared helper for atomic writes:
        - Write to tmp file in same directory
        - os.replace(tmp, final) for atomicity
        - Text encoding for str, binary mode for bytes
        """
        ...


# metadata/exporters/registry.py
from __future__ import annotations

from dataclasses import dataclass, field

from .base import MetadataExporter


@dataclass
class ExporterRegistry:
    """Registry for exporters (mirrors ProviderRegistry pattern)."""
    _exporters: dict[str, MetadataExporter] = field(default_factory=dict)
    
    def register(self, exporter: MetadataExporter) -> None:
        self._exporters[exporter.name] = exporter
    
    def get(self, name: str) -> MetadataExporter | None:
        return self._exporters.get(name)
    
    def all(self) -> list[MetadataExporter]:
        # Stable order: by name
        return sorted(self._exporters.values(), key=lambda e: e.name)
```

**Potential exporters:**

- `OPFExporter` - Current OPF generator
- `JsonExporter` - ABS metadata.json
- `NFOExporter` - Kodi/Plex NFO format
- `CueExporter` - CUE sheets for chapter markers
- `M3UExporter` - Playlist generation
- `MarkdownExporter` - Human-readable summary

> **When to build:** Extract to this pattern when you add a third format. Current OPF/JSON generation works fine.

---

## 2. Caching Layer (Shared Infrastructure)

Don't let each provider implement caching differently:

```python
# metadata/cache.py
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Protocol

from .providers.types import FieldName, IdType
from .schemas.versioning import SCHEMA_VERSION


def make_cache_key(provider: str, id_type: IdType, identifier: str, region: str = "us") -> str:
    """Build versioned cache key — auto-invalidates when schema changes.
    
    Note: region param is intentional for providers like Audnex that
    return different results per region.
    """
    return f"{SCHEMA_VERSION}:{provider}:{id_type}:{identifier}:{region}"


@dataclass(frozen=True)
class CachedResult:
    """What we store in cache — enough to reconstruct ProviderResult."""
    fields: dict[FieldName, Any]
    confidence: dict[FieldName, float]
    fetched_at: datetime  # Should be timezone-aware: datetime.now(timezone.utc)
    schema_version: str = SCHEMA_VERSION


class MetadataCache(Protocol):
    """Abstract caching interface."""
    
    async def get(self, key: str) -> CachedResult | None: ...
    async def set(self, key: str, value: CachedResult, ttl_seconds: int) -> None: ...
    async def invalidate(self, key: str) -> None: ...
    async def invalidate_pattern(self, pattern: str) -> None: ...


# Implementations
class FileCache(MetadataCache):
    """JSON file-based cache (current approach)."""

class SqliteCache(MetadataCache):
    """SQLite for larger datasets."""

class RedisCache(MetadataCache):
    """Redis for distributed/multi-instance setups."""
```

**Key design decisions:**

1. **Schema version in cache key** — old entries auto-invalidate when `CanonicalMetadata` changes
2. **Cache stores provenance** — `confidence`, `fetched_at` survive cache round-trip
3. **Apply cache at provider boundary** — network providers get most benefit
4. **Migration lives in IO layer** — readers/writers migrate, aggregator stays dumb

---

## 3. Event Hooks / Middleware

> **YAGNI Note:** Structured logging gives you 80% of this. Add events when you actually need Discord alerts or external integrations.

Allow instrumentation without modifying core code:

```python
# metadata/events.py
import inspect
import logging
from dataclasses import dataclass, field
from typing import Callable

logger = logging.getLogger(__name__)


@dataclass
class EventBus:
    """Event system for metadata operations.
    
    Instance-based (not class-level globals) for test isolation.
    Pass into ProviderRegistry / Aggregator / Orchestration.
    """
    _handlers: dict[str, list[Callable]] = field(default_factory=dict)
    
    # Event type constants
    PROVIDER_FETCH_START = "provider.fetch.start"
    PROVIDER_FETCH_SUCCESS = "provider.fetch.success"
    PROVIDER_FETCH_ERROR = "provider.fetch.error"
    AGGREGATION_CONFLICT = "aggregation.conflict"
    EXPORT_COMPLETE = "export.complete"
    
    def on(self, event: str, handler: Callable) -> None:
        """Register event handler."""
        self._handlers.setdefault(event, []).append(handler)
    
    async def emit(self, event: str, data: dict) -> None:
        """Emit event to all handlers (with error isolation)."""
        for handler in self._handlers.get(event, []):
            try:
                result = handler(data)
                if inspect.isawaitable(result):
                    await result
            except Exception:
                logger.exception("Event handler failed", extra={"event": event})


# Usage (instance-based, not global)
event_bus = EventBus()
event_bus.on("provider.fetch.error", send_discord_alert)
event_bus.on("aggregation.conflict", log_conflict_for_review)

# Pass to aggregator
aggregator = MetadataAggregator(registry=registry, event_bus=event_bus)
```

---

## 4. Schema Versioning & Migration

When `CanonicalMetadata` changes, we need to handle old cached data:

```python
# metadata/schemas/versioning.py
SCHEMA_VERSION = "2.0.0"

class VersionedMetadata(BaseModel):
    """Wrapper with version tracking."""
    
    schema_version: str = SCHEMA_VERSION
    data: CanonicalMetadata
    migrated_from: str | None = None  # Previous version if migrated


def migrate_metadata(data: dict, from_version: str) -> CanonicalMetadata:
    """Migrate old schema versions to current."""
    migrations = {
        "1.0.0": migrate_v1_to_v2,
        "1.5.0": migrate_v1_5_to_v2,
    }
    # Apply migrations in order...
```

---

## 5. Field Mapping Configuration

External config for provider → canonical field mapping (avoid hardcoding):

```yaml
# config/provider_mappings.yaml
hardcover:
  title: title
  subtitle: subtitle
  series.name: series_primary.name
  series.position: series_primary.position
  authors[].name: authors[].name
  published_date: release_date  # Different field name

goodreads:
  work.title: title
  work.original_publication_year: release_date
  authors.author[].name: authors[].name
```

---

## 6. Data Provenance / Audit Trail

Track where every field came from (useful for debugging, corrections):

```python
@dataclass
class FieldProvenance:
    """Track origin of each metadata field."""
    
    field: str
    value: Any
    provider: str
    fetched_at: datetime
    confidence: float
    overridden_by: str | None = None  # If user corrected


class ProvenanceTracker:
    """Track complete history of metadata assembly."""
    
    def __init__(self):
        self.history: list[FieldProvenance] = []
    
    def record(self, field: str, value: Any, provider: str, confidence: float):
        self.history.append(FieldProvenance(...))
    
    def get_source(self, field: str) -> str:
        """Which provider supplied this field?"""
        ...
    
    def export_audit_log(self) -> dict:
        """Full provenance report for debugging."""
        ...
```

---

## 7. Batch Operations

Some APIs support bulk lookups - design for it:

```python
class MetadataProvider(Protocol):
    # ... existing methods ...
    
    supports_batch: bool = False
    max_batch_size: int = 1
    
    async def fetch_batch(
        self, 
        identifiers: list[tuple[str, str]]  # [(id, type), ...]
    ) -> list[ProviderResult]:
        """Fetch multiple items in one request (if supported)."""
        ...
```

---

## 8. Custom User Fields

Let users add their own fields that flow through the system:

```python
class CanonicalMetadata(BaseModel):
    # ... standard fields ...
    
    # User-defined extras (preserved through pipeline)
    custom_fields: dict[str, Any] = Field(default_factory=dict)
    
    # Example usage:
    # metadata.custom_fields["my_rating"] = 5
    # metadata.custom_fields["read_date"] = "2024-01-15"
```

---

## 9. Sync/Async Flexibility

Some providers may need sync (file-based), others async (API):

```python
class MetadataProvider(Protocol):
    is_async: bool = True
    
    # Providers implement ONE of these
    async def fetch_async(self, identifier: str, id_type: str) -> ProviderResult: ...
    def fetch_sync(self, identifier: str, id_type: str) -> ProviderResult: ...


# Aggregator handles both
class MetadataAggregator:
    async def _call_provider(self, provider: MetadataProvider, id: str, id_type: str):
        if provider.is_async:
            return await provider.fetch_async(id, id_type)
        else:
            return await asyncio.to_thread(provider.fetch_sync, id, id_type)
```

---

## 10. Rate Limiting Infrastructure

Shared rate limiter per provider:

```python
# metadata/ratelimit.py
class RateLimiter:
    """Token bucket rate limiter."""
    
    def __init__(self, requests_per_second: float, burst: int = 1):
        self.rate = requests_per_second
        self.burst = burst
        self._tokens = burst
        self._last_refill = time.monotonic()
    
    async def acquire(self) -> None:
        """Wait until a request can be made."""
        ...


# Per-provider configuration
RATE_LIMITS = {
    "audnex": RateLimiter(5.0, burst=10),  # 5 req/s
    "hardcover": RateLimiter(2.0, burst=5),  # 2 req/s
    "goodreads": RateLimiter(1.0, burst=1),  # Very limited
}
```

---

## 11. Circuit Breaker Integration

We already have `CircuitBreaker` - make it provider-aware:

```python
# Each provider gets its own circuit breaker
class ProviderCircuitBreakers:
    _breakers: dict[str, CircuitBreaker] = {}
    
    @classmethod
    def get(cls, provider_name: str) -> CircuitBreaker:
        if provider_name not in cls._breakers:
            cls._breakers[provider_name] = CircuitBreaker(
                failure_threshold=5,
                recovery_timeout=60,
                name=f"provider:{provider_name}"
            )
        return cls._breakers[provider_name]
```

---

## 12. Testing Infrastructure

Make providers easy to mock:

```python
# metadata/providers/mock.py
class MockProvider(MetadataProvider):
    """Mock provider for testing."""
    
    name = "mock"
    priority = 999
    
    def __init__(self, responses: dict[str, ProviderResult]):
        self.responses = responses
        self.call_log: list[tuple[str, str]] = []
    
    async def fetch(self, identifier: str, id_type: str) -> ProviderResult:
        self.call_log.append((identifier, id_type))
        return self.responses.get(identifier, ProviderResult(success=False))


# In tests:
mock = MockProvider({"B0CJ1234": ProviderResult(success=True, data={...})})
ProviderRegistry.register(mock)
```
