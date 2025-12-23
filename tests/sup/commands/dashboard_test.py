"""
Tests for ``sup.commands.dashboard``.
"""

# pylint: disable=redefined-outer-name, invalid-name

from typing import Any, Dict, List
from unittest.mock import MagicMock

import pytest
from typer.testing import CliRunner
from pytest_mock import MockerFixture

from sup.commands.dashboard import app


@pytest.fixture
def mock_sup_context(mocker: MockerFixture) -> MagicMock:
    """
    Fixture that mocks SupContext for use in dashboard command tests.

    This fixture can be reused in other command tests as well.
    """
    # Patch SupContext where it's imported (inside the function)
    mock_ctx = mocker.patch("sup.config.settings.SupContext")
    mock_instance = MagicMock()
    mock_ctx.return_value = mock_instance

    # Set default return values
    mock_instance.get_workspace_hostname.return_value = "test-workspace.preset.io"

    return mock_instance


@pytest.fixture
def mock_superset_client(mocker: MockerFixture, mock_sup_context: MagicMock) -> MagicMock:
    """
    Fixture that mocks SupSupersetClient for use in dashboard command tests.

    This fixture can be reused in other command tests as well.
    """
    # Patch SupSupersetClient where it's imported (inside the function)
    mock_client_class = mocker.patch("sup.clients.superset.SupSupersetClient")
    mock_client_instance = MagicMock()
    mock_client_class.from_context.return_value = mock_client_instance

    # Set default return value for get_dashboards
    mock_client_instance.get_dashboards.return_value = []

    return mock_client_instance


@pytest.fixture
def sample_dashboards() -> List[Dict[str, Any]]:
    """
    Sample dashboard data for testing.

    This fixture can be reused in other dashboard tests.
    """
    return [
        {
            "id": 1,
            "dashboard_title": "Sales Dashboard",
            "published": True,
            "created_on_delta_humanized": "2 days ago",
            "slug": "sales-dashboard",
        },
        {
            "id": 2,
            "dashboard_title": "Marketing Dashboard",
            "published": False,
            "created_on_delta_humanized": "5 days ago",
            "slug": "marketing-dashboard",
        },
    ]


def test_list_dashboards_basic(
    mocker: MockerFixture,
    mock_sup_context: MagicMock,
    mock_superset_client: MagicMock,
    sample_dashboards: List[Dict[str, Any]],
) -> None:
    """
    Test the basic functionality of ``list_dashboards`` command.
    """

    # Mock the spinner to avoid console output during tests
    mock_spinner = mocker.patch("sup.output.spinners.data_spinner")
    mock_spinner.return_value.__enter__.return_value = None

    # Mock console to capture output
    mock_console = mocker.patch("sup.commands.dashboard.console")

    # Mock display_dashboards_table to avoid Rich table rendering
    mock_display_table = mocker.patch("sup.commands.dashboard.display_dashboards_table")

    # Set up mock return values
    mock_superset_client.get_dashboards.return_value = sample_dashboards

    # Run the command
    runner = CliRunner()
    result = runner.invoke(app, ["list"], catch_exceptions=False)

    # Assertions
    assert result.exit_code == 0

    # Verify SupContext was instantiated (at least once)
    from sup.config.settings import SupContext

    assert SupContext.call_count >= 1

    # Verify client was created from context
    from sup.clients.superset import SupSupersetClient

    SupSupersetClient.from_context.assert_called_once_with(mock_sup_context, None)

    # Verify get_dashboards was called with correct parameters
    mock_superset_client.get_dashboards.assert_called_once_with(
        silent=True,
        limit=None,
        text_search=None,
    )

    # Verify display_dashboards_table was called with correct parameters
    mock_display_table.assert_called_once_with(
        sample_dashboards,
        "test-workspace.preset.io",
    )


