"""Test BBCode signature output matches known working format."""

from __future__ import annotations

# Non-breaking space character
NBSP = "\u00a0"


class TestBBCodeSignature:
    """Test signature BBCode generation."""

    def test_simple_pre_block(self) -> None:
        """Test simple [pre] block - newlines to [br], spaces to nbsp."""
        from shelfr.metadata import _convert_newlines_for_mam

        input_text = "[pre]line 1\nline 2\nline 3[/pre]"
        expected = f"[pre]line{NBSP}1[br]line{NBSP}2[br]line{NBSP}3[/pre]"

        result = _convert_newlines_for_mam(input_text)
        assert result == expected

    def test_mixed_pre_and_regular(self) -> None:
        """Test mixed content - newlines removed outside [pre], converted inside."""
        from shelfr.metadata import _convert_newlines_for_mam

        input_text = "before text\n[pre]in pre\nblock[/pre]\nafter text"
        expected = f"before text[pre]in{NBSP}pre[br]block[/pre]after text"

        result = _convert_newlines_for_mam(input_text)
        assert result == expected

    def test_pre_block_spaces_converted_to_nbsp(self) -> None:
        """Verify that spaces inside [pre] blocks are converted to non-breaking spaces."""
        from shelfr.metadata import _convert_newlines_for_mam

        # Simple case with multiple spaces
        input_text = "[pre]hello    world[/pre]"
        result = _convert_newlines_for_mam(input_text)

        # Should have nbsp, not regular spaces
        assert " " not in result.replace("[pre]", "").replace("[/pre]", "")
        assert NBSP in result
        assert f"hello{NBSP}{NBSP}{NBSP}{NBSP}world" in result

    def test_spaces_outside_pre_preserved(self) -> None:
        """Verify that spaces outside [pre] blocks are NOT converted."""
        from shelfr.metadata import _convert_newlines_for_mam

        input_text = "hello world[pre]in pre[/pre]after text"
        result = _convert_newlines_for_mam(input_text)

        # Regular spaces should remain outside [pre]
        assert "hello world" in result
        assert "after text" in result
        # But inside [pre] should be nbsp
        assert f"in{NBSP}pre" in result

    def test_multiline_ascii_art_banner(self) -> None:
        """Test that complex multiline ASCII art with colors converts correctly.

        This tests a complex banner similar to what would appear in MAM descriptions,
        ensuring newlines become [br] and spaces become nbsp inside [pre] blocks.
        """
        from shelfr.metadata import _convert_newlines_for_mam

        # Test banner (shelfr test suite banner)
        # fmt: off
        # ruff: noqa: E501
        multiline_input = """[center][pre][bold #22C55E]███████╗██╗  ██╗███████╗██╗     ███████╗██████╗      ████████╗███████╗███████╗████████╗[/]
[bold #34D399]██╔════╝██║  ██║██╔════╝██║     ██╔════╝██╔══██╗     ╚══██╔══╝██╔════╝██╔════╝╚══██╔══╝[/]
[bold #6EE7B7]███████╗███████║█████╗  ██║     █████╗  ██████╔╝        ██║   █████╗  ███████╗   ██║   [/]
[bold #A7F3D0]╚════██║██╔══██║██╔══╝  ██║     ██╔══╝  ██╔══██╗        ██║   ██╔══╝  ╚════██║   ██║   [/]
[bold #D1FAE5]███████║██║  ██║███████╗███████╗██║     ██║  ██║        ██║   ███████╗███████║   ██║   [/]
[bold #ECFDF5]╚══════╝╚═╝  ╚═╝╚══════╝╚══════╝╚═╝     ╚═╝  ╚═╝        ╚═╝   ╚══════╝╚══════╝   ╚═╝   [/][/pre]
[bold #06B6D4]Pytest Suite for Audiobookshelf Integration[/][/center]"""
        # fmt: on

        result = _convert_newlines_for_mam(multiline_input)

        # Verify basic transformations occurred
        # 1. Newlines inside [pre] should become [br]
        assert "[br]" in result

        # 2. Spaces inside [pre] should become nbsp
        assert NBSP in result

        # 3. Content outside [pre] (like tagline) should have newlines stripped
        # The tagline line should be directly after the [/pre] close, no newline
        assert "[/pre]\n" not in result

        # 4. The banner text content should be preserved
        assert "███████╗" in result
        assert "SHELFR" not in result  # It's ASCII art, not literal text
        assert "Pytest Suite" in result

    def test_nested_tags_in_pre(self) -> None:
        """Test that nested BBCode tags inside [pre] are preserved."""
        from shelfr.metadata import _convert_newlines_for_mam

        input_text = "[pre][b]bold text[/b]\n[i]italic[/i][/pre]"
        result = _convert_newlines_for_mam(input_text)

        # Tags should be preserved
        assert "[b]bold" in result
        assert "[/b]" in result
        assert "[i]italic[/i]" in result
        # Newline should become [br]
        assert "[br]" in result

    def test_empty_pre_block(self) -> None:
        """Test empty [pre] block handling."""
        from shelfr.metadata import _convert_newlines_for_mam

        input_text = "before[pre][/pre]after"
        result = _convert_newlines_for_mam(input_text)

        assert result == "before[pre][/pre]after"

    def test_multiple_pre_blocks(self) -> None:
        """Test multiple [pre] blocks in same content."""
        from shelfr.metadata import _convert_newlines_for_mam

        input_text = "[pre]block 1\nline 2[/pre]\nmiddle\n[pre]block 2\nline 2[/pre]"
        result = _convert_newlines_for_mam(input_text)

        # Should have two separate [br] conversions
        assert result.count("[br]") == 2
        # Middle newline should be stripped (outside pre)
        assert "middle" in result
        assert "\nmiddle" not in result


if __name__ == "__main__":
    # Quick manual test
    test = TestBBCodeSignature()

    print("Running test_simple_pre_block...")
    test.test_simple_pre_block()
    print("PASSED\n")

    print("Running test_mixed_pre_and_regular...")
    test.test_mixed_pre_and_regular()
    print("PASSED\n")

    print("Running test_pre_block_spaces_converted_to_nbsp...")
    test.test_pre_block_spaces_converted_to_nbsp()
    print("PASSED\n")

    print("Running test_spaces_outside_pre_preserved...")
    test.test_spaces_outside_pre_preserved()
    print("PASSED\n")

    print("Running test_multiline_ascii_art_banner...")
    test.test_multiline_ascii_art_banner()
    print("PASSED\n")

    print("Running test_nested_tags_in_pre...")
    test.test_nested_tags_in_pre()
    print("PASSED\n")

    print("Running test_empty_pre_block...")
    test.test_empty_pre_block()
    print("PASSED\n")

    print("Running test_multiple_pre_blocks...")
    test.test_multiple_pre_blocks()
    print("PASSED\n")

    print("All tests passed!")
