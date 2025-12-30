"""Core pipeline commands.

Commands: scan, discover, prepare, metadata, torrent, upload, run, status, config
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from mamfast.cli._app import CORE_COMMANDS, AsinArg
from mamfast.cli._helpers import get_args


def register_core_commands(app: typer.Typer) -> None:
    """Register core pipeline commands on the app."""

    @app.command(rich_help_panel=CORE_COMMANDS)
    def scan(
        ctx: typer.Context,
        liberate: Annotated[
            bool,
            typer.Option(
                "--liberate",
                help="Also download new books after scanning.",
            ),
        ] = False,
    ) -> None:
        """🔍 Scan Audible library for new audiobooks.

        Runs libationcli scan in the Libation Docker container to check
        for new purchases in your Audible library.

        [bold]Examples:[/]
          mamfast scan              # Just scan for new books
          mamfast scan --liberate   # Scan and download new books
        """
        from mamfast.commands import cmd_scan

        args = get_args(ctx, liberate=liberate, command="scan")
        result = cmd_scan(args)
        raise typer.Exit(result)

    @app.command(rich_help_panel=CORE_COMMANDS)
    def discover(
        ctx: typer.Context,
        all_books: Annotated[
            bool,
            typer.Option(
                "--all",
                help="Show all audiobooks, not just unprocessed.",
            ),
        ] = False,
    ) -> None:
        """📖 List new audiobooks found in Libation library.

        Discovers unprocessed audiobooks that are ready to be staged
        for upload to MAM.

        [bold]Examples:[/]
          mamfast discover       # Show unprocessed books
          mamfast discover --all # Show all books

        [dim]Tip: Scans Libation output directory for new audiobooks.[/]
        """
        from mamfast.commands import cmd_discover

        args = get_args(ctx, all=all_books, command="discover")
        result = cmd_discover(args)
        raise typer.Exit(result)

    @app.command(rich_help_panel=CORE_COMMANDS)
    def prepare(
        ctx: typer.Context,
        asin: AsinArg = None,
        dry_run_hint: Annotated[
            bool,
            typer.Option("--dry-run", hidden=True),
        ] = False,
    ) -> None:
        """📦 Stage audiobooks for upload.

        Creates hardlinks and renames files to MAM-compliant naming format
        in the staging directory.

        [bold]Examples:[/]
          mamfast prepare              # Prepare all discovered books
          mamfast prepare -a B0DK9T5P28  # Prepare specific book

        [dim]Tip: Stages release for upload by hardlinking files and validating structure.[/]
        """
        from mamfast.console import console

        if dry_run_hint:
            console.print(
                "[yellow]⚠️  --dry-run must come BEFORE the subcommand:[/]\n\n"
                "    [green]mamfast --dry-run prepare[/]  ✓\n"
                "    [red]mamfast prepare --dry-run[/]  ✗\n"
            )
            raise typer.Exit(2)

        from mamfast.commands import cmd_prepare

        args = get_args(ctx, asin=asin, command="prepare")
        result = cmd_prepare(args)
        raise typer.Exit(result)

    @app.command(rich_help_panel=CORE_COMMANDS)
    def metadata(
        ctx: typer.Context,
        path: Annotated[
            Path | None,
            typer.Argument(help="Path to specific audiobook directory."),
        ] = None,
        asin: AsinArg = None,
    ) -> None:
        """📋 Fetch metadata for staged releases.

        Retrieves metadata from Audnex API and MediaInfo for staged
        audiobook releases.

        [bold]Examples:[/]
          mamfast metadata                    # All staged releases
          mamfast metadata -a B0DK9T5P28      # Specific ASIN
          mamfast metadata /path/to/audiobook # Specific path

        [dim]Tip: Fetches from Audnex API and extracts MediaInfo from audio files.[/]
        """
        from mamfast.commands import cmd_metadata

        args = get_args(ctx, path=path, asin=asin, command="metadata")
        result = cmd_metadata(args)
        raise typer.Exit(result)

    @app.command(rich_help_panel=CORE_COMMANDS)
    def torrent(
        ctx: typer.Context,
        path: Annotated[
            Path | None,
            typer.Argument(help="Path to specific audiobook directory."),
        ] = None,
        preset: Annotated[
            str | None,
            typer.Option(help="Override mkbrr preset (default from config)."),
        ] = None,
        asin: AsinArg = None,
    ) -> None:
        """🧲 Create .torrent files for staged releases.

        Uses mkbrr in Docker to create .torrent files for upload.

        [bold]Examples:[/]
          mamfast torrent                     # All staged releases
          mamfast torrent -a B0DK9T5P28       # Specific ASIN
          mamfast torrent --preset custom     # Use custom preset

        [dim]Tip: Creates .torrent file using mkbrr in Docker container.[/]
        """
        from mamfast.commands import cmd_torrent

        args = get_args(ctx, path=path, preset=preset, asin=asin, command="torrent")
        result = cmd_torrent(args)
        raise typer.Exit(result)

    @app.command(rich_help_panel=CORE_COMMANDS)
    def upload(
        ctx: typer.Context,
        paused: Annotated[
            bool,
            typer.Option(help="Add torrents in paused state."),
        ] = False,
        dry_run_hint: Annotated[
            bool,
            typer.Option("--dry-run", hidden=True),
        ] = False,
    ) -> None:
        """⬆️  Upload .torrent files to qBittorrent.

        Adds created torrent files to qBittorrent for seeding.

        [bold]Examples:[/]
          mamfast upload           # Upload all ready torrents
          mamfast upload --paused  # Upload but don't start seeding

        [dim]Tip: Submits torrent and metadata to MAM tracker.[/]
        """
        from mamfast.console import console

        if dry_run_hint:
            console.print(
                "[yellow]⚠️  --dry-run must come BEFORE the subcommand:[/]\n\n"
                "    [green]mamfast --dry-run upload[/]  ✓\n"
                "    [red]mamfast upload --dry-run[/]  ✗\n"
            )
            raise typer.Exit(2)

        from mamfast.commands import cmd_upload

        args = get_args(ctx, paused=paused, command="upload")
        result = cmd_upload(args)
        raise typer.Exit(result)

    @app.command(rich_help_panel=CORE_COMMANDS)
    def run(
        ctx: typer.Context,
        skip_scan: Annotated[
            bool,
            typer.Option("--skip-scan", help="Skip Libation scan step."),
        ] = False,
        skip_metadata: Annotated[
            bool,
            typer.Option("--skip-metadata", help="Skip metadata fetching step."),
        ] = False,
        no_run_lock: Annotated[
            bool,
            typer.Option(
                "--no-run-lock",
                help="[red]DANGEROUS:[/] Bypass run lock (can cause data corruption).",
            ),
        ] = False,
        dry_run_hint: Annotated[
            bool,
            typer.Option(
                "--dry-run",
                hidden=True,
                help="(Use 'mamfast --dry-run run' instead)",
            ),
        ] = False,
    ) -> None:
        """🚀 Run the full upload pipeline.

        Executes all steps: [cyan]scan → discover → prepare → metadata → torrent → upload[/]

        [bold]Examples:[/]
          mamfast run               # Full pipeline
          mamfast --dry-run run     # Preview without changes
          mamfast run --skip-scan   # Skip Libation scan
        """
        from mamfast.console import console

        # Handle misplaced --dry-run flag
        if dry_run_hint:
            console.print(
                "[yellow]⚠️  --dry-run must come BEFORE the subcommand:[/]\n\n"
                "    [green]mamfast --dry-run run[/]  ✓\n"
                "    [red]mamfast run --dry-run[/]  ✗\n"
            )
            raise typer.Exit(2)

        from mamfast.commands import cmd_run

        args = get_args(
            ctx,
            skip_scan=skip_scan,
            skip_metadata=skip_metadata,
            no_run_lock=no_run_lock,
            command="run",
        )
        result = cmd_run(args)
        raise typer.Exit(result)

    @app.command(rich_help_panel=CORE_COMMANDS)
    def status(ctx: typer.Context) -> None:
        """📊 Show processing status of all releases.

        Displays a summary of discovered, staged, and processed releases.
        """
        from mamfast.commands import cmd_status

        args = get_args(ctx, command="status")
        result = cmd_status(args)
        raise typer.Exit(result)

    @app.command(rich_help_panel=CORE_COMMANDS)
    def config(ctx: typer.Context) -> None:
        """⚙️  Print loaded configuration.

        Shows the current configuration values for debugging.
        """
        from mamfast.commands import cmd_config

        args = get_args(ctx, command="config")
        result = cmd_config(args)
        raise typer.Exit(result)
