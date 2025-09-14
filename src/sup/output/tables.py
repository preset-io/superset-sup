"""
Generic table display system for sup CLI entities.

Provides configurable table display with entity-specific field definitions
and clickable links, eliminating the need for separate table display functions
in dataset.py, chart.py, workspace.py, etc.
"""

from typing import Any, Callable, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from sup.output.styles import COLORS, EMOJIS, RICH_STYLES

console = Console()


class EntityTableConfig:
    """Configuration for displaying an entity type in a Rich table."""

    def __init__(
        self,
        title_emoji: str,
        title_name: str,
        border_style: str = COLORS.secondary,
        info_command: Optional[str] = None,
    ):
        self.title_emoji = title_emoji
        self.title_name = title_name
        self.border_style = border_style
        self.info_command = info_command
        self.columns: List[Dict[str, Any]] = []

    def add_column(
        self,
        field: str,
        display_name: str,
        style: str = COLORS.secondary,
        no_wrap: bool = True,
        min_width: Optional[int] = None,
        max_width: Optional[int] = None,
        link_template: Optional[str] = None,
        transform_func: Optional[Callable[..., Any]] = None,
    ):
        """Add a column to the table configuration."""
        self.columns.append(
            {
                "field": field,
                "display_name": display_name,
                "style": style,
                "no_wrap": no_wrap,
                "min_width": min_width,
                "max_width": max_width,
                "link_template": link_template,
                "transform_func": transform_func,
            },
        )
        return self  # For chaining


def display_entity_table(
    items: List[Dict[str, Any]],
    config: EntityTableConfig,
    workspace_hostname: Optional[str] = None,
) -> None:
    """
    Display entities in a beautiful Rich table with clickable links.

    Args:
        items: List of entity dictionaries
        config: EntityTableConfig defining how to display the table
        workspace_hostname: Optional hostname for creating clickable links
    """
    if not items:
        console.print(
            f"{EMOJIS['warning']} No {config.title_name.lower()} found",
            style=RICH_STYLES["warning"],
        )
        return

    table = Table(
        title=f"{config.title_emoji} Available {config.title_name}",
        show_header=True,
        header_style=RICH_STYLES["header"],
        border_style=config.border_style,
    )

    # Add columns from configuration
    for column in config.columns:
        table.add_column(
            column["display_name"],
            style=column["style"],
            no_wrap=column["no_wrap"],
            min_width=column.get("min_width"),
            max_width=column.get("max_width"),
        )

    # Add rows
    for item in items:
        row_values = []
        for column in config.columns:
            field = column["field"]
            raw_value = item.get(field, "")

            # Apply transformation function if provided
            if column["transform_func"]:
                raw_value = column["transform_func"](raw_value, item)

            # Create clickable link if template and hostname provided
            if column["link_template"] and workspace_hostname:
                # Replace placeholders in template with actual values
                # Create template context without duplicate keys
                template_context = {
                    "hostname": workspace_hostname,
                    "name": raw_value,
                    **item,  # item already contains 'id', so don't pass it explicitly
                }
                link_url = column["link_template"].format(**template_context)
                display_value = f"[link={link_url}]{raw_value}[/link]"
            else:
                display_value = str(raw_value) if raw_value is not None else ""

            row_values.append(display_value)

        table.add_row(*row_values)

    console.print(table)

    # Show helpful info
    if config.info_command:
        console.print(
            f"\n💡 Use [bold]{config.info_command} <ID>[/] for detailed information",
            style=RICH_STYLES["dim"],
        )

    if workspace_hostname:
        console.print(
            "🔗 Click ID for API endpoint, Name for GUI exploration",
            style=RICH_STYLES["dim"],
        )


