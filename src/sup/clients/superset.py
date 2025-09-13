"""
Superset client wrapper for sup CLI.

Provides database and SQL execution functionality.
"""

from typing import Any, Dict, List, Optional

from rich.console import Console
from rich.table import Table

from preset_cli.api.clients.superset import SupersetClient
from sup.auth.preset import SupPresetAuth
from sup.config.settings import SupContext
from sup.output.styles import EMOJIS, RICH_STYLES

console = Console()


class SupSupersetClient:
    """
    Superset client wrapper with sup-specific functionality.
    """

    def __init__(self, workspace_url: str, auth: SupPresetAuth):
        self.workspace_url = workspace_url
        self.auth = auth
        self.client = SupersetClient(workspace_url, auth)

    @classmethod
    def from_context(
        cls,
        ctx: SupContext,
        workspace_id: Optional[int] = None,
    ) -> "SupSupersetClient":
        """Create Superset client from sup configuration context."""
        # Get workspace ID from context if not provided
        if workspace_id is None:
            workspace_id = ctx.get_workspace_id()

        if not workspace_id:
            console.print(
                f"{EMOJIS['error']} No workspace configured",
                style=RICH_STYLES["error"],
            )
            console.print(
                "💡 Run [bold]sup workspace list[/] and [bold]sup workspace use <ID>[/]",
                style=RICH_STYLES["info"],
            )
            raise ValueError("No workspace configured")

        # Check if we have cached hostname first
        hostname = ctx.get_workspace_hostname()

        if not hostname:
            # No cached hostname, fetch from Preset API
            from sup.clients.preset import SupPresetClient

            preset_client = SupPresetClient.from_context(ctx, silent=True)
            workspaces = preset_client.get_all_workspaces(
                silent=True,
            )  # Silent for internal operation

            # Find our workspace
            workspace = None
            for ws in workspaces:
                if ws.get("id") == workspace_id:
                    workspace = ws
                    break

            if not workspace:
                console.print(
                    f"{EMOJIS['error']} Workspace {workspace_id} not found",
                    style=RICH_STYLES["error"],
                )
                raise ValueError(f"Workspace {workspace_id} not found")

            hostname = workspace.get("hostname")
            if not hostname:
                console.print(
                    f"{EMOJIS['error']} No hostname for workspace {workspace_id}",
                    style=RICH_STYLES["error"],
                )
                raise ValueError(f"No hostname for workspace {workspace_id}")

            # Cache the hostname for future use
            ctx.set_workspace_context(workspace_id, hostname=hostname)

        workspace_url = f"https://{hostname}/"

        auth = SupPresetAuth.from_sup_config(
            ctx,
            silent=True,
        )  # Always silent for Superset client
        return cls(workspace_url, auth)

    def get_databases(self, silent: bool = False) -> List[Dict[str, Any]]:
        """Get all databases in the workspace."""
        try:
            databases = self.client.get_databases()
            if not silent:
                console.print(
                    f"Found {len(databases)} databases",
                    style=RICH_STYLES["dim"],
                )
            return databases
        except Exception as e:
            if not silent:
                console.print(
                    f"{EMOJIS['error']} Failed to fetch databases: {e}",
                    style=RICH_STYLES["error"],
                )
            return []

    def get_database(self, database_id: int) -> Dict[str, Any]:
        """Get a specific database by ID."""
        try:
            database = self.client.get_database(database_id)
            return database
        except Exception as e:
            console.print(
                f"{EMOJIS['error']} Failed to fetch database {database_id}: {e}",
                style=RICH_STYLES["error"],
            )
            raise

    def display_databases_table(self, databases: List[Dict[str, Any]]) -> None:
        """Display databases in a beautiful Rich table."""
        if not databases:
            console.print(
                f"{EMOJIS['warning']} No databases found",
                style=RICH_STYLES["warning"],
            )
            return

        table = Table(
            title=f"{EMOJIS['database']} Available Databases",
            show_header=True,
            header_style=RICH_STYLES["header"],
            border_style="green",
        )

        table.add_column("ID", style="cyan", no_wrap=True)
        table.add_column("Name", style="bright_white", no_wrap=False)
        table.add_column("Type", style="yellow", no_wrap=True)
        table.add_column("Backend", style="blue", no_wrap=True)
        table.add_column("Status", style="green", no_wrap=True)

        for database in databases:
            db_id = str(database.get("id", ""))
            name = database.get("database_name", "Unknown")
            backend = database.get("backend", "Unknown")

            # Try to determine database type from sqlalchemy_uri or backend
            db_type = backend.lower() if backend else "unknown"
            if "postgres" in db_type:
                db_type = "PostgreSQL"
            elif "mysql" in db_type:
                db_type = "MySQL"
            elif "sqlite" in db_type:
                db_type = "SQLite"
            elif "snowflake" in db_type:
                db_type = "Snowflake"
            elif "bigquery" in db_type:
                db_type = "BigQuery"
            else:
                db_type = backend or "Unknown"

            # Simple status check (in real implementation, could ping the database)
            status = "Available" if database.get("expose_in_sqllab", True) else "Hidden"

            table.add_row(db_id, name, db_type, backend or "Unknown", status)

        console.print(table)
        console.print(
            "\n💡 Use [bold]sup database use <ID>[/] to set default database",
            style=RICH_STYLES["dim"],
        )

    def get_datasets(
        self,
        silent: bool = False,
        limit: Optional[int] = None,
        page: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get datasets with fast pagination - only fetch what we need."""
        try:
            # Use direct API call to fetch only one page instead of everything
            import prison

            from preset_cli.lib import validate_response

            # Build query for single page fetch (use API default order)
            query = prison.dumps(
                {
                    "filters": [],
                    "order_column": "changed_on_delta_humanized",  # API default
                    "order_direction": "desc",
                    "page": page,
                    "page_size": limit or 50,  # Use our limit as page_size
                },
            )

            url = self.client.baseurl / "api/v1/dataset/" % {"q": query}
            response = self.client.session.get(url)
            validate_response(response)

            datasets = response.json()["result"]

            if not silent:
                console.print(
                    f"Found {len(datasets)} datasets",
                    style=RICH_STYLES["dim"],
                )
            return datasets

        except Exception as e:
            if not silent:
                console.print(
                    f"{EMOJIS['error']} Failed to fetch datasets: {e}",
                    style=RICH_STYLES["error"],
                )
            return []

    def get_dataset(self, dataset_id: int, silent: bool = False) -> Dict[str, Any]:
        """Get a specific dataset by ID."""
        try:
            dataset = self.client.get_dataset(dataset_id)
            return dataset
        except Exception as e:
            if not silent:
                console.print(
                    f"{EMOJIS['error']} Failed to fetch dataset {dataset_id}: {e}",
                    style=RICH_STYLES["error"],
                )
            raise

    def get_charts(
        self,
        silent: bool = False,
        limit: Optional[int] = None,
        page: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get charts with fast pagination - only fetch what we need."""
        try:
            # Use direct API call to fetch only one page instead of everything
            import prison

            from preset_cli.lib import validate_response

            # Build query for single page fetch (use API default order)
            query = prison.dumps(
                {
                    "filters": [],
                    "order_column": "changed_on_delta_humanized",  # API default
                    "order_direction": "desc",
                    "page": page,
                    "page_size": limit or 50,  # Use our limit as page_size
                },
            )

            url = self.client.baseurl / "api/v1/chart/" % {"q": query}
            response = self.client.session.get(url)
            validate_response(response)

            charts = response.json()["result"]

            if not silent:
                console.print(f"Found {len(charts)} charts", style=RICH_STYLES["dim"])
            return charts

        except Exception as e:
            if not silent:
                console.print(
                    f"{EMOJIS['error']} Failed to fetch charts: {e}",
                    style=RICH_STYLES["error"],
                )
            return []

    def get_chart(self, chart_id: int, silent: bool = False) -> Dict[str, Any]:
        """Get a specific chart by ID."""
        try:
            chart = self.client.get_chart(chart_id)
            return chart
        except Exception as e:
            if not silent:
                console.print(
                    f"{EMOJIS['error']} Failed to fetch chart {chart_id}: {e}",
                    style=RICH_STYLES["error"],
                )
            raise

    def execute_sql(self, database_id: int, sql: str) -> Dict[str, Any]:
        """Execute SQL query against a database."""
        try:
            console.print(
                f"{EMOJIS['loading']} Executing query...",
                style=RICH_STYLES["info"],
            )

            # Use the Superset SQL Lab API
            result = self.client.run_query(database_id, sql)
            return result
        except Exception as e:
            console.print(
                f"{EMOJIS['error']} Query failed: {e}",
                style=RICH_STYLES["error"],
            )
            raise
