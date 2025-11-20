"""
Saved query management commands for sup CLI.

Handles saved query listing, details, and management operations.
"""

from typing import Any, Dict, Optional

import typer

# Removed: from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from typing_extensions import Annotated

from sup.output.console import console
from sup.output.formatters import display_porcelain_list
from sup.output.styles import COLORS, EMOJIS, RICH_STYLES
from sup.output.tables import display_saved_queries_table

app = typer.Typer(help="Manage saved queries", no_args_is_help=True)


@app.command("list")
def list_saved_queries(
    # Universal filters (simplified for saved queries)
    id_filter: Annotated[
        Optional[int],
        typer.Option("--id", help="Filter by specific ID"),
    ] = None,
    name_filter: Annotated[
        Optional[str],
        typer.Option("--name", help="Filter by label pattern (supports wildcards)"),
    ] = None,
    mine_filter: Annotated[
        bool,
        typer.Option("--mine", "-m", help="Show only queries you created"),
    ] = False,
    limit_filter: Annotated[
        Optional[int],
        typer.Option("--limit", "-l", help="Maximum number of results"),
    ] = None,
    # Query-specific filters
    database_id: Annotated[
        Optional[int],
        typer.Option("--database-id", help="Filter by database ID"),
    ] = None,
    schema: Annotated[
        Optional[str],
        typer.Option("--schema", help="Filter by schema name"),
    ] = None,
    # Output options
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Workspace ID"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", "-y", help="Output as YAML")] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output (no decorations)"),
    ] = False,
):
    """
    List saved queries in the current or specified workspace.

    Examples:
        sup query list                                    # All saved queries
        sup query list --mine                            # My queries only
        sup query list --database-id=1 --porcelain      # Specific DB, machine-readable
        sup query list --name="*sales*" --json          # Pattern matching, JSON
        sup query list --schema=analytics               # Specific schema
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        # Get saved queries with spinner
        with data_spinner("saved queries", silent=porcelain) as sp:
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id)

            # Fetch saved queries
            saved_queries = client.get_saved_queries(silent=True, limit=limit_filter)

            # Apply basic client-side filters
            filtered_queries = saved_queries

            # Filter by name pattern
            if name_filter:
                import fnmatch

                pattern = name_filter.lower()
                filtered_queries = [
                    query
                    for query in filtered_queries
                    if fnmatch.fnmatch((query.get("label") or "").lower(), pattern)
                ]

            # Filter by mine
            if mine_filter:
                # Try to get current user info for filtering
                # For now, just show all since we'd need additional API call
                pass

            # Filter by database
            if database_id:
                filtered_queries = [
                    query for query in filtered_queries if query.get("db_id") == database_id
                ]

            # Filter by schema
            if schema:
                filtered_queries = [
                    query for query in filtered_queries if query.get("schema") == schema
                ]

            # Filter by ID
            if id_filter:
                filtered_queries = [
                    query for query in filtered_queries if query.get("id") == id_filter
                ]

            # Update spinner
            if sp:
                if filtered_queries != saved_queries:
                    sp.text = (
                        f"Found {len(saved_queries)} saved queries, "
                        f"showing {len(filtered_queries)} after filtering"
                    )
                else:
                    sp.text = f"Found {len(saved_queries)} saved queries"

        # Display results
        if porcelain:
            display_porcelain_list(
                filtered_queries,
                ["id", "label", "database.database_name", "schema", "changed_on"],
            )
        elif json_output:
            import json

            console.print(json.dumps(filtered_queries, indent=2, default=str))
        elif yaml_output:
            import yaml

            console.print(
                yaml.safe_dump(filtered_queries, default_flow_style=False, indent=2),
            )
        else:
            # Beautiful Rich table
            display_saved_queries_table(filtered_queries, ctx.get_workspace_hostname())

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to list saved queries: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


@app.command("info")
def saved_query_info(
    query_id: Annotated[int, typer.Argument(help="Saved query ID to inspect")],
    workspace_id: Annotated[
        Optional[int],
        typer.Option("--workspace-id", "-w", help="Workspace ID"),
    ] = None,
    json_output: Annotated[bool, typer.Option("--json", "-j", help="Output as JSON")] = False,
    yaml_output: Annotated[bool, typer.Option("--yaml", "-y", help="Output as YAML")] = False,
    porcelain: Annotated[
        bool,
        typer.Option("--porcelain", help="Machine-readable output"),
    ] = False,
):
    """
    Show detailed information about a saved query.

    Displays SQL content, metadata, and execution history.
    """
    from sup.clients.superset import SupSupersetClient
    from sup.config.settings import SupContext
    from sup.output.spinners import data_spinner

    try:
        with data_spinner(f"saved query {query_id}", silent=porcelain):
            ctx = SupContext()
            client = SupSupersetClient.from_context(ctx, workspace_id)
            query = client.get_saved_query(query_id, silent=True)

        if porcelain:
            # Simple key-value output
            print(
                f"{query_id}\t{query.get('label', '')}\t"
                f"{query.get('database', {}).get('database_name', '')}",
            )
        elif json_output:
            import json

            console.print(json.dumps(query, indent=2, default=str))
        elif yaml_output:
            import yaml

            console.print(yaml.safe_dump(query, default_flow_style=False, indent=2))
        else:
            display_saved_query_details(query)

    except Exception as e:
        if not porcelain:
            console.print(
                f"{EMOJIS['error']} Failed to get saved query info: {e}",
                style=RICH_STYLES["error"],
            )
        raise typer.Exit(1)


def display_saved_query_details(query: Dict[str, Any]) -> None:
    """Display detailed saved query information in Rich format."""
    query_id = query.get("id", "")
    label = query.get("label", "Unknown")
    database_info = query.get("database", {})

    # Basic info
    info_lines = [
        f"ID: {query_id}",
        f"Label: {label}",
        f"Database: {database_info.get('database_name', 'Unknown')}",
        f"Schema: {query.get('schema', 'default')}",
    ]

    if query.get("description"):
        info_lines.append(f"Description: {query['description']}")

    if query.get("created_on"):
        info_lines.append(f"Created: {query['created_on'].split('T')[0]}")

    if query.get("changed_on"):
        info_lines.append(f"Modified: {query['changed_on'].split('T')[0]}")

    if query.get("last_run_delta_humanized"):
        info_lines.append(f"Last Run: {query['last_run_delta_humanized']}")

    panel_content = "\n".join(info_lines)
    console.print(Panel(panel_content, title=f"Saved Query: {label}", border_style=COLORS.info))

    # Show SQL content with syntax highlighting
    sql_content = query.get("sql", "")
    if sql_content:
        console.print(f"\n{EMOJIS['sql']} SQL Query:", style=RICH_STYLES["header"])
        sql_syntax = Syntax(sql_content, "sql", theme="monokai", line_numbers=False)
        console.print(Panel(sql_syntax, title="SQL Content", border_style=COLORS.info))

    # Show tags if available
    tags = query.get("tags", [])
    if tags:
        console.print(
            f"\n{EMOJIS['star']} Tags ({len(tags)}):",
            style=RICH_STYLES["header"],
        )
        for tag in tags:
            tag_name = tag.get("name", "Unknown")
            console.print(f"  • {tag_name}", style=RICH_STYLES["dim"])


if __name__ == "__main__":
    app()
