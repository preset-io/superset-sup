"""Tests for sup.commands.sql module."""

from unittest.mock import MagicMock, patch

import pandas as pd
import pytest
from click.exceptions import Exit as ClickExit
from typer.testing import CliRunner

from sup.commands.sql import app, execute_sql_query, sql_command, sql_main

runner = CliRunner()


def _make_ctx_mock(workspace_id=1, database_id=2):
    ctx = MagicMock()
    ctx.get_workspace_id.return_value = workspace_id
    ctx.get_database_id.return_value = database_id
    return ctx


def _make_client_mock():
    client = MagicMock()
    client.client.run_query.return_value = pd.DataFrame({"a": [1]})
    return client


def _make_timer_mock(execution_time=0.5):
    timer = MagicMock()
    timer.execution_time = execution_time
    timer.__enter__ = MagicMock(return_value=timer)
    timer.__exit__ = MagicMock(return_value=False)
    return timer


def _make_spinner_mock(sp_value=None):
    """Return a context-manager mock. sp_value is what __enter__ yields."""
    if sp_value is None:
        sp_value = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=sp_value)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, sp_value


# ---------------------------------------------------------------------------
# execute_sql_query tests
# ---------------------------------------------------------------------------

class TestExecuteSqlQuery:
    """Tests for the execute_sql_query function."""

    @patch("sup.config.settings.SupContext")
    def test_no_workspace_configured(self, mock_ctx_cls):
        """Exit(1) when no workspace is configured."""
        mock_ctx_cls.return_value = _make_ctx_mock(workspace_id=None)

        with pytest.raises(ClickExit):
            execute_sql_query("SELECT 1")

    @patch("sup.config.settings.SupContext")
    def test_no_database_configured(self, mock_ctx_cls):
        """Exit(1) when no database is configured."""
        mock_ctx_cls.return_value = _make_ctx_mock(workspace_id=123, database_id=None)

        with pytest.raises(ClickExit):
            execute_sql_query("SELECT 1")

    @patch("sup.output.formatters.display_query_results")
    @patch("sup.output.formatters.QueryResult")
    @patch("sup.output.formatters.QueryTimer")
    @patch("sup.output.spinners.query_spinner")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_successful_query_table_output(
        self, mock_ctx_cls, mock_client_cls, mock_spinner_fn, mock_timer_cls,
        mock_result_cls, mock_display,
    ):
        """Successful query with default table output."""
        mock_ctx_cls.return_value = _make_ctx_mock()
        mock_client_cls.from_context.return_value = _make_client_mock()
        cm, sp = _make_spinner_mock()
        mock_spinner_fn.return_value = cm
        mock_timer_cls.return_value = _make_timer_mock()

        execute_sql_query("SELECT 1")

        mock_display.assert_called_once()
        assert mock_display.call_args[0][1] == "table"

    @patch("sup.output.formatters.display_query_results")
    @patch("sup.output.formatters.QueryResult")
    @patch("sup.output.formatters.QueryTimer")
    @patch("sup.output.spinners.query_spinner")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_successful_query_json_output(
        self, mock_ctx_cls, mock_client_cls, mock_spinner_fn, mock_timer_cls,
        mock_result_cls, mock_display,
    ):
        """Successful query with JSON output."""
        mock_ctx_cls.return_value = _make_ctx_mock()
        mock_client_cls.from_context.return_value = _make_client_mock()
        cm, _ = _make_spinner_mock()
        mock_spinner_fn.return_value = cm
        mock_timer_cls.return_value = _make_timer_mock()

        execute_sql_query("SELECT 1", json_output=True)

        assert mock_display.call_args[0][1] == "json"

    @patch("sup.output.formatters.display_query_results")
    @patch("sup.output.formatters.QueryResult")
    @patch("sup.output.formatters.QueryTimer")
    @patch("sup.output.spinners.query_spinner")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_successful_query_csv_output(
        self, mock_ctx_cls, mock_client_cls, mock_spinner_fn, mock_timer_cls,
        mock_result_cls, mock_display,
    ):
        """Successful query with CSV output."""
        mock_ctx_cls.return_value = _make_ctx_mock()
        mock_client_cls.from_context.return_value = _make_client_mock()
        cm, _ = _make_spinner_mock()
        mock_spinner_fn.return_value = cm
        mock_timer_cls.return_value = _make_timer_mock()

        execute_sql_query("SELECT 1", csv_output=True)

        assert mock_display.call_args[0][1] == "csv"

    @patch("sup.output.formatters.display_query_results")
    @patch("sup.output.formatters.QueryResult")
    @patch("sup.output.formatters.QueryTimer")
    @patch("sup.output.spinners.query_spinner")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_successful_query_yaml_output(
        self, mock_ctx_cls, mock_client_cls, mock_spinner_fn, mock_timer_cls,
        mock_result_cls, mock_display,
    ):
        """Successful query with YAML output."""
        mock_ctx_cls.return_value = _make_ctx_mock()
        mock_client_cls.from_context.return_value = _make_client_mock()
        cm, _ = _make_spinner_mock()
        mock_spinner_fn.return_value = cm
        mock_timer_cls.return_value = _make_timer_mock()

        execute_sql_query("SELECT 1", yaml_output=True)

        assert mock_display.call_args[0][1] == "yaml"

    @patch("sup.output.formatters.display_query_results")
    @patch("sup.output.formatters.QueryResult")
    @patch("sup.output.formatters.QueryTimer")
    @patch("sup.output.spinners.query_spinner")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_spinner_updated_when_not_none(
        self, mock_ctx_cls, mock_client_cls, mock_spinner_fn, mock_timer_cls,
        mock_result_cls, mock_display,
    ):
        """Spinner text is updated with execution time when sp is not None."""
        mock_ctx_cls.return_value = _make_ctx_mock()
        mock_client_cls.from_context.return_value = _make_client_mock()
        cm, sp = _make_spinner_mock()
        mock_spinner_fn.return_value = cm
        mock_timer_cls.return_value = _make_timer_mock(execution_time=1.23)

        execute_sql_query("SELECT 1")

        assert "1.23" in sp.text

    @patch("sup.output.formatters.display_query_results")
    @patch("sup.output.formatters.QueryResult")
    @patch("sup.output.formatters.QueryTimer")
    @patch("sup.output.spinners.query_spinner")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_spinner_none_in_porcelain_mode(
        self, mock_ctx_cls, mock_client_cls, mock_spinner_fn, mock_timer_cls,
        mock_result_cls, mock_display,
    ):
        """When spinner returns None (porcelain), no text update attempted."""
        mock_ctx_cls.return_value = _make_ctx_mock()
        mock_client_cls.from_context.return_value = _make_client_mock()
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=None)
        cm.__exit__ = MagicMock(return_value=False)
        mock_spinner_fn.return_value = cm
        mock_timer_cls.return_value = _make_timer_mock()

        # Should not raise AttributeError on None.text
        execute_sql_query("SELECT 1", porcelain=True)

        mock_display.assert_called_once()


