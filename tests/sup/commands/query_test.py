"""Tests for sup.commands.query - saved query management commands."""

from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from sup.commands.query import app, display_saved_query_details

runner = CliRunner()


def _make_spinner_cm(sp_obj=None):
    """Create a mock spinner context manager."""
    cm = MagicMock()
    obj = sp_obj or MagicMock()
    cm.__enter__ = MagicMock(return_value=obj)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, obj


# Patch targets at the source modules (lazy imports inside functions)
CTX = "sup.config.settings.SupContext"
CLIENT = "sup.clients.superset.SupSupersetClient"
SPINNER = "sup.output.spinners.data_spinner"

SAMPLE_QUERIES = [
    {
        "id": 1,
        "label": "Sales Report",
        "db_id": 10,
        "schema": "analytics",
        "database": {"database_name": "main_db"},
        "changed_on": "2024-01-15T10:00:00",
    },
    {
        "id": 2,
        "label": "User Stats",
        "db_id": 20,
        "schema": "public",
        "database": {"database_name": "stats_db"},
        "changed_on": "2024-02-20T12:00:00",
    },
    {
        "id": 3,
        "label": "daily_sales_summary",
        "db_id": 10,
        "schema": "analytics",
        "database": {"database_name": "main_db"},
        "changed_on": "2024-03-01T08:00:00",
    },
]