# Pre-configured entity table configs
DATASET_TABLE_CONFIG = (
    EntityTableConfig(
        title_emoji=EMOJIS["table"],
        title_name="Datasets",
        border_style=COLORS.secondary,
        info_command="sup dataset info",
    )
    .add_column(
        "id",
        "ID",
        style=COLORS.secondary,
        link_template="https://{hostname}/api/v1/dataset/{id}",
    )
    .add_column(
        "table_name",
        "Name",
        style="bright_white",
        no_wrap=False,
        min_width=15,
        max_width=40,
        link_template="https://{hostname}{explore_url}",
        transform_func=lambda name, item: name,  # Could add explore_url handling
    )
    .add_column(
        "database.database_name",
        "Database",
        style=COLORS.warning,
        min_width=20,
        max_width=35,
        transform_func=lambda _, item: item.get("database", {}).get("database_name", "Unknown"),
    )
    .add_column(
        "schema",
        "Schema",
        style=COLORS.info,
        transform_func=lambda schema, _: schema or "default",
    )
    .add_column(
        "kind",
        "Type",
        style=COLORS.success,
        transform_func=lambda kind, _: kind or "physical",
    )
    .add_column(
        "columns",
        "Columns",
        style=RICH_STYLES["accent"],
        transform_func=lambda columns, _: str(len(columns or [])),
    )
)

CHART_TABLE_CONFIG = (
    EntityTableConfig(
        title_emoji=EMOJIS["chart"],
        title_name="Charts",
        border_style=COLORS.secondary,
        info_command="sup chart info",
    )
    .add_column(
        "id",
        "ID",
        style=COLORS.secondary,
        link_template="https://{hostname}/api/v1/chart/{id}",
    )
    .add_column(
        "slice_name",
        "Name",
        style="bright_white",
        no_wrap=False,
        min_width=15,
        max_width=30,
        link_template="https://{hostname}/superset/explore/?slice_id={id}",
    )
    .add_column(
        "viz_type",
        "Type",
        style=COLORS.warning,
        min_width=12,
        max_width=25,
        transform_func=lambda viz_type, _: viz_type or "Unknown",
    )
    .add_column(
        "datasource_name",
        "Dataset",
        style=COLORS.info,
        min_width=18,
        max_width=35,
        transform_func=lambda ds_name, item: (
            item.get("datasource_name_text")
            or ds_name
            or (f"ID:{item.get('datasource_id')}" if item.get("datasource_id") else "Unknown")
        ),
    )
    .add_column(
        "dashboards",
        "Dashboards",
        style=COLORS.success,
        min_width=15,
        max_width=25,
        transform_func=lambda dashboards, _: (
            ", ".join(
                [str(d.get("dashboard_title", d.get("id", ""))) for d in (dashboards or [])[:2]],
            )
            + (f" (+{len(dashboards) - 2} more)" if len(dashboards or []) > 2 else "")
            if dashboards
            else "None"
        ),
    )
)

WORKSPACE_TABLE_CONFIG = (
    EntityTableConfig(
        title_emoji=EMOJIS["workspace"],
        title_name="Workspaces",
        border_style=COLORS.info,
    )
    .add_column("id", "ID", style=COLORS.secondary)
    .add_column("title", "Name", style="bright_white", no_wrap=False)
    .add_column("team_name", "Team", style=COLORS.warning)
    .add_column("hostname", "URL", style=COLORS.info, no_wrap=False)
    .add_column(
        "status",
        "Status",
        style=COLORS.success,
        transform_func=lambda status, _: status or "active",
    )
)

