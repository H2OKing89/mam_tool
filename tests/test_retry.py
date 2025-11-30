"""Tests for retry utilities."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from mamfast.utils.retry import (
    NETWORK_EXCEPTIONS,
    RetryableError,
    retry_with_backoff,
)


class TestRetryWithBackoff:
    """Tests for the retry_with_backoff decorator."""

    def test_success_on_first_try(self) -> None:
        """Function should return immediately on success."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def success_func() -> str:
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()

        assert result == "success"
        assert call_count == 1

    def test_success_after_retry(self) -> None:
        """Function should succeed after retrying."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def fail_then_succeed() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"

        result = fail_then_succeed()

        assert result == "success"
        assert call_count == 3

    def test_fails_after_max_attempts(self) -> None:
        """Function should raise after max attempts exceeded."""
        call_count = 0

        @retry_with_backoff(max_attempts=3, base_delay=0.01)
        def always_fail() -> str:
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Always fails")

        with pytest.raises(ConnectionError, match="Always fails"):
            always_fail()

        assert call_count == 3

    def test_only_catches_specified_exceptions(self) -> None:
        """Should not retry for non-specified exceptions."""
        call_count = 0

        @retry_with_backoff(
            max_attempts=3,
            base_delay=0.01,
            exceptions=(ConnectionError,),
        )
        def raise_value_error() -> str:
            nonlocal call_count
            call_count += 1
            raise ValueError("Not retryable")

        with pytest.raises(ValueError, match="Not retryable"):
            raise_value_error()

        assert call_count == 1  # No retry for ValueError

    def test_exponential_backoff_timing(self) -> None:
        """Verify delays increase exponentially."""
        delays: list[float] = []
        call_count = 0

        def on_retry(exc: Exception, attempt: int, delay: float) -> None:
            delays.append(delay)

        @retry_with_backoff(
            max_attempts=4,
            base_delay=0.1,
            max_delay=10.0,
            exponential_base=2.0,
            jitter=False,  # Disable jitter for predictable timing
            on_retry=on_retry,
        )
        def fail_three_times() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 4:
                raise ConnectionError("Fail")
            return "success"

        result = fail_three_times()

        assert result == "success"
        assert len(delays) == 3
        # Expected: 0.1, 0.2, 0.4 (base * 2^(attempt-1))
        assert abs(delays[0] - 0.1) < 0.01
        assert abs(delays[1] - 0.2) < 0.01
        assert abs(delays[2] - 0.4) < 0.01

    def test_max_delay_cap(self) -> None:
        """Verify delay is capped at max_delay."""
        delays: list[float] = []

        def on_retry(exc: Exception, attempt: int, delay: float) -> None:
            delays.append(delay)

        @retry_with_backoff(
            max_attempts=5,
            base_delay=1.0,
            max_delay=2.0,  # Cap at 2 seconds
            exponential_base=2.0,
            jitter=False,
            on_retry=on_retry,
        )
        def always_fail() -> str:
            raise ConnectionError("Fail")

        with pytest.raises(ConnectionError):
            always_fail()

        # Delays should be: 1.0, 2.0, 2.0, 2.0 (capped)
        assert delays[0] == 1.0
        assert delays[1] == 2.0
        assert delays[2] == 2.0
        assert delays[3] == 2.0

    def test_on_retry_callback(self) -> None:
        """Verify on_retry callback is called with correct args."""
        callback = MagicMock()
        call_count = 0

        @retry_with_backoff(
            max_attempts=3,
            base_delay=0.01,
            jitter=False,
            on_retry=callback,
        )
        def fail_twice() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Network error")
            return "success"

        fail_twice()

        assert callback.call_count == 2
        # Check first call
        first_call = callback.call_args_list[0]
        assert isinstance(first_call[0][0], ConnectionError)
        assert first_call[0][1] == 1  # attempt
        assert first_call[0][2] == pytest.approx(0.01, abs=0.001)  # delay

    def test_preserves_function_metadata(self) -> None:
        """Decorator should preserve function name and docstring."""

        @retry_with_backoff(max_attempts=3)
        def my_function() -> str:
            """My docstring."""
            return "result"

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."

    def test_jitter_adds_randomness(self) -> None:
        """Verify jitter adds randomness to delays."""
        delays: list[float] = []

        def on_retry(exc: Exception, attempt: int, delay: float) -> None:
            delays.append(delay)

        @retry_with_backoff(
            max_attempts=5,
            base_delay=0.01,
            max_delay=0.05,
            jitter=True,
            on_retry=on_retry,
        )
        def always_fail() -> str:
            raise ConnectionError("Fail")

        with pytest.raises(ConnectionError):
            always_fail()

        # With jitter, delays should vary (±25% of base)
        # Check that not all delays are identical
        unique_delays = {round(d, 3) for d in delays}
        assert len(unique_delays) > 1, "Jitter should produce varying delays"


class TestRetryableError:
    """Tests for RetryableError exception."""

    def test_retryable_error_is_caught(self) -> None:
        """RetryableError should be caught by retry decorator."""
        call_count = 0

        @retry_with_backoff(
            max_attempts=3,
            base_delay=0.01,
            exceptions=(RetryableError,),
        )
        def raise_retryable() -> str:
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableError("Retry me")
            return "success"

        result = raise_retryable()

        assert result == "success"
        assert call_count == 3

    def test_retryable_error_preserves_original(self) -> None:
        """RetryableError should preserve original exception."""
        original = ValueError("Original error")
        error = RetryableError("Wrapped", original=original)

        assert error.original is original
        assert str(error) == "Wrapped"


class TestNetworkExceptions:
    """Tests for NETWORK_EXCEPTIONS tuple."""

    def test_contains_base_exceptions(self) -> None:
        """Should contain basic network-related exceptions."""
        assert ConnectionError in NETWORK_EXCEPTIONS
        assert TimeoutError in NETWORK_EXCEPTIONS
        assert OSError in NETWORK_EXCEPTIONS
        assert RetryableError in NETWORK_EXCEPTIONS

    def test_retry_catches_network_exceptions(self) -> None:
        """Retry decorator should catch NETWORK_EXCEPTIONS."""
        call_count = 0

        @retry_with_backoff(
            max_attempts=3,
            base_delay=0.01,
            exceptions=NETWORK_EXCEPTIONS,
        )
        def network_operation() -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ConnectionError("Connection refused")
            if call_count == 2:
                raise TimeoutError("Timed out")
            return "success"

        result = network_operation()

        assert result == "success"
        assert call_count == 3
