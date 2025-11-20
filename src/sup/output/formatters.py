"""
Output formatters for sup CLI.

Beautiful data formatting for query results and other outputs.
"""

import json
import time
from io import StringIO
from typing import Any, Callable, Dict, List, Optional

import pandas as pd
import yaml
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from sup.output.styles import COLORS, EMOJIS, RICH_STYLES
from sup.output.console import console


class QueryResult:
    """Container for SQL query results with metadata."""

    def __init__(
        self,
        data: pd.DataFrame,
        query: str,
        execution_time: Optional[float] = None,
        database_id: Optional[int] = None,
    ):
        self.data = data
        self.query = query
        self.execution_time = execution_time
        self.database_id = database_id


def display_query_results(
    result: QueryResult,
    output_format: str = "table",
    max_rows: int = 100,
    max_width: Optional[int] = None,
    porcelain: bool = False,
) -> None:
    """
    Display query results in the specified format.

    Args:
        result: QueryResult containing DataFrame and metadata
        output_format: "table", "json", "csv", "yaml", "porcelain"
        max_rows: Maximum number of rows to display
        max_width: Maximum column width for table display
        porcelain: If True, output machine-readable format without decorations
    """
    df = result.data

    # Porcelain mode: suppress decorations but respect output format
    if porcelain:
        if output_format == "json":
            display_porcelain_json(df, max_rows)
        elif output_format == "csv":
            display_porcelain_csv(df, max_rows)
        elif output_format == "yaml":
            display_porcelain_yaml(df, max_rows)
        else:
            display_porcelain(df, max_rows)  # Default tab-separated
        return

    # Show query info
    console.print(f"\n{EMOJIS['sql']} Query executed", style=RICH_STYLES["header"])

    # Display the SQL query with syntax highlighting
    sql_syntax = Syntax(result.query, "sql", theme="monokai", line_numbers=False)
    console.print(Panel(sql_syntax, title="SQL Query", border_style=COLORS.info))

    # Show execution time if available
    if result.execution_time:
        console.print(
            f"⏱️  Execution time: {result.execution_time:.3f}s",
            style=RICH_STYLES["info"],
        )

    # Show row count
    row_count = len(df)
    console.print(
        f"📊 Returned {row_count:,} row{'s' if row_count != 1 else ''}",
        style=RICH_STYLES["success"],
    )

    if row_count == 0:
        console.print(f"{EMOJIS['info']} No data returned", style=RICH_STYLES["dim"])
        return

    # Display data in requested format
    if output_format == "json":
        display_json(df, max_rows)
    elif output_format == "csv":
        display_csv(df, max_rows)
    elif output_format == "yaml":
        display_yaml(df, max_rows)
    else:
        display_table(df, max_rows, max_width)


def display_table(
    df: pd.DataFrame,
    max_rows: int = 100,
    max_width: Optional[int] = None,
) -> None:
    """Display DataFrame as a beautiful Rich table."""
    console.print()

    # Create table
    table = Table(
        title=f"{EMOJIS['table']} Results",
        show_header=True,
        header_style=RICH_STYLES["header"],
        border_style="bright_blue",
        row_styles=["", "dim"],
        expand=False,
    )

    # Add columns with smart width management
    for col in df.columns:
        # Determine column styling based on data type
        style = COLORS.secondary
        if df[col].dtype in ["int64", "int32", "float64", "float32"]:
            style = COLORS.success
        elif df[col].dtype == "bool":
            style = COLORS.warning
        elif pd.api.types.is_datetime64_any_dtype(df[col]):
            style = RICH_STYLES["accent"]

        table.add_column(str(col), style=style, no_wrap=True, max_width=max_width or 50)

    # Add rows (limit for performance)
    display_df = df.head(max_rows)
    for _, row in display_df.iterrows():
        # Convert each value to string, handling NaN/None gracefully
        formatted_row = []
        for val in row:
            if pd.isna(val):
                formatted_row.append("[dim]NULL[/dim]")
            else:
                formatted_row.append(str(val))

        table.add_row(*formatted_row)

    console.print(table)

    # Show truncation message if needed
    if len(df) > max_rows:
        console.print(
            f"📋 Showing first {max_rows:,} of {len(df):,} rows",
            style=RICH_STYLES["dim"],
        )


def display_json(df: pd.DataFrame, max_rows: int = 100) -> None:
    """Display DataFrame as formatted JSON."""
    console.print()

    # Convert to records format (list of dicts)
    display_df = df.head(max_rows)
    data = display_df.to_dict("records")

    # Pretty print JSON with syntax highlighting
    json_str = json.dumps(data, indent=2, default=str)
    syntax = Syntax(json_str, "json", theme="monokai", line_numbers=False)
    console.print(syntax)

    # Show truncation message if needed
    if len(df) > max_rows:
        console.print(
            f"📋 Showing first {max_rows:,} of {len(df):,} rows",
            style=RICH_STYLES["dim"],
        )


def display_csv(df: pd.DataFrame, max_rows: int = 100) -> None:
    """Display DataFrame as CSV."""
    console.print()

    # Convert to CSV
    display_df = df.head(max_rows)
    csv_buffer = StringIO()
    display_df.to_csv(csv_buffer, index=False)
    csv_str = csv_buffer.getvalue()

    # Display with subtle styling
    console.print(csv_str.rstrip(), style=RICH_STYLES["data"])

    # Show truncation message if needed
    if len(df) > max_rows:
        console.print(
            f"# Showing first {max_rows:,} of {len(df):,} rows",
            style=RICH_STYLES["dim"],
        )


