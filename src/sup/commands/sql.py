"""
SQL execution commands for sup CLI.

The crown jewel of the sup experience - making SQL queries beautiful and easy.
"""

from typing import Optional

import typer
from rich.console import Console
from typing_extensions import Annotated

from sup.output.styles import EMOJIS, RICH_STYLES

console = Console()


def execute_sql_query(
    query: str,
    workspace_id: Optional[int] = None,
    database_id: Optional[int] = None,
    json_output: bool = False,
    csv_output: bool = False,
    yaml_output: bool = False,
    porcelain: bool = False,
    limit: int = 1000,
    max_display_rows: int = 100,
) -> None:
    """Execute a SQL query - DRY function for reuse."""
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.formatters import (
        QueryResult,
        QueryTimer,
        display_query_results,
    )

    # Get context and resolve IDs
    ctx = SupContext()
    final_workspace_id = ctx.get_workspace_id(workspace_id)
    final_database_id = ctx.get_database_id(database_id)

    if not final_workspace_id:
        console.print(
            f"{EMOJIS['error']} No workspace configured",
            style=RICH_STYLES["error"],
        )
        console.print(
            "💡 Run [bold]sup workspace list[/] and [bold]sup workspace use <ID>[/]",
            style=RICH_STYLES["info"],
        )
        raise typer.Exit(1)

    if not final_database_id:
        console.print(
            f"{EMOJIS['error']} No database configured",
            style=RICH_STYLES["error"],
        )
        console.print(
            "💡 Run [bold]sup database list[/] and [bold]sup database use <ID>[/]",
            style=RICH_STYLES["info"],
        )
        raise typer.Exit(1)

    # Execute query with spinner
    from sup.output.spinners import query_spinner

    with query_spinner(query, silent=porcelain) as sp:
        # Create Superset client and execute query
        client = SupSupersetClient.from_context(ctx, final_workspace_id)

        with QueryTimer() as timer:
            df = client.client.run_query(final_database_id, query, limit=limit)

        # Update spinner with execution time
        if sp:
            sp.text = f"Query executed in {timer.execution_time:.2f}s"

    # Determine output format
    output_format = "table"  # default
    if json_output:
        output_format = "json"
    elif csv_output:
        output_format = "csv"
    elif yaml_output:
        output_format = "yaml"

    # Create result object and display
    result = QueryResult(
        data=df,
        query=query,
        execution_time=timer.execution_time,
        database_id=final_database_id,
    )

    display_query_results(result, output_format, max_display_rows, porcelain=porcelain)


def sql_command(
    query: Annotated[Optional[str], typer.Argument(help="SQL query to execute")] = None,
    interactive: Annotated[
        bool,
        typer.Option("--interactive", "-i", help="Start interactive SQL session"),
    ] = False,
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Workspace ID"),
    ] = None,
    database_id: Annotated[
        Optional[int],
        typer.Option("--database-id", "-d", help="Database ID"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", help="Output as JSON")] = False,
    csv_output: Annotated[bool, typer.Option("--csv", help="Output as CSV")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", help="Output as YAML")] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output (no decorations)"),
    ] = False,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum rows to fetch"),
    ] = 1000,
    max_display_rows: Annotated[
        int,
        typer.Option("--max-rows", help="Maximum rows to display"),
    ] = 100,
):
    """
    Execute SQL queries against your databases.

    Examples:
        sup sql "SELECT COUNT(*) FROM users"
        sup sql "SELECT * FROM sales LIMIT 10" --json
        sup sql --interactive
        sup sql -i
    """
    if interactive or query is None:
        # Start interactive mode
        console.print(
            f"{EMOJIS['rocket']} Starting interactive SQL session...",
            style=RICH_STYLES["brand"],
        )
        console.print(
            f"{EMOJIS['warning']} Interactive mode not yet implemented",
            style=RICH_STYLES["warning"],
        )
        return

    # Execute the query using DRY function
    try:
        execute_sql_query(
            query=query,
            workspace_id=workspace_id,
            database_id=database_id,
            json_output=json_output,
            csv_output=csv_output,
            yaml_output=yaml_output,
            porcelain=porcelain,
            limit=limit,
            max_display_rows=max_display_rows,
        )
    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Query failed: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)