# ---- list_saved_queries ----


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_table_output(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    """Default table output path."""
    cm, sp = _make_spinner_cm()
    mock_data_spinner.return_value = cm

    ctx = MagicMock()
    ctx.get_workspace_hostname.return_value = "ws.preset.io"
    mock_ctx_cls.return_value = ctx

    client = MagicMock()
    client.get_saved_queries.return_value = SAMPLE_QUERIES
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.query.display_saved_queries_table") as mock_table:
        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        mock_table.assert_called_once_with(SAMPLE_QUERIES, "ws.preset.io")
    # Spinner text for unfiltered
    assert sp.text == f"Found {len(SAMPLE_QUERIES)} saved queries"


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_porcelain_output(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_saved_queries.return_value = SAMPLE_QUERIES
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.query.display_porcelain_list") as mock_porcelain:
        result = runner.invoke(app, ["list", "--porcelain"])
        assert result.exit_code == 0
        mock_porcelain.assert_called_once()
    mock_data_spinner.assert_called_once_with("saved queries", silent=True)


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_json_output(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_saved_queries.return_value = [SAMPLE_QUERIES[0]]
    mock_client_cls.from_context.return_value = client

    result = runner.invoke(app, ["list", "--json"])
    assert result.exit_code == 0
    assert "Sales Report" in result.output


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_yaml_output(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_saved_queries.return_value = [SAMPLE_QUERIES[0]]
    mock_client_cls.from_context.return_value = client

    result = runner.invoke(app, ["list", "--yaml"])
    assert result.exit_code == 0
    assert "Sales Report" in result.output


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_name_filter(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    """fnmatch name filter path."""
    cm, sp = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    ctx = MagicMock()
    ctx.get_workspace_hostname.return_value = "ws.preset.io"
    mock_ctx_cls.return_value = ctx
    client = MagicMock()
    client.get_saved_queries.return_value = SAMPLE_QUERIES
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.query.display_saved_queries_table") as mock_table:
        result = runner.invoke(app, ["list", "--name", "*sales*"])
        assert result.exit_code == 0
        called_queries = mock_table.call_args[0][0]
        assert len(called_queries) == 2
    assert "showing 2 after filtering" in sp.text


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_mine_filter(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    """--mine is a pass-through (no-op currently)."""
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    ctx = MagicMock()
    ctx.get_workspace_hostname.return_value = "ws.preset.io"
    mock_ctx_cls.return_value = ctx
    client = MagicMock()
    client.get_saved_queries.return_value = SAMPLE_QUERIES
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.query.display_saved_queries_table"):
        result = runner.invoke(app, ["list", "--mine"])
        assert result.exit_code == 0


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_database_id_filter(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    cm, sp = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    ctx = MagicMock()
    ctx.get_workspace_hostname.return_value = "ws.preset.io"
    mock_ctx_cls.return_value = ctx
    client = MagicMock()
    client.get_saved_queries.return_value = SAMPLE_QUERIES
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.query.display_saved_queries_table") as mock_table:
        result = runner.invoke(app, ["list", "--database-id", "10"])
        assert result.exit_code == 0
        called_queries = mock_table.call_args[0][0]
        assert len(called_queries) == 2
        assert all(q["db_id"] == 10 for q in called_queries)


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_schema_filter(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    ctx = MagicMock()
    ctx.get_workspace_hostname.return_value = "ws.preset.io"
    mock_ctx_cls.return_value = ctx
    client = MagicMock()
    client.get_saved_queries.return_value = SAMPLE_QUERIES
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.query.display_saved_queries_table") as mock_table:
        result = runner.invoke(app, ["list", "--schema", "public"])
        assert result.exit_code == 0
        called_queries = mock_table.call_args[0][0]
        assert len(called_queries) == 1
        assert called_queries[0]["id"] == 2


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_id_filter(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    ctx = MagicMock()
    ctx.get_workspace_hostname.return_value = "ws.preset.io"
    mock_ctx_cls.return_value = ctx
    client = MagicMock()
    client.get_saved_queries.return_value = SAMPLE_QUERIES
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.query.display_saved_queries_table") as mock_table:
        result = runner.invoke(app, ["list", "--id", "3"])
        assert result.exit_code == 0
        called_queries = mock_table.call_args[0][0]
        assert len(called_queries) == 1
        assert called_queries[0]["id"] == 3


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_limit_filter(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_saved_queries.return_value = SAMPLE_QUERIES
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.query.display_saved_queries_table"):
        result = runner.invoke(app, ["list", "--limit", "5"])
        assert result.exit_code == 0
    client.get_saved_queries.assert_called_once_with(silent=True, limit=5)


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_workspace_id(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    ctx = MagicMock()
    mock_ctx_cls.return_value = ctx
    client = MagicMock()
    client.get_saved_queries.return_value = []
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.query.display_saved_queries_table"):
        result = runner.invoke(app, ["list", "--workspace-id", "99"])
        assert result.exit_code == 0
    mock_client_cls.from_context.assert_called_once_with(ctx, 99)


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_spinner_silent_porcelain(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    """Spinner sp is None in silent (porcelain) mode -- covers `if sp:` False branch."""
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=None)
    cm.__exit__ = MagicMock(return_value=False)
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_saved_queries.return_value = SAMPLE_QUERIES
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.query.display_porcelain_list"):
        result = runner.invoke(app, ["list", "--porcelain"])
        assert result.exit_code == 0


@patch(CTX)
def test_list_error_no_porcelain(mock_ctx_cls):
    """Error path without porcelain -- prints error and exits 1."""
    mock_ctx_cls.side_effect = RuntimeError("connection failed")

    result = runner.invoke(app, ["list"])
    assert result.exit_code == 1
    assert "Failed to list saved queries" in result.output


@patch(CTX)
def test_list_error_with_porcelain(mock_ctx_cls):
    """Error path with porcelain -- no error message printed, exits 1."""
    mock_ctx_cls.side_effect = RuntimeError("connection failed")

    result = runner.invoke(app, ["list", "--porcelain"])
    assert result.exit_code == 1
    assert "Failed to list saved queries" not in result.output


# ---- saved_query_info ----


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_info_table_output(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    """Default rich table output calls display_saved_query_details."""
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    query_data = {"id": 1, "label": "Test", "database": {"database_name": "db"}}
    client.get_saved_query.return_value = query_data
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.query.display_saved_query_details") as mock_display:
        result = runner.invoke(app, ["info", "1"])
        assert result.exit_code == 0
        mock_display.assert_called_once_with(query_data)


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_info_porcelain(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_saved_query.return_value = {
        "id": 5,
        "label": "My Query",
        "database": {"database_name": "mydb"},
    }
    mock_client_cls.from_context.return_value = client

    result = runner.invoke(app, ["info", "5", "--porcelain"])
    assert result.exit_code == 0
    assert "5\tMy Query\tmydb" in result.output


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_info_json(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_saved_query.return_value = {"id": 1, "label": "Q1"}
    mock_client_cls.from_context.return_value = client

    result = runner.invoke(app, ["info", "1", "--json"])
    assert result.exit_code == 0
    assert '"label"' in result.output


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_info_yaml(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_saved_query.return_value = {"id": 1, "label": "Q1"}
    mock_client_cls.from_context.return_value = client

    result = runner.invoke(app, ["info", "1", "--yaml"])
    assert result.exit_code == 0
    assert "label:" in result.output


@patch(CTX)
def test_info_error_no_porcelain(mock_ctx_cls):
    mock_ctx_cls.side_effect = RuntimeError("not found")

    result = runner.invoke(app, ["info", "999"])
    assert result.exit_code == 1
    assert "Failed to get saved query info" in result.output


@patch(CTX)
def test_info_error_with_porcelain(mock_ctx_cls):
    mock_ctx_cls.side_effect = RuntimeError("not found")

    result = runner.invoke(app, ["info", "999", "--porcelain"])
    assert result.exit_code == 1
    assert "Failed to get saved query info" not in result.output


@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_info_workspace_id(mock_ctx_cls, mock_client_cls, mock_data_spinner):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    ctx = MagicMock()
    mock_ctx_cls.return_value = ctx
    client = MagicMock()
    client.get_saved_query.return_value = {"id": 1, "label": "Q", "database": {}}
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.query.display_saved_query_details"):
        result = runner.invoke(app, ["info", "1", "--workspace-id", "42"])
        assert result.exit_code == 0
    mock_client_cls.from_context.assert_called_once_with(ctx, 42)


# ---- display_saved_query_details ----


@patch("sup.commands.query.console")
def test_display_details_full(mock_console):
    """All optional fields present."""
    query = {
        "id": 10,
        "label": "Full Query",
        "database": {"database_name": "prod_db"},
        "schema": "public",
        "description": "A useful query",
        "created_on": "2024-01-10T09:00:00",
        "changed_on": "2024-06-15T14:30:00",
        "last_run_delta_humanized": "2 hours ago",
        "sql": "SELECT * FROM users",
        "tags": [{"name": "important"}, {"name": "daily"}],
    }
    display_saved_query_details(query)
    # Panel + SQL header + SQL panel + Tags header + 2 tag lines = 6 calls
    assert mock_console.print.call_count >= 5


@patch("sup.commands.query.console")
def test_display_details_minimal(mock_console):
    """No optional fields -- only basic panel printed."""
    query = {
        "id": 1,
        "label": "Bare",
        "database": {"database_name": "db"},
        "schema": "default",
    }
    display_saved_query_details(query)
    assert mock_console.print.call_count == 1


@patch("sup.commands.query.console")
def test_display_details_no_description(mock_console):
    query = {
        "id": 1,
        "label": "Q",
        "database": {},
        "sql": "SELECT 1",
    }
    display_saved_query_details(query)
    # Panel + SQL header + SQL panel = 3
    assert mock_console.print.call_count == 3


@patch("sup.commands.query.console")
def test_display_details_no_sql(mock_console):
    query = {
        "id": 1,
        "label": "Q",
        "database": {},
        "sql": "",
        "tags": [{"name": "t1"}],
    }
    display_saved_query_details(query)
    # Panel + tags header + 1 tag = 3
    assert mock_console.print.call_count == 3


@patch("sup.commands.query.console")
def test_display_details_no_created_on(mock_console):
    query = {
        "id": 1,
        "label": "Q",
        "database": {},
        "changed_on": "2024-01-01T00:00:00",
    }
    display_saved_query_details(query)
    assert mock_console.print.call_count == 1


@patch("sup.commands.query.console")
def test_display_details_no_changed_on(mock_console):
    query = {
        "id": 1,
        "label": "Q",
        "database": {},
        "created_on": "2024-01-01T00:00:00",
    }
    display_saved_query_details(query)
    assert mock_console.print.call_count == 1


@patch("sup.commands.query.console")
def test_display_details_no_last_run(mock_console):
    query = {
        "id": 1,
        "label": "Q",
        "database": {},
    }
    display_saved_query_details(query)
    assert mock_console.print.call_count == 1


@patch("sup.commands.query.console")
def test_display_details_empty_tags(mock_console):
    query = {
        "id": 1,
        "label": "Q",
        "database": {},
        "tags": [],
    }
    display_saved_query_details(query)
    assert mock_console.print.call_count == 1