def display_yaml(df: pd.DataFrame, max_rows: int = 100) -> None:
    """Display DataFrame as YAML."""
    console.print()

    # Convert to records format
    display_df = df.head(max_rows)
    data = display_df.to_dict("records")

    # Convert to YAML
    yaml_str = yaml.safe_dump(data, default_flow_style=False, indent=2)

    # Display with syntax highlighting
    syntax = Syntax(yaml_str, "yaml", theme="monokai", line_numbers=False)
    console.print(syntax)

    # Show truncation message if needed
    if len(df) > max_rows:
        console.print(
            f"# Showing first {max_rows:,} of {len(df):,} rows",
            style=RICH_STYLES["dim"],
        )


def show_query_progress(query: str) -> None:
    """Show a progress indicator while query is running."""
    console.print(
        f"\n{EMOJIS['loading']} Executing query...",
        style=RICH_STYLES["info"],
    )

    # Show truncated query for context
    if len(query) > 100:
        display_query = query[:97] + "..."
    else:
        display_query = query

    console.print(f"[dim]SQL: {display_query}[/dim]")


class QueryTimer:
    """Context manager for timing SQL queries."""

    def __init__(self):
        self.start_time = None
        self.execution_time = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time:
            self.execution_time = time.time() - self.start_time


def display_porcelain(df: pd.DataFrame, max_rows: int = 100) -> None:
    """Display DataFrame in porcelain mode - pure data, no decorations."""
    if len(df) == 0:
        return  # No output for empty results in porcelain mode

    # Simple tab-separated output, no headers, no decorations
    display_df = df.head(max_rows)
    for _, row in display_df.iterrows():
        # Convert each value to string, handling NaN/None as empty
        formatted_row = []
        for val in row:
            if pd.isna(val):
                formatted_row.append("")
            else:
                formatted_row.append(str(val))

        # Output as tab-separated values
        print("\t".join(formatted_row))


def display_porcelain_list(items: List[Dict[str, Any]], fields: List[str]) -> None:
    """Display list data in porcelain mode - tab-separated fields."""
    for item in items:
        values = []
        for field in fields:
            value = item.get(field, "")
            values.append(str(value) if value is not None else "")
        print("\t".join(values))


def display_porcelain_json(df: pd.DataFrame, max_rows: int = 100) -> None:
    """Display DataFrame as pure JSON (no decorations)."""
    display_df = df.head(max_rows)
    data = display_df.to_dict("records")
    print(json.dumps(data, default=str))


def display_porcelain_csv(df: pd.DataFrame, max_rows: int = 100) -> None:
    """Display DataFrame as pure CSV (no decorations)."""
    display_df = df.head(max_rows)
    csv_buffer = StringIO()
    display_df.to_csv(csv_buffer, index=False)
    print(csv_buffer.getvalue().rstrip())


def display_porcelain_yaml(df: pd.DataFrame, max_rows: int = 100) -> None:
    """Display DataFrame as pure YAML (no decorations)."""
    display_df = df.head(max_rows)
    data = display_df.to_dict("records")
    print(yaml.safe_dump(data, default_flow_style=False, indent=2).rstrip())


def display_entity_results(
    items: List[Dict[str, Any]],
    output_format: str = "table",
    porcelain: bool = False,
    porcelain_fields: Optional[List[str]] = None,
    table_display_func: Optional[Callable[..., Any]] = None,
) -> None:
    """
    Consolidated output handler for all entity results.

    This eliminates the repeated output logic across dataset.py, chart.py, etc.

    Args:
        items: List of entity dictionaries
        output_format: "table", "json", "yaml", "porcelain"
        porcelain: If True, use machine-readable format
        porcelain_fields: List of field names for porcelain tab-separated output
        table_display_func: Optional custom table display function
    """
    if porcelain:
        # Tab-separated porcelain output
        if porcelain_fields:
            display_porcelain_list(items, porcelain_fields)
        else:
            # Fallback: display first few keys as fields
            if items:
                keys = list(items[0].keys())[:5]  # First 5 fields
                display_porcelain_list(items, keys)
    elif output_format == "json":
        print(json.dumps(items, indent=2, default=str))
    elif output_format == "yaml":
        print(yaml.safe_dump(items, default_flow_style=False, indent=2))
    else:
        # Rich table display
        if table_display_func:
            table_display_func(items)
        else:
            console.print(f"{EMOJIS['info']} Found {len(items)} items")
            if items:
                # Generic table fallback
                table = Table(show_header=True, header_style=RICH_STYLES["header"])

                # Add first few columns
                sample_item = items[0]
                columns = list(sample_item.keys())[:5]  # Limit to 5 columns
                for col in columns:
                    table.add_column(str(col), style=COLORS.secondary)

                # Add rows
                for item in items[:50]:  # Limit to 50 rows
                    row_values = []
                    for col in columns:
                        val = item.get(col, "")
                        row_values.append(str(val) if val is not None else "")
                    table.add_row(*row_values)

                console.print(table)
