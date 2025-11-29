"""Tests for libation module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from mamfast.libation import (
    ScanResult,
    check_container_running,
    run_liberate,
    run_scan,
)


class TestScanResult:
    """Tests for ScanResult dataclass."""

    def test_success_when_returncode_zero(self):
        """Test success property is True when returncode is 0."""
        result = ScanResult(returncode=0, stdout="OK")
        assert result.success is True

    def test_failure_when_returncode_nonzero(self):
        """Test success property is False when returncode is non-zero."""
        result = ScanResult(returncode=1, stderr="Error")
        assert result.success is False


class TestCheckContainerRunning:
    """Tests for check_container_running function."""

    def test_container_running(self):
        """Test detecting running container."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "true\n"

        mock_settings = MagicMock()
        mock_settings.docker_bin = "/usr/bin/docker"
        mock_settings.libation_container = "Libation"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("mamfast.libation.get_settings", return_value=mock_settings),
        ):
            assert check_container_running() is True

    def test_container_not_running(self):
        """Test detecting stopped container."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "false\n"

        mock_settings = MagicMock()
        mock_settings.docker_bin = "/usr/bin/docker"
        mock_settings.libation_container = "Libation"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("mamfast.libation.get_settings", return_value=mock_settings),
        ):
            assert check_container_running() is False

    def test_docker_command_fails(self):
        """Test handling docker command failure."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""

        mock_settings = MagicMock()
        mock_settings.docker_bin = "/usr/bin/docker"
        mock_settings.libation_container = "Libation"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("mamfast.libation.get_settings", return_value=mock_settings),
        ):
            assert check_container_running() is False

    def test_exception_returns_false(self):
        """Test that exceptions return False."""
        mock_settings = MagicMock()
        mock_settings.docker_bin = "/usr/bin/docker"
        mock_settings.libation_container = "Libation"

        with (
            patch("subprocess.run", side_effect=OSError("Docker not found")),
            patch("mamfast.libation.get_settings", return_value=mock_settings),
        ):
            assert check_container_running() is False


class TestRunScan:
    """Tests for run_scan function."""

    def test_scan_success(self):
        """Test successful scan."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Scanned 5 books"
        mock_result.stderr = ""

        mock_settings = MagicMock()
        mock_settings.libation_container = "Libation"
        mock_settings.docker_bin = "/usr/bin/docker"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("mamfast.libation.get_settings", return_value=mock_settings),
        ):
            result = run_scan()
            assert result.success is True
            assert result.returncode == 0

    def test_scan_failure(self):
        """Test failed scan."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error"

        mock_settings = MagicMock()
        mock_settings.libation_container = "Libation"
        mock_settings.docker_bin = "/usr/bin/docker"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("mamfast.libation.get_settings", return_value=mock_settings),
        ):
            result = run_scan()
            assert result.success is False

    def test_scan_docker_not_found(self):
        """Test scan when docker binary is missing."""
        mock_settings = MagicMock()
        mock_settings.docker_bin = "/nonexistent/docker"
        mock_settings.libation_container = "Libation"

        with (
            patch("subprocess.run", side_effect=FileNotFoundError),
            patch("mamfast.libation.get_settings", return_value=mock_settings),
        ):
            result = run_scan()
            assert result.success is False
            assert result.returncode == -1


class TestRunLiberate:
    """Tests for run_liberate function."""

    def test_liberate_success(self):
        """Test successful liberate."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Downloaded 3 books"
        mock_result.stderr = ""

        mock_settings = MagicMock()
        mock_settings.libation_container = "Libation"
        mock_settings.docker_bin = "/usr/bin/docker"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("mamfast.libation.get_settings", return_value=mock_settings),
        ):
            result = run_liberate()
            assert result.success is True

    def test_liberate_with_asin(self):
        """Test liberate with specific ASIN."""
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Downloaded 1 book"
        mock_result.stderr = ""

        mock_settings = MagicMock()
        mock_settings.libation_container = "Libation"
        mock_settings.docker_bin = "/usr/bin/docker"

        with (
            patch("subprocess.run", return_value=mock_result) as mock_run,
            patch("mamfast.libation.get_settings", return_value=mock_settings),
        ):
            result = run_liberate(asin="B01234567X")
            assert result.success is True
            # Verify ASIN was passed to command
            call_args = mock_run.call_args[0][0]
            assert "B01234567X" in call_args

    def test_liberate_failure(self):
        """Test failed liberate."""
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stdout = ""
        mock_result.stderr = "Error downloading"

        mock_settings = MagicMock()
        mock_settings.libation_container = "Libation"
        mock_settings.docker_bin = "/usr/bin/docker"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("mamfast.libation.get_settings", return_value=mock_settings),
        ):
            result = run_liberate()
            assert result.success is False

    def test_liberate_exception(self):
        """Test liberate when exception occurs."""
        mock_settings = MagicMock()
        mock_settings.libation_container = "Libation"
        mock_settings.docker_bin = "/usr/bin/docker"

        with (
            patch("subprocess.run", side_effect=RuntimeError("Unexpected error")),
            patch("mamfast.libation.get_settings", return_value=mock_settings),
        ):
            result = run_liberate()
            assert result.success is False
            assert result.returncode == -1
            assert "Unexpected error" in result.stderr


class TestRunScanInteractive:
    """Tests for run_scan interactive mode."""

    def test_scan_interactive_success(self):
        """Test successful interactive scan."""
        mock_result = MagicMock()
        mock_result.returncode = 0

        mock_settings = MagicMock()
        mock_settings.libation_container = "Libation"
        mock_settings.docker_bin = "/usr/bin/docker"

        with (
            patch("subprocess.run", return_value=mock_result) as mock_run,
            patch("mamfast.libation.get_settings", return_value=mock_settings),
        ):
            result = run_scan(interactive=True)
            assert result.success is True
            # Verify -it flag is passed
            call_args = mock_run.call_args[0][0]
            assert "-it" in call_args

    def test_scan_interactive_failure(self):
        """Test failed interactive scan."""
        mock_result = MagicMock()
        mock_result.returncode = 1

        mock_settings = MagicMock()
        mock_settings.libation_container = "Libation"
        mock_settings.docker_bin = "/usr/bin/docker"

        with (
            patch("subprocess.run", return_value=mock_result),
            patch("mamfast.libation.get_settings", return_value=mock_settings),
        ):
            result = run_scan(interactive=True)
            assert result.success is False

    def test_scan_exception_generic(self):
        """Test scan with generic exception."""
        mock_settings = MagicMock()
        mock_settings.libation_container = "Libation"
        mock_settings.docker_bin = "/usr/bin/docker"

        with (
            patch("subprocess.run", side_effect=RuntimeError("Docker crash")),
            patch("mamfast.libation.get_settings", return_value=mock_settings),
        ):
            result = run_scan()
            assert result.success is False
            assert result.returncode == -1
            assert "Docker crash" in result.stderr
