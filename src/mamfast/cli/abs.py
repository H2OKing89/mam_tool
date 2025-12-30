"""Audiobookshelf commands.

Commands: abs-init, abs-import, abs-check-duplicate, abs-trump-check,
          abs-restore, abs-cleanup, abs-rename, abs-orphans, abs-resolve-asins
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer

from mamfast.cli._app import (
    ABS_COMMANDS,
    AsinArg,
    CleanupStrategy,
    DuplicatePolicy,
    TrumpAggressiveness,
)
from mamfast.cli._helpers import get_args


def register_abs_commands(app: typer.Typer) -> None:
    """Register Audiobookshelf commands on the app."""

    @app.command("abs-init", rich_help_panel=ABS_COMMANDS)
    def abs_init(ctx: typer.Context) -> None:
        """🔌 Initialize Audiobookshelf connection.

        Tests ABS API connection and discovers available libraries.
        """
        from mamfast.commands import cmd_abs_init

        args = get_args(ctx, command="abs-init")
        result = cmd_abs_init(args)
        raise typer.Exit(result)

    @app.command("abs-import", rich_help_panel=ABS_COMMANDS)
    def abs_import(
        ctx: typer.Context,
        paths: Annotated[
            list[Path] | None,
            typer.Argument(help="Specific folder(s) to import."),
        ] = None,
        duplicate_policy: Annotated[
            DuplicatePolicy | None,
            typer.Option("-d", "--duplicate-policy", help="Duplicate handling policy."),
        ] = None,
        no_scan: Annotated[
            bool,
            typer.Option("--no-scan", help="Don't trigger ABS library scan after import."),
        ] = False,
        no_abs_search: Annotated[
            bool,
            typer.Option("--no-abs-search", help="Disable ABS metadata search for missing ASINs."),
        ] = False,
        confidence: Annotated[
            float | None,
            typer.Option(help="Minimum confidence (0.0-1.0) for ABS search matches."),
        ] = None,
        no_trump: Annotated[
            bool,
            typer.Option("--no-trump", help="Disable trumping for this run."),
        ] = False,
        trump_aggressiveness: Annotated[
            TrumpAggressiveness | None,
            typer.Option(help="Override trumping aggressiveness."),
        ] = None,
        cleanup_strategy: Annotated[
            CleanupStrategy | None,
            typer.Option(help="Override cleanup strategy."),
        ] = None,
        cleanup_path: Annotated[
            Path | None,
            typer.Option(help="Override cleanup path for 'move' strategy."),
        ] = None,
        no_cleanup: Annotated[
            bool,
            typer.Option("--no-cleanup", help="Disable post-import cleanup."),
        ] = False,
        no_metadata: Annotated[
            bool,
            typer.Option("--no-metadata", help="Disable metadata.json generation."),
        ] = False,
    ) -> None:
        """📥 Import staged audiobooks to Audiobookshelf.

        Moves staged books to ABS library structure with duplicate detection.

        [bold]Examples:[/]
          mamfast abs-import                    # Import all staged
          mamfast abs-import /path/to/book      # Import specific folder
          mamfast abs-import -d skip            # Skip duplicates
        """
        from mamfast.commands import cmd_abs_import

        args = get_args(
            ctx,
            paths=paths or [],
            duplicate_policy=duplicate_policy.value if duplicate_policy else None,
            no_scan=no_scan,
            no_abs_search=no_abs_search,
            confidence=confidence,
            no_trump=no_trump,
            trump_aggressiveness=trump_aggressiveness.value if trump_aggressiveness else None,
            cleanup_strategy=cleanup_strategy.value if cleanup_strategy else None,
            cleanup_path=cleanup_path,
            no_cleanup=no_cleanup,
            no_metadata=no_metadata,
            command="abs-import",
        )
        result = cmd_abs_import(args)
        raise typer.Exit(result)

    @app.command("abs-check-duplicate", rich_help_panel=ABS_COMMANDS)
    def abs_check_duplicate(
        ctx: typer.Context,
        asin: Annotated[
            str, typer.Argument(metavar="ASIN", help="ASIN to check (e.g., B0DK27WWT8).")
        ],
    ) -> None:
        """🔍 Check if ASIN exists in library.

        Quick lookup to check for duplicates before importing.

        [bold]Example:[/]
          mamfast abs-check-duplicate B0DK9T5P28
        """
        from mamfast.commands import cmd_abs_check_duplicate

        args = get_args(ctx, asin=asin, command="abs-check-duplicate")
        result = cmd_abs_check_duplicate(args)
        raise typer.Exit(result)

    @app.command("abs-trump-check", rich_help_panel=ABS_COMMANDS)
    def abs_trump_check(
        ctx: typer.Context,
        paths: Annotated[
            list[Path] | None,
            typer.Argument(help="Specific folder(s) to check."),
        ] = None,
        detailed: Annotated[
            bool,
            typer.Option("--detailed", help="Show detailed quality comparison tables."),
        ] = False,
    ) -> None:
        """⚔️  Preview trumping decisions for staged folders.

        Shows what would be replaced, kept, or rejected based on quality comparison.
        """
        from mamfast.commands import cmd_abs_trump_check

        args = get_args(ctx, paths=paths or [], detailed=detailed, command="abs-trump-check")
        result = cmd_abs_trump_check(args)
        raise typer.Exit(result)

    @app.command("abs-restore", rich_help_panel=ABS_COMMANDS)
    def abs_restore(
        ctx: typer.Context,
        archive_path: Annotated[
            Path | None,
            typer.Argument(help="Specific archive folder to restore."),
        ] = None,
        asin: AsinArg = None,
        list_archives: Annotated[
            bool,
            typer.Option("--list", help="List available archives without restoring."),
        ] = False,
    ) -> None:
        """♻️  Restore archived books to library.

        Restore books that were archived by trumping back to the library.

        [bold]Examples:[/]
          mamfast abs-restore --list            # List archives
          mamfast abs-restore -a B0DK9T5P28     # Filter by ASIN
          mamfast abs-restore /path/to/archive  # Restore specific
        """
        from mamfast.commands import cmd_abs_restore

        args = get_args(
            ctx,
            archive_path=archive_path,
            asin=asin,
            list=list_archives,
            command="abs-restore",
        )
        result = cmd_abs_restore(args)
        raise typer.Exit(result)

    @app.command("abs-cleanup", rich_help_panel=ABS_COMMANDS)
    def abs_cleanup(
        ctx: typer.Context,
        paths: Annotated[
            list[Path] | None,
            typer.Argument(help="Specific folder(s) to cleanup."),
        ] = None,
        strategy: Annotated[
            CleanupStrategy | None,
            typer.Option(help="Cleanup strategy."),
        ] = None,
        cleanup_path: Annotated[
            Path | None,
            typer.Option(help="Destination for 'move' strategy."),
        ] = None,
        no_verify_seed: Annotated[
            bool,
            typer.Option(
                "--no-verify-seed",
                help=("[red]DANGEROUS:[/] Skip seed hardlink verification."),
            ),
        ] = False,
        min_age_days: Annotated[
            int | None,
            typer.Option(help="Only cleanup sources older than N days."),
        ] = None,
    ) -> None:
        """🧹 Cleanup Libation source files after import.

        Standalone cleanup of Libation source folders that have been imported.
        Supports strategies: hide (add marker), move, or delete.
        """
        from mamfast.commands import cmd_abs_cleanup

        args = get_args(
            ctx,
            paths=paths or [],
            strategy=strategy.value if strategy else None,
            cleanup_path=cleanup_path,
            no_verify_seed=no_verify_seed,
            min_age_days=min_age_days,
            command="abs-cleanup",
        )
        result = cmd_abs_cleanup(args)
        raise typer.Exit(result)

    @app.command("abs-rename", rich_help_panel=ABS_COMMANDS)
    def abs_rename(
        ctx: typer.Context,
        source: Annotated[
            Path | None,
            typer.Option(help="Directory to scan (default: ABS library from config)."),
        ] = None,
        pattern: Annotated[
            str,
            typer.Option(help="Glob pattern to filter folders."),
        ] = "*",
        fetch_metadata: Annotated[
            bool,
            typer.Option("--fetch-metadata", help="Fetch missing metadata from Audnex API."),
        ] = False,
        abs_search: Annotated[
            bool,
            typer.Option("--abs-search", help="Use ABS Audible search for ASIN resolution."),
        ] = False,
        abs_search_confidence: Annotated[
            float,
            typer.Option(help="Minimum confidence for ABS search matches."),
        ] = 0.75,
        interactive: Annotated[
            bool,
            typer.Option("--interactive", help="Prompt for confirmation on each rename."),
        ] = False,
        force: Annotated[
            bool,
            typer.Option("--force", help="Rename files even when folder names are correct."),
        ] = False,
        report: Annotated[
            Path | None,
            typer.Option(help="Output JSON report of changes to file."),
        ] = None,
    ) -> None:
        """✏️  Rename folders to match MAM naming schema.

        Normalizes folder names in your Audiobookshelf library to follow
        the MAM naming convention for consistency.
        """
        from mamfast.commands import cmd_abs_rename

        args = get_args(
            ctx,
            source=source,
            pattern=pattern,
            fetch_metadata=fetch_metadata,
            abs_search=abs_search,
            abs_search_confidence=abs_search_confidence,
            interactive=interactive,
            force=force,
            report=report,
            command="abs-rename",
        )
        result = cmd_abs_rename(args)
        raise typer.Exit(result)

    @app.command("abs-orphans", rich_help_panel=ABS_COMMANDS)
    def abs_orphans(
        ctx: typer.Context,
        source: Annotated[
            Path | None,
            typer.Option(help="Directory to scan (default: ABS library from config)."),
        ] = None,
        cleanup: Annotated[
            bool,
            typer.Option("--cleanup", help="Remove orphaned folders (with matching audio folder)."),
        ] = False,
        cleanup_all: Annotated[
            bool,
            typer.Option("--cleanup-all", help="[red]DANGEROUS:[/] Remove ALL orphaned folders."),
        ] = False,
        min_match_score: Annotated[
            float,
            typer.Option(help="Minimum similarity score to consider a match."),
        ] = 0.5,
        report: Annotated[
            Path | None,
            typer.Option(help="Output JSON report of orphaned folders."),
        ] = None,
    ) -> None:
        """🔎 Find and clean up orphaned folders.

        Finds orphaned folders that have metadata.json but no audio files.
        These are often created by ABS when it creates duplicate library entries.
        """
        from mamfast.commands import cmd_abs_orphans

        args = get_args(
            ctx,
            source=source,
            cleanup=cleanup,
            cleanup_all=cleanup_all,
            min_match_score=min_match_score,
            report=report,
            command="abs-orphans",
        )
        result = cmd_abs_orphans(args)
        raise typer.Exit(result)

    @app.command("abs-resolve-asins", rich_help_panel=ABS_COMMANDS)
    def abs_resolve_asins(
        ctx: typer.Context,
        path: Annotated[
            Path | None,
            typer.Option(help="Specific folder to resolve (default: scan Unknown/)."),
        ] = None,
        confidence: Annotated[
            float,
            typer.Option(help="Minimum confidence threshold (0-1)."),
        ] = 0.75,
        write_sidecar: Annotated[
            bool,
            typer.Option("--write-sidecar", help="Write resolved ASINs to sidecar JSON files."),
        ] = False,
    ) -> None:
        """🔍 Resolve ASINs for Unknown/ books via ABS search.

        Searches Audible via ABS to find ASINs for books in Unknown/.
        """
        from mamfast.commands import cmd_abs_resolve_asins

        args = get_args(
            ctx,
            path=path,
            confidence=confidence,
            write_sidecar=write_sidecar,
            command="abs-resolve-asins",
        )
        result = cmd_abs_resolve_asins(args)
        raise typer.Exit(result)

    # Command alias
    app.command("abs-dup", hidden=True)(abs_check_duplicate)