DASHBOARD_TABLE_CONFIG = (
    EntityTableConfig(
        title_emoji=EMOJIS["dashboard"],
        title_name="Dashboards",
        border_style=COLORS.primary,
        info_command="sup dashboard info",
    )
    .add_column(
        "id",
        "ID",
        style=COLORS.secondary,
        link_template="https://{hostname}/api/v1/dashboard/{id}",
    )
    .add_column(
        "dashboard_title",
        "Name",
        style="bright_white",
        no_wrap=False,
        link_template="https://{hostname}/superset/dashboard/{id}/",
    )
    .add_column(
        "published",
        "Status",
        style=COLORS.success,
        transform_func=lambda published, _: "Published" if published else "Draft",
    )
    .add_column(
        "owners",
        "Owners",
        style=COLORS.info,
        transform_func=lambda owners, _: (
            ", ".join(
                [
                    f"{owner.get('first_name', '')} {owner.get('last_name', '')}".strip()
                    for owner in (owners or [])[:2]
                ],
            )
            + (f" (+{len(owners) - 2} more)" if len(owners or []) > 2 else "")
            if owners
            else "None"
        ),
    )
    .add_column(
        "created_on",
        "Created",
        style="dim",
        transform_func=lambda created_on, _: (
            created_on.split("T")[0] if created_on else "Unknown"
        ),
    )
)

SAVED_QUERY_TABLE_CONFIG = (
    EntityTableConfig(
        title_emoji=EMOJIS["sql"],
        title_name="Saved Queries",
        border_style=COLORS.info,
        info_command="sup query info",
    )
    .add_column(
        "id",
        "ID",
        style=COLORS.secondary,
        link_template="https://{hostname}/api/v1/saved_query/{id}",
    )
    .add_column(
        "label",
        "Name",
        style="bright_white",
        no_wrap=False,
        link_template="https://{hostname}/superset/sqllab/?savedQueryId={id}",
    )
    .add_column(
        "database.database_name",
        "Database",
        style=COLORS.warning,
        transform_func=lambda _, item: item.get("database", {}).get("database_name", "Unknown"),
    )
    .add_column(
        "schema",
        "Schema",
        style=COLORS.info,
        transform_func=lambda schema, _: schema or "default",
    )
    .add_column(
        "changed_on",
        "Modified",
        style="dim",
        transform_func=lambda changed_on, _: (
            changed_on.split("T")[0] if changed_on else "Unknown"
        ),
    )
)

DATABASE_TABLE_CONFIG = (
    EntityTableConfig(
        title_emoji=EMOJIS["database"],
        title_name="Databases",
        border_style=COLORS.success,
    )
    .add_column("id", "ID", style=COLORS.secondary)
    .add_column("database_name", "Name", style="bright_white", no_wrap=False)
    .add_column("backend", "Engine", style=COLORS.warning)
    .add_column(
        "allow_run_async",
        "Async",
        style=COLORS.success,
        transform_func=lambda allow_async, _: "Yes" if allow_async else "No",
    )
    .add_column(
        "expose_in_sqllab",
        "SQL Lab",
        style=COLORS.info,
        transform_func=lambda expose, _: "Yes" if expose else "No",
    )
)


# Convenience functions using pre-configured configs
def display_datasets_table(items: List[Dict[str, Any]], hostname: Optional[str] = None) -> None:
    """Display datasets using the standard configuration."""
    display_entity_table(items, DATASET_TABLE_CONFIG, hostname)


def display_charts_table(items: List[Dict[str, Any]], hostname: Optional[str] = None) -> None:
    """Display charts using the standard configuration."""
    display_entity_table(items, CHART_TABLE_CONFIG, hostname)


def display_workspaces_table(items: List[Dict[str, Any]], hostname: Optional[str] = None) -> None:
    """Display workspaces using the standard configuration."""
    display_entity_table(items, WORKSPACE_TABLE_CONFIG, hostname)


def display_dashboards_table(items: List[Dict[str, Any]], hostname: Optional[str] = None) -> None:
    """Display dashboards using the standard configuration."""
    display_entity_table(items, DASHBOARD_TABLE_CONFIG, hostname)


def display_saved_queries_table(
    items: List[Dict[str, Any]],
    hostname: Optional[str] = None,
) -> None:
    """Display saved queries using the standard configuration."""
    display_entity_table(items, SAVED_QUERY_TABLE_CONFIG, hostname)


def display_databases_table(items: List[Dict[str, Any]], hostname: Optional[str] = None) -> None:
    """Display databases using the standard configuration."""
    display_entity_table(items, DATABASE_TABLE_CONFIG, hostname)