def test_list_dashboards_with_filters(
    mocker: MockerFixture,
    mock_sup_context: MagicMock,
    mock_superset_client: MagicMock,
    sample_dashboards: List[Dict[str, Any]],
) -> None:
    """
    Test ``list_dashboards`` with various filter options.
    """
    # Mock the spinner
    mock_spinner = mocker.patch("sup.output.spinners.data_spinner")
    mock_spinner.return_value.__enter__.return_value = None

    # Mock console
    mocker.patch("sup.commands.dashboard.console")

    # Mock display_dashboards_table
    mocker.patch("sup.commands.dashboard.display_dashboards_table")

    # Set up mock return values
    mock_superset_client.get_dashboards.return_value = sample_dashboards

    # Run the command with filters
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["list", "--search", "sales", "--limit", "10"],
        catch_exceptions=False,
    )

    # Assertions
    assert result.exit_code == 0

    # Verify get_dashboards was called with filter parameters
    mock_superset_client.get_dashboards.assert_called_once_with(
        silent=True,
        limit=10,
        text_search="sales",
    )


def test_list_dashboards_porcelain_output(
    mocker: MockerFixture,
    mock_sup_context: MagicMock,
    mock_superset_client: MagicMock,
    sample_dashboards: List[Dict[str, Any]],
) -> None:
    """
    Test ``list_dashboards`` with porcelain output format.
    """
    # Mock the spinner
    mock_spinner = mocker.patch("sup.output.spinners.data_spinner")
    mock_spinner.return_value.__enter__.return_value = None

    # Capture print output from display_porcelain_list
    printed_lines = []

    def capture_print(*args, **kwargs):
        # Join all args with space (print's default separator)
        # But display_porcelain_list uses \t.join, so args[0] should be the full line
        if args:
            printed_lines.append(str(args[0]) if len(args) == 1 else " ".join(str(arg) for arg in args))

    mock_print = mocker.patch("sup.output.formatters.print", side_effect=capture_print)

    # Set up mock return values
    mock_superset_client.get_dashboards.return_value = sample_dashboards

    # Run the command with porcelain flag
    runner = CliRunner()
    result = runner.invoke(app, ["list", "--porcelain"], catch_exceptions=False)

    # Assertions
    assert result.exit_code == 0

    # Verify output format: tab-separated values
    assert len(printed_lines) == 2, f"Expected 2 lines, got {len(printed_lines)}: {printed_lines}"

    # Verify first line: "1	Sales Dashboard	True	2 days ago"
    line1_parts = printed_lines[0].split("\t")
    assert len(line1_parts) == 4, f"Expected 4 tab-separated fields, got {len(line1_parts)}: {line1_parts}"
    assert line1_parts[0] == "1"
    assert line1_parts[1] == "Sales Dashboard"
    assert line1_parts[2] == "True"
    assert line1_parts[3] == "2 days ago"

    # Verify second line: "2	Marketing Dashboard	False	5 days ago"
    line2_parts = printed_lines[1].split("\t")
    assert len(line2_parts) == 4, f"Expected 4 tab-separated fields, got {len(line2_parts)}: {line2_parts}"
    assert line2_parts[0] == "2"
    assert line2_parts[1] == "Marketing Dashboard"
    assert line2_parts[2] == "False"
    assert line2_parts[3] == "5 days ago"


def test_list_dashboards_json_output(
    mocker: MockerFixture,
    mock_sup_context: MagicMock,
    mock_superset_client: MagicMock,
    sample_dashboards: List[Dict[str, Any]],
) -> None:
    """
    Test ``list_dashboards`` with JSON output format.
    """
    # Mock the spinner
    mock_spinner = mocker.patch("sup.output.spinners.data_spinner")
    mock_spinner.return_value.__enter__.return_value = None

    # Mock console.print to capture JSON output
    mock_console_print = mocker.patch("sup.commands.dashboard.console.print")

    # Set up mock return values
    mock_superset_client.get_dashboards.return_value = sample_dashboards

    # Run the command with JSON flag
    runner = CliRunner()
    result = runner.invoke(app, ["list", "--json"], catch_exceptions=False)

    # Assertions
    assert result.exit_code == 0

    # Verify console.print was called (for JSON output)
    assert mock_console_print.called

    # Verify the output contains JSON (check first call's args)
    import json

    call_args = mock_console_print.call_args_list
    json_output = call_args[0][0][0] if call_args else ""

    # Verify it's valid JSON
    parsed = json.loads(json_output)
    assert isinstance(parsed, list)
    assert len(parsed) == len(sample_dashboards)
