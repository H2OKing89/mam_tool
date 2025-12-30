"""Tools commands (sub-app).

Commands: tools mamff, tools bbcode
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Annotated

import typer

from mamfast.cli._app import validate_asin_callback
from mamfast.cli._helpers import get_args

logger = logging.getLogger(__name__)


def register_tools_commands(tools_app: typer.Typer) -> None:
    """Register tools commands on the tools sub-app."""

    @tools_app.callback(invoke_without_command=True)
    def tools_callback(ctx: typer.Context) -> None:
        """🔧 Utility tools.

        [bold]Commands:[/]
          mamfast tools mamff    Generate MAM fast-fill JSON
          mamfast tools bbcode   Test HTML to BBCode conversion

        Running [cyan]mamfast tools[/] without a command shows this help.
        """
        if ctx.invoked_subcommand is None:
            from mamfast.console import console

            console.print(ctx.get_help())
            raise typer.Exit(0)

    @tools_app.command("mamff")
    def tools_mamff(
        ctx: typer.Context,
        path: Annotated[
            Path,
            typer.Argument(
                help="Path to release folder or audio file.",
                exists=True,
            ),
        ],
        output: Annotated[
            Path | None,
            typer.Option(
                "--output",
                "-o",
                help="Output JSON path (default: same folder as audio file).",
            ),
        ] = None,
    ) -> None:
        """📝 Generate MAM fast-fill JSON for a release folder.

        Creates the JSON file used by MAM's fast-fill upload feature.
        Fetches metadata from Audnex and extracts info from MediaInfo.

        [bold]Examples:[/]
          mamfast tools mamff /path/to/release/folder
          mamfast tools mamff /path/to/book.m4b
          mamfast tools mamff ./folder --output ./custom.json

        [bold]What it does:[/]
          1. Extracts ASIN from folder/file name
          2. Fetches Audnex metadata (title, author, etc.)
          3. Fetches Audnex chapter data
          4. Runs MediaInfo on the audio file
          5. Generates the MAM JSON with BBCode description
        """
        from mamfast.commands.tools import cmd_tools_mamff

        args = get_args(ctx, path=path, output=output, command="tools-mamff")
        result = cmd_tools_mamff(args)
        raise typer.Exit(result)

    @tools_app.command("bbcode")
    def tools_bbcode(
        ctx: typer.Context,
        asin: Annotated[
            str | None,
            typer.Option(
                "--asin",
                "-a",
                callback=validate_asin_callback,
                help="ASIN to fetch and convert.",
            ),
        ] = None,
        html: Annotated[
            str | None,
            typer.Option("--html", help="Raw HTML to convert to BBCode."),
        ] = None,
    ) -> None:
        """🔤 Test HTML to BBCode conversion.

        Debug tool for testing synopsis HTML to BBCode conversion.

        [bold]Examples:[/]
          mamfast tools bbcode --asin B073PG4DX8
          mamfast tools bbcode --html "<p><b>Bold</b> and <i>italic</i></p>"
        """
        from mamfast.commands.tools import cmd_tools_bbcode

        args = get_args(ctx, asin=asin, html=html)
        result = cmd_tools_bbcode(args)
        raise typer.Exit(result)
