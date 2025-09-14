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
from sup.output.styles import COLORS, EMOJIS, RICH_STYLES

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
            border_style=COLORS.success,
        )

        table.add_column("ID", style=COLORS.secondary, no_wrap=True)
        table.add_column("Name", style="bright_white", no_wrap=False)
        table.add_column("Type", style=COLORS.warning, no_wrap=True)
        table.add_column("Backend", style=COLORS.info, no_wrap=True)
        table.add_column("Status", style=COLORS.success, no_wrap=True)

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

    def get_dashboards(
        self,
        silent: bool = False,
        limit: Optional[int] = None,
        page: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get dashboards with fast pagination - only fetch what we need."""
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

            url = self.client.baseurl / "api/v1/dashboard/" % {"q": query}
            response = self.client.session.get(url)
            validate_response(response)

            dashboards = response.json()["result"]

            if not silent:
                console.print(
                    f"Found {len(dashboards)} dashboards",
                    style=RICH_STYLES["dim"],
                )
            return dashboards

        except Exception as e:
            if not silent:
                console.print(
                    f"{EMOJIS['error']} Failed to fetch dashboards: {e}",
                    style=RICH_STYLES["error"],
                )
            return []

    def get_dashboard(self, dashboard_id: int, silent: bool = False) -> Dict[str, Any]:
        """Get a specific dashboard by ID."""
        try:
            dashboard = self.client.get_dashboard(dashboard_id)
            return dashboard
        except Exception as e:
            if not silent:
                console.print(
                    f"{EMOJIS['error']} Failed to fetch dashboard {dashboard_id}: {e}",
                    style=RICH_STYLES["error"],
                )
            raise

    def get_saved_queries(
        self,
        silent: bool = False,
        limit: Optional[int] = None,
        page: int = 0,
    ) -> List[Dict[str, Any]]:
        """Get saved queries with fast pagination."""
        try:
            # Use direct API call for saved queries
            import prison

            from preset_cli.lib import validate_response

            # Build query for single page fetch (use default ordering to avoid API errors)
            query = prison.dumps(
                {
                    "filters": [],
                    "page": page,
                    "page_size": limit or 50,
                },
            )

            url = self.client.baseurl / "api/v1/saved_query/" % {"q": query}
            response = self.client.session.get(url)
            validate_response(response)

            saved_queries = response.json()["result"]

            if not silent:
                console.print(
                    f"Found {len(saved_queries)} saved queries",
                    style=RICH_STYLES["dim"],
                )
            return saved_queries

        except Exception as e:
            if not silent:
                console.print(
                    f"{EMOJIS['error']} Failed to fetch saved queries: {e}",
                    style=RICH_STYLES["error"],
                )
            return []

    def get_saved_query(self, query_id: int, silent: bool = False) -> Dict[str, Any]:
        """Get a specific saved query by ID."""
        try:
            saved_query = self.client.get_resource("saved_query", query_id)
            return saved_query
        except Exception as e:
            if not silent:
                console.print(
                    f"{EMOJIS['error']} Failed to fetch saved query {query_id}: {e}",
                    style=RICH_STYLES["error"],
                )
            raise

    def get_chart_data(
        self,
        chart_id: int,
        result_type: str = "results",
        silent: bool = False,
    ) -> Dict[str, Any]:
        """
        Get chart data or SQL query using the chart data endpoint.

        Args:
            chart_id: Chart ID to get data for
            result_type: "results" for data, "query" for SQL
            silent: Whether to suppress error messages
        """
        try:
            # First get the chart to get its query_context and form_data
            chart = self.client.get_chart(chart_id)

            # Try to use query_context if available (this is what actually gets executed)
            query_context = chart.get("query_context", "{}")
            if isinstance(query_context, str):
                import json

                query_context = json.loads(query_context)

            # Build the payload using the chart's existing query context
            # This should match what Superset expects
            from preset_cli.lib import validate_response

            url = self.client.baseurl / "api/v1/chart/data"

            # Use the form data format that Superset expects
            form_data_payload = {
                **query_context,
                "result_type": result_type,
                "result_format": "json",
            }

            # Send as form data, not JSON (matching frontend)
            import json

            response = self.client.session.post(
                url,
                data={"form_data": json.dumps(form_data_payload)},
            )
            validate_response(response)

            result = response.json()

            if not silent:
                console.print(
                    f"Retrieved chart {result_type}",
                    style=RICH_STYLES["dim"],
                )

            return result

        except Exception as e:
            if not silent:
                console.print(
                    f"{EMOJIS['error']} Failed to get chart {result_type}: {e}",
                    style=RICH_STYLES["error"],
                )
            return {}

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

    def display_users_table(self, users: List[Dict[str, Any]]) -> None:
        """Display users in a beautiful Rich table."""
        if not users:
            console.print(
                f"{EMOJIS['warning']} No users found",
                style=RICH_STYLES["warning"],
            )
            return

        table = Table(
            title=f"{EMOJIS['user']} Available Users",
            show_header=True,
            header_style="bold #10B981",
            border_style="#10B981",
        )

        table.add_column("ID", justify="right", style="cyan", min_width=4)
        table.add_column("Email", style="bright_white", min_width=20)
        table.add_column("First Name", style="bright_white", min_width=15)
        table.add_column("Last Name", style="bright_white", min_width=15)
        table.add_column("Status", justify="center", min_width=8)
        table.add_column("Roles", style="dim", min_width=15)

        for user in users:
            # Format roles for display - UserType uses "role" field as List[str]
            roles = user.get("role", [])
            if isinstance(roles, list) and roles:
                roles_display = ", ".join(roles[:3])  # Show first 3 roles
                if len(roles) > 3:
                    roles_display += f" +{len(roles) - 3} more"
            else:
                roles_display = "-"

            # Format active status - UserType doesn't have active field, assume active if has roles
            active_status = "✅" if roles else "❓"

            table.add_row(
                str(user.get("id", "")),
                user.get("email", ""),
                user.get("first_name", ""),
                user.get("last_name", ""),
                active_status,
                roles_display,
            )

        console.print(table)
