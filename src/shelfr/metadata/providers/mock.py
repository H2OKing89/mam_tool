"""
Mock provider for testing.

MockProvider allows tests to simulate provider behavior without
hitting real APIs or running subprocesses.
"""

from __future__ import annotations

from typing import Any

from .base import ProviderKind
from .types import FieldName, IdType, LookupContext, ProviderResult


class MockProvider:
    """Mock provider for testing the aggregator and registry.

    Configure responses, errors, and behavior for test scenarios.

    Attributes:
        name: Provider name (default: "mock")
        priority: Priority for ordering (default: 50)
        kind: Provider kind (default: "network")
        is_override: Whether provider can set empty values (default: False)

    Example:
        # Simple mock with fixed responses
        mock = MockProvider(
            responses={
                "B08G9PRS1K": {
                    "title": "The Way of Kings",
                    "authors": [{"name": "Brandon Sanderson"}],
                }
            }
        )

        # Mock that fails for certain ASINs
        mock = MockProvider(errors={"BADASIN": "Not found"})

        # Mock with confidence scores
        mock = MockProvider(
            responses={"B08G9PRS1K": {"title": "Book"}},
            confidences={"B08G9PRS1K": {"title": 0.8}},
        )
    """

    def __init__(
        self,
        *,
        name: str = "mock",
        priority: int = 50,
        kind: ProviderKind = "network",
        is_override: bool = False,
        responses: dict[str, dict[FieldName, Any]] | None = None,
        confidences: dict[str, dict[FieldName, float]] | None = None,
        errors: dict[str, str] | None = None,
        supported_id_types: set[IdType] | None = None,
    ):
        """Initialize mock provider.

        Args:
            name: Provider name
            priority: Priority ordering (lower = higher priority)
            kind: Provider kind ("local" or "network")
            is_override: Whether provider can intentionally set empty values
            responses: Mapping of identifier -> fields to return
            confidences: Mapping of identifier -> field confidence scores
            errors: Mapping of identifier -> error message (causes failure)
            supported_id_types: Set of supported ID types (default: {"asin"})
        """
        self.name = name
        self.priority = priority
        self.kind: ProviderKind = kind
        self.is_override = is_override
        self._responses = responses or {}
        self._confidences = confidences or {}
        self._errors = errors or {}
        self._supported_id_types = supported_id_types or {"asin"}
        self._fetch_count = 0
        self._fetch_history: list[tuple[LookupContext, IdType]] = []

    def can_lookup(self, ctx: LookupContext, id_type: IdType) -> bool:
        """Check if mock can handle this lookup.

        Returns True if:
        1. id_type is in supported_id_types
        2. The identifier is in responses or errors
        """
        if id_type not in self._supported_id_types:
            return False
        identifier = ctx.ids.get(id_type)
        if not identifier:
            return False
        return identifier in self._responses or identifier in self._errors

    async def fetch(self, ctx: LookupContext, id_type: IdType) -> ProviderResult:
        """Fetch mock data.

        Returns configured response or error for the identifier.
        """
        self._fetch_count += 1
        self._fetch_history.append((ctx, id_type))

        identifier = ctx.ids.get(id_type)
        if not identifier:
            return ProviderResult.failure(self.name, f"No {id_type} in context")

        # Check for configured error
        if identifier in self._errors:
            return ProviderResult.failure(self.name, self._errors[identifier])

        # Check for configured response
        if identifier in self._responses:
            result = ProviderResult(provider=self.name, success=True)
            fields = self._responses[identifier]
            confidences = self._confidences.get(identifier, {})

            for field_name, value in fields.items():
                confidence = confidences.get(field_name, 1.0)
                result.set_field(field_name, value, confidence)

            return result

        # No configured response - return empty success
        return ProviderResult.empty(self.name)

    @property
    def fetch_count(self) -> int:
        """Number of times fetch() was called."""
        return self._fetch_count

    @property
    def fetch_history(self) -> list[tuple[LookupContext, IdType]]:
        """History of (ctx, id_type) passed to fetch()."""
        return self._fetch_history

    def reset(self) -> None:
        """Reset fetch count and history."""
        self._fetch_count = 0
        self._fetch_history = []

    def set_response(
        self,
        identifier: str,
        fields: dict[FieldName, Any],
        confidences: dict[FieldName, float] | None = None,
    ) -> None:
        """Set response for an identifier.

        Args:
            identifier: ASIN, ISBN, etc.
            fields: Field values to return
            confidences: Optional confidence scores per field
        """
        self._responses[identifier] = fields
        if confidences:
            self._confidences[identifier] = confidences

    def set_error(self, identifier: str, error: str) -> None:
        """Set error response for an identifier.

        Args:
            identifier: ASIN, ISBN, etc.
            error: Error message to return
        """
        self._errors[identifier] = error
