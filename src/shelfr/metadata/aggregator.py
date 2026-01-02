"""
Metadata aggregator for merging results from multiple providers.

The aggregator fetches from multiple providers and merges results into
a single canonical metadata object using deterministic conflict resolution.

Key features:
- Two-stage fetch: local providers first, then network (if needed)
- Deterministic merge: confidence → priority → quality
- Error isolation: one provider failure doesn't nuke the batch
- Override support: abs_sidecar/private_db can intentionally clear fields
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, get_args

from .providers.base import MetadataProvider
from .providers.registry import ProviderRegistry, default_registry
from .providers.types import FieldName, IdType, LookupContext, ProviderResult

logger = logging.getLogger(__name__)

# Runtime set of all canonical fields (from Literal type)
ALL_FIELDS: set[FieldName] = set(get_args(FieldName))


@dataclass
class FieldConflict:
    """Record of a field conflict between providers.

    Attributes:
        field: Canonical field name
        values: Mapping of provider name to value
        resolved_value: Final value after resolution
        resolution_reason: Why this value won ("priority", "confidence", "quality")
    """

    field: FieldName
    values: dict[str, Any]
    resolved_value: Any
    resolution_reason: str


@dataclass
class AggregatedResult:
    """Aggregated metadata from multiple providers.

    Attributes:
        fields: Merged field values
        sources: Field -> provider that provided it
        conflicts: Fields where providers disagreed
        missing: Fields no provider had
        errors: Provider -> error message for failed fetches
    """

    fields: dict[FieldName, Any] = field(default_factory=dict)
    sources: dict[FieldName, str] = field(default_factory=dict)
    conflicts: list[FieldConflict] = field(default_factory=list)
    missing: list[FieldName] = field(default_factory=list)
    errors: dict[str, str] = field(default_factory=dict)


class MetadataAggregator:
    """Aggregate metadata from multiple providers with conflict resolution.

    Merge strategy tie-breaker order (deterministic, no randomness):
    1. Higher confidence score
    2. Lower provider priority (more trusted)
    3. Value quality heuristic (non-empty > empty, longer summary > shorter)

    Note: Some fields use custom merge semantics:
    - genres: union + dedupe (combine from all providers)
    - authors/narrators: prefer single provider (don't merge partial lists)

    Example:
        registry = ProviderRegistry()
        registry.register(AudnexProvider())
        registry.register(MediaInfoProvider())

        aggregator = MetadataAggregator(registry)
        ctx = LookupContext.from_asin(asin="B08G9PRS1K", path=book_path)
        result = await aggregator.fetch_all(ctx)

        print(f"Title: {result.fields.get('title')}")
        print(f"From: {result.sources.get('title')}")
    """

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        merge_strategy: str = "confidence",
    ):
        """Initialize aggregator.

        Args:
            registry: Provider registry (defaults to global default_registry)
            merge_strategy: How to resolve conflicts
                - "priority": Use highest-priority provider's value
                - "confidence": Use highest-confidence value per field
        """
        self.registry = registry or default_registry
        self.merge_strategy = merge_strategy

    async def fetch_all(
        self,
        ctx: LookupContext,
        id_type: IdType = "asin",
        *,
        providers: list[str] | None = None,
        stop_on_complete: bool = True,
        required_fields: list[FieldName] | None = None,
    ) -> AggregatedResult:
        """Fetch from multiple providers and merge results.

        Two-stage fetch when stop_on_complete=True:
        1. Run local providers first (cheap, parallelized)
        2. Run network providers only if required_fields still missing

        Args:
            ctx: Lookup context with identifiers and paths
            id_type: Identifier type to use for lookup (default: "asin")
            providers: Optional list of provider names to use (all if None)
            stop_on_complete: If True, skip network calls when required_fields filled
            required_fields: Fields that must be filled (default: ["title"])

        Returns:
            AggregatedResult with merged fields and metadata
        """
        required = set(required_fields or ["title"])

        # Get applicable providers
        if providers:
            provider_list = [p for name in providers if (p := self.registry.get(name)) is not None]
        else:
            provider_list = self.registry.get_for_context(ctx, id_type)

        if not provider_list:
            logger.warning("No providers available for context: %s", ctx)
            return AggregatedResult(missing=list(ALL_FIELDS))

        # Build provider lookup for is_override check
        provider_map = {p.name: p for p in provider_list}

        # Split by kind (not hardcoded names)
        local_providers = [p for p in provider_list if p.kind == "local"]
        network_providers = [p for p in provider_list if p.kind == "network"]

        results: list[ProviderResult] = []
        errors: dict[str, str] = {}

        # Stage 1: Run local providers (cheap, parallelized)
        if local_providers:
            logger.debug("Stage 1: fetching from %d local providers", len(local_providers))
            stage1 = await asyncio.gather(
                *(self._safe_fetch(p, ctx, id_type) for p in local_providers)
            )
            for result in stage1:
                if result.success:
                    results.append(result)
                elif result.error:
                    errors[result.provider] = result.error

        # Check if we can skip network calls
        if stop_on_complete and required:
            filled = self._get_filled_fields(results, provider_map)
            if required.issubset(filled):
                logger.debug("Required fields filled by local providers, skipping network")
                return self._merge(results, provider_map, errors)

        # Stage 2: Run network providers (sequential to be nice to APIs)
        if network_providers:
            logger.debug("Stage 2: fetching from %d network providers", len(network_providers))
            for provider in network_providers:
                result = await self._safe_fetch(provider, ctx, id_type)
                if result.success:
                    results.append(result)
                elif result.error:
                    errors[result.provider] = result.error

                # Early exit if required fields now filled
                if stop_on_complete and required:
                    filled = self._get_filled_fields(results, provider_map)
                    if required.issubset(filled):
                        logger.debug("Required fields filled, stopping early")
                        break

        return self._merge(results, provider_map, errors)

    async def _safe_fetch(
        self,
        provider: MetadataProvider,
        ctx: LookupContext,
        id_type: IdType,
    ) -> ProviderResult:
        """Fetch with error handling - one provider failure doesn't nuke the batch."""
        try:
            return await provider.fetch(ctx, id_type)
        except Exception as e:
            logger.warning("Provider %s failed: %s", provider.name, e)
            return ProviderResult.failure(provider.name, str(e))

    def _merge(
        self,
        results: list[ProviderResult],
        provider_map: dict[str, MetadataProvider],
        errors: dict[str, str],
    ) -> AggregatedResult:
        """Merge multiple provider results.

        Core rules:
        - Skip success=False results
        - Skip empty values (unless from override provider)
        - Use merge strategy for conflicts
        """
        aggregated = AggregatedResult(errors=errors)

        # Collect candidates per field: field -> [(provider, value, confidence, priority)]
        candidates: dict[FieldName, list[tuple[str, Any, float, int]]] = {}

        for result in results:
            if not result.success:
                continue

            provider = provider_map.get(result.provider)
            if not provider:
                continue

            for field_name, value in result.fields.items():
                # Skip empty unless override provider
                if self._should_skip_empty(provider, value):
                    continue

                confidence = result.confidence.get(field_name, 1.0)
                if field_name not in candidates:
                    candidates[field_name] = []
                candidates[field_name].append(
                    (result.provider, value, confidence, provider.priority)
                )

        # Resolve each field
        for field_name, field_candidates in candidates.items():
            if len(field_candidates) == 1:
                # No conflict - just use the value
                provider_name, value, _, _ = field_candidates[0]
                aggregated.fields[field_name] = value
                aggregated.sources[field_name] = provider_name
            else:
                # Conflict - resolve using strategy
                resolved, reason = self._resolve_conflict(field_name, field_candidates)
                aggregated.fields[field_name] = resolved

                # Find which provider provided the resolved value
                for provider_name, value, _, _ in field_candidates:
                    if value == resolved:
                        aggregated.sources[field_name] = provider_name
                        break

                # Record conflict
                conflict = FieldConflict(
                    field=field_name,
                    values={p: v for p, v, _, _ in field_candidates},
                    resolved_value=resolved,
                    resolution_reason=reason,
                )
                aggregated.conflicts.append(conflict)

        # Track missing fields
        aggregated.missing = [f for f in ALL_FIELDS if f not in aggregated.fields]

        return aggregated

    def _get_filled_fields(
        self,
        results: list[ProviderResult],
        provider_map: dict[str, MetadataProvider],
    ) -> set[FieldName]:
        """Get all fields that have non-empty values."""
        filled: set[FieldName] = set()
        for result in results:
            if not result.success:
                continue
            provider = provider_map.get(result.provider)
            for field_name, value in result.fields.items():
                if provider and provider.is_override:
                    # Override providers count even for empty
                    filled.add(field_name)
                elif not self._is_empty(value):
                    filled.add(field_name)
        return filled

    def _is_empty(self, value: Any) -> bool:
        """Check if a value is considered empty."""
        return value is None or value == "" or value == []

    def _should_skip_empty(self, provider: MetadataProvider, value: Any) -> bool:
        """Check if an empty value should be skipped.

        Override providers (is_override=True) can set empty values
        intentionally - user wants to clear a field.
        """
        if provider.is_override:
            return False
        return self._is_empty(value)

    def _resolve_conflict(
        self,
        field_name: FieldName,
        candidates: list[tuple[str, Any, float, int]],
    ) -> tuple[Any, str]:
        """Resolve a field conflict using deterministic tie-breakers.

        Args:
            field_name: Canonical field name
            candidates: List of (provider, value, confidence, priority)

        Returns:
            (resolved_value, resolution_reason)
        """
        if self.merge_strategy == "priority":
            # Lowest priority number wins
            candidates.sort(key=lambda x: (x[3], x[0]))  # priority, then name
            return candidates[0][1], "priority"

        # Confidence strategy with full tie-breaker chain
        # Sort by: max(confidence), min(priority), max(quality), name
        scored = []
        for provider, value, confidence, priority in candidates:
            quality = self._value_quality(field_name, value)
            scored.append((provider, value, confidence, priority, quality))

        # Sort: highest confidence, lowest priority, highest quality, alpha name
        scored.sort(key=lambda x: (-x[2], x[3], -x[4], x[0]))
        winner = scored[0]

        # Determine what broke the tie
        if len(scored) > 1:
            second = scored[1]
            if winner[2] != second[2]:
                reason = "confidence"
            elif winner[3] != second[3]:
                reason = "priority"
            else:
                reason = "quality"
        else:
            reason = "confidence"

        return winner[1], reason

    def _value_quality(self, field_name: FieldName, value: Any) -> int:
        """Compute quality score for a value (higher = better).

        Used as tie-breaker when confidence and priority are equal.
        """
        if value is None:
            return 0
        if isinstance(value, str):
            # Longer strings are generally better for descriptions
            return len(value)
        if isinstance(value, list):
            # More items = more data
            return len(value)
        # Default: non-empty is better than empty
        return 1
