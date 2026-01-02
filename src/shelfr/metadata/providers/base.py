"""
MetadataProvider protocol definition.

All metadata providers implement this protocol. The protocol uses duck typing
via typing.Protocol for flexibility with mocks and plugins.

Key design decisions:
- All providers implement async fetch() - sync providers use asyncio.to_thread()
- Protocol (not ABC) allows easy mocking and duck typing
- kind attribute enables two-stage fetch (local first, then network)
- is_override flag allows abs_sidecar/private_db to intentionally clear fields
"""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from .types import IdType, LookupContext, ProviderResult

# Provider kind determines fetch ordering in aggregator
ProviderKind = Literal["local", "network"]


@runtime_checkable
class MetadataProvider(Protocol):
    """Protocol for pluggable metadata providers.

    All providers implement async fetch(). Sync providers (like MediaInfo)
    wrap their subprocess work with asyncio.to_thread() internally.
    This keeps the aggregator simple - it doesn't care who's sync vs async.

    Attributes:
        name: Unique provider identifier (e.g., "audnex", "mediainfo")
        priority: Lower = higher priority (0 = primary). Used for tie-breaking.
        kind: "local" (cheap) or "network" (expensive). Affects fetch order.
        is_override: True for providers that can intentionally clear fields
                     (e.g., abs_sidecar, private_db). Normal providers can't
                     set empty values - they're skipped.

    Example implementation:
        class MyProvider:
            name = "my_provider"
            priority = 50
            kind: ProviderKind = "network"
            is_override = False

            def can_lookup(self, ctx: LookupContext, id_type: IdType) -> bool:
                return id_type == "asin" and ctx.asin is not None

            async def fetch(self, ctx: LookupContext, id_type: IdType) -> ProviderResult:
                # Fetch metadata...
                result = ProviderResult(provider=self.name, success=True)
                result.set_field("title", "My Book", confidence=0.9)
                return result
    """

    name: str
    priority: int
    kind: ProviderKind
    is_override: bool

    def can_lookup(self, ctx: LookupContext, id_type: IdType) -> bool:
        """Check if provider can handle this lookup context.

        Args:
            ctx: Full lookup context (ASIN, path, existing metadata, etc.)
            id_type: Which identifier to use for lookup

        Returns:
            True if provider can attempt lookup with given context
        """
        ...

    async def fetch(self, ctx: LookupContext, id_type: IdType) -> ProviderResult:
        """Fetch metadata from this provider.

        For sync providers (e.g., MediaInfo subprocess), implement as:
            async def fetch(self, ctx, id_type):
                return await asyncio.to_thread(self._fetch_sync, ctx, id_type)

        Args:
            ctx: Full lookup context
            id_type: Which identifier to use for lookup

        Returns:
            ProviderResult with partial canonical fields
        """
        ...
