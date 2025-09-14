"""
DRY Refactored dataset management commands for sup CLI.

This is a demonstration of the DRY improvements - shows how clean the commands
become after applying decorators and consolidated output handling.

Compare this to the original dataset.py to see the massive reduction in code duplication.
"""

from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from sup.config.settings import OutputOptions
from sup.decorators import with_output_options, with_universal_filters
from sup.filters.base import UniversalFilters
from sup.filters.dataset import apply_dataset_filters
from sup.output.formatters import display_entity_results
from sup.output.styles import EMOJIS, RICH_STYLES
from sup.output.tables import display_datasets_table

app = typer.Typer(help="Manage datasets", no_args_is_help=True)
console = Console()


@app.command("list")
@with_universal_filters
@with_output_options
def list_datasets(
    filters: UniversalFilters,
    output: OutputOptions,
    # Only dataset-specific filters need to be defined manually
    database_id: Annotated[
        Optional[int],
        typer.Option("--database-id", help="Filter by database ID"),
    ] = None,
    schema: Annotated[
        Optional[str],
        typer.Option("--schema", help="Filter by schema name pattern"),
    ] = None,
    table_type: Annotated[
        Optional[str],
        typer.Option("--table-type", help="Filter by table type (table, view, etc.)"),
    ] = None,
):
    """
    List datasets in the current or specified workspace.

    Notice how clean this function is compared to the original!
    - No 15+ parameter definitions
    - No repeated output handling logic
    - No manual filter parsing

    Examples:
        sup dataset list                                    # All datasets
        sup dataset list --mine                            # My datasets only
        sup dataset list --database-id=1 --porcelain      # Specific DB, machine-readable
        sup dataset list --name="sales*" --json           # Pattern matching, JSON
        sup dataset list --modified-after=2024-01-01      # Recent modifications
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        # Add dataset-specific filters to the universal filters
        dataset_filters = filters.copy(
            update={
                "database_id": database_id,
                "schema": schema,
                "table_type": table_type,
            },
        )

        # Get datasets from API with spinner
        with data_spinner("datasets", silent=output.porcelain) as sp:
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, output.workspace_id)

            # Fetch datasets with pagination
            page = (filters.page - 1) if filters.page else 0
            datasets = client.get_datasets(silent=True, limit=filters.limit, page=page)

            # Apply filters
            filtered_datasets = apply_dataset_filters(datasets, dataset_filters)

            # Update spinner
            if sp:
                if filtered_datasets != datasets:
                    sp.text = (
                        f"Found {len(datasets)} datasets, "
                        f"showing {len(filtered_datasets)} after filtering"
                    )
                else:
                    sp.text = f"Found {len(datasets)} datasets"

        # Use consolidated output handling - no more repeated logic!
        display_entity_results(
            items=filtered_datasets,
            output_format=output.format.value,
            porcelain=output.porcelain,
            porcelain_fields=["id", "table_name", "database_name", "schema", "kind"],
            table_display_func=lambda items: display_datasets_table(
                items, ctx.get_workspace_hostname(),
            ),
        )

    except Exception as e:
        if not output.porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to list datasets: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("info")
@with_output_options
def dataset_info(
    dataset_id: Annotated[int, typer.Argument(help="Dataset ID to inspect")],
    output: OutputOptions,
):
    """
    Show detailed information about a dataset.

    Much cleaner - no repeated output parameter definitions!
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext

    if not output.porcelain:
        console.print(
            f"{EMOJIS['info']} Loading dataset {dataset_id} details...",
            style=RICH_STYLES["info"],
        )

    try:
        ctx = SupContext()
        client = SupSupersetClient.from_context(ctx, output.workspace_id)
        dataset = client.get_dataset(dataset_id, silent=output.porcelain)

        # Consolidated output handling
        if output.porcelain:
            print(
                f"{dataset_id}\t{dataset.get('table_name', '')}\t{dataset.get('database_name', '')}",
            )
        elif output.json_output:
            import json

            print(json.dumps(dataset, indent=2, default=str))
        else:
            from sup.commands.dataset import (
                display_dataset_details,
            )  # Reuse existing function

            display_dataset_details(dataset)

    except Exception as e:
        if not output.porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to get dataset info: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


# Export command would follow the same pattern - much cleaner!
@app.command("export")
@with_universal_filters  # Could add export-specific filters too
@with_output_options
def export_dataset(
    filters: UniversalFilters,
    output: OutputOptions,
    folder: Annotated[
        Optional[str],
        typer.Option("--folder", help="Export folder (default: ./assets/)"),
    ] = None,
    overwrite: Annotated[
        bool,
        typer.Option("--overwrite", help="Overwrite existing files"),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Preview export without writing files"),
    ] = False,
):
    """
    Export dataset(s) to YAML files.

    The decorators automatically provide all the universal filters
    and output options - no need to manually define them!
    """
    console.print(
        f"{EMOJIS['export']} Exporting datasets...",
        style=RICH_STYLES["info"],
    )
    # TODO: Implement dataset export using the filters and output objects
    console.print(
        f"{EMOJIS['warning']} Dataset export not yet implemented",
        style=RICH_STYLES["warning"],
    )