# ---------------------------------------------------------------------------
# sql_command tests
# ---------------------------------------------------------------------------

class TestSqlCommand:
    """Tests for the sql_command function."""

    def test_interactive_mode_when_query_is_none(self):
        """When query is None, prints interactive mode warning."""
        with patch("sup.commands.sql.console") as mock_console:
            sql_command(query=None)
            calls = [str(c) for c in mock_console.print.call_args_list]
            assert any("nteractive" in c for c in calls)

    def test_explicit_interactive_flag(self):
        """When interactive=True, prints interactive mode warning."""
        with patch("sup.commands.sql.console") as mock_console:
            sql_command(query="SELECT 1", interactive=True)
            calls = [str(c) for c in mock_console.print.call_args_list]
            assert any("nteractive" in c for c in calls)

    @patch("sup.commands.sql.execute_sql_query")
    def test_normal_query_calls_execute(self, mock_execute):
        """Normal query delegates to execute_sql_query."""
        sql_command(query="SELECT 1")
        mock_execute.assert_called_once_with(
            query="SELECT 1",
            workspace_id=None,
            database_id=None,
            json_output=False,
            csv_output=False,
            yaml_output=False,
            porcelain=False,
            limit=1000,
            max_display_rows=100,
        )

    @patch("sup.commands.sql.execute_sql_query")
    def test_query_error_non_porcelain_prints_error(self, mock_execute):
        """On error with porcelain=False, error is printed."""
        mock_execute.side_effect = RuntimeError("connection failed")

        with patch("sup.commands.sql.console") as mock_console:
            with pytest.raises(ClickExit):
                sql_command(query="SELECT 1", porcelain=False)
            calls = [str(c) for c in mock_console.print.call_args_list]
            assert any("connection failed" in c for c in calls)

    @patch("sup.commands.sql.execute_sql_query")
    def test_query_error_porcelain_no_print(self, mock_execute):
        """On error with porcelain=True, no error is printed."""
        mock_execute.side_effect = RuntimeError("connection failed")

        with patch("sup.commands.sql.console") as mock_console:
            with pytest.raises(ClickExit):
                sql_command(query="SELECT 1", porcelain=True)
            mock_console.print.assert_not_called()


# ---------------------------------------------------------------------------
# sql_main tests
# ---------------------------------------------------------------------------

class TestSqlMain:
    """Tests for sql_main callback invoked through the Typer app."""

    @patch("sup.commands.sql.sql_command")
    def test_invoked_without_subcommand_calls_sql_command(self, mock_sql_cmd):
        """When invoked without a subcommand, sql_main delegates to sql_command."""
        result = runner.invoke(app, ["SELECT 1"])
        assert result.exit_code == 0
        mock_sql_cmd.assert_called_once()

    @patch("sup.commands.sql.sql_command")
    def test_interactive_flag_via_cli(self, mock_sql_cmd):
        """--interactive flag is forwarded to sql_command."""
        result = runner.invoke(app, ["--interactive"])
        assert result.exit_code == 0
        mock_sql_cmd.assert_called_once()
        call_args = mock_sql_cmd.call_args
        assert call_args[0][1] is True or call_args.kwargs.get("interactive") is True

    @patch("sup.commands.sql.sql_command")
    def test_subcommand_present_skips_sql_command(self, mock_sql_cmd):
        """When ctx.invoked_subcommand is set, sql_main does NOT call sql_command."""
        # Call sql_main directly with a mock context that has a subcommand
        mock_ctx = MagicMock()
        mock_ctx.invoked_subcommand = "some_subcommand"

        sql_main(ctx=mock_ctx)

        mock_sql_cmd.assert_not_called()
