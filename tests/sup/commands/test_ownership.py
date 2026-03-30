"""Tests for the sup ownership export/import commands."""

from unittest.mock import MagicMock, patch
from uuid import UUID

import yaml
from typer.testing import CliRunner

from sup.commands.ownership import app

runner = CliRunner()

SAMPLE_OWNERSHIP = {
    "dataset": [
        {
            "name": "test_table",
            "uuid": "e4e6a14b-c3e8-4fdf-a850-183ba6ce15e0",
            "owners": ["admin@example.com"],
        },
    ],
    "chart": [
        {
            "name": "test_chart",
            "uuid": "f5f7b25c-d4f9-5eef-b961-294cb7df26f1",
            "owners": ["admin@example.com", "user@example.com"],
        },
    ],
}

PATCH_CLIENT = "sup.clients.superset.SupSupersetClient"
PATCH_CONTEXT = "sup.config.settings.SupContext"


def _mock_export_ownership(resource_name):
    data = {
        "dataset": [
            {
                "name": "test_table",
                "uuid": UUID("e4e6a14b-c3e8-4fdf-a850-183ba6ce15e0"),
                "owners": ["admin@example.com"],
            }
        ],
        "chart": [
            {
                "name": "test_chart",
                "uuid": UUID("f5f7b25c-d4f9-5eef-b961-294cb7df26f1"),
                "owners": ["admin@example.com", "user@example.com"],
            }
        ],
        "dashboard": [],
    }
    return iter(data.get(resource_name, []))


# --- Export tests ---


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_ownership(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.export_ownership.side_effect = _mock_export_ownership
    MockClient.from_context.return_value = mock_client
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["export", "ownership.yaml"])
        assert result.exit_code == 0
        with open("ownership.yaml") as f:
            exported = yaml.safe_load(f)
        assert "dataset" in exported
        assert "chart" in exported


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_ownership_json(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.export_ownership.return_value = iter([])
    MockClient.from_context.return_value = mock_client
    result = runner.invoke(app, ["export", "--json"])
    assert result.exit_code == 0


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_ownership_yaml(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.export_ownership.side_effect = _mock_export_ownership
    MockClient.from_context.return_value = mock_client
    result = runner.invoke(app, ["export", "--yaml"])
    assert result.exit_code == 0
    assert "test_table" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_ownership_porcelain(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.export_ownership.side_effect = _mock_export_ownership
    MockClient.from_context.return_value = mock_client
    result = runner.invoke(app, ["export", "--porcelain"])
    assert result.exit_code == 0
    assert "dataset\ttest_table\t" in result.output
    assert "chart\ttest_chart\t" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_ownership_error(_MockContext, MockClient):
    MockClient.from_context.side_effect = RuntimeError("boom")
    result = runner.invoke(app, ["export"])
    assert result.exit_code == 1
    assert "Failed to export ownership" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_ownership_error_porcelain(_MockContext, MockClient):
    MockClient.from_context.side_effect = RuntimeError("boom")
    result = runner.invoke(app, ["export", "--porcelain"])
    assert result.exit_code == 1
    assert "Failed" not in result.output


# --- Import tests ---


def _setup_import_mocks(MockClient, mock_get_logs, import_side_effect=None):
    from preset_cli.cli.superset.lib import LogType

    mock_client = MagicMock()
    mock_client.client.export_users.return_value = [
        {"id": 1, "email": "admin@example.com"},
    ]
    mock_client.client.get_uuids.return_value = {
        1: UUID("e4e6a14b-c3e8-4fdf-a850-183ba6ce15e0"),
    }
    if import_side_effect:
        mock_client.client.import_ownership.side_effect = import_side_effect
    MockClient.from_context.return_value = mock_client
    mock_get_logs.return_value = (
        "progress.log",
        {LogType.OWNERSHIP: [], LogType.ASSETS: []},
    )
    return mock_client


@patch("preset_cli.cli.superset.lib.clean_logs")
@patch("preset_cli.cli.superset.lib.write_logs_to_file")
@patch("preset_cli.cli.superset.lib.get_logs")
@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_ownership(_MockContext, MockClient, mock_get_logs, _mock_write, _mock_clean):
    _setup_import_mocks(MockClient, mock_get_logs)
    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            yaml.dump(SAMPLE_OWNERSHIP, f)
        with open("progress.log", "w") as f:
            pass
        result = runner.invoke(app, ["import", "ownership.yaml"])
        assert result.exit_code == 0
    mock = MockClient.from_context.return_value
    assert mock.client.import_ownership.call_count == 2


@patch("preset_cli.cli.superset.lib.clean_logs")
@patch("preset_cli.cli.superset.lib.write_logs_to_file")
@patch("preset_cli.cli.superset.lib.get_logs")
@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_ownership_porcelain(
    _MockContext, MockClient, mock_get_logs, _mock_write, _mock_clean
):
    _setup_import_mocks(MockClient, mock_get_logs)
    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            yaml.dump(SAMPLE_OWNERSHIP, f)
        with open("progress.log", "w") as f:
            pass
        result = runner.invoke(app, ["import", "ownership.yaml", "--porcelain"])
        assert result.exit_code == 0
        assert "imported:2" in result.output


@patch("preset_cli.cli.superset.lib.clean_logs")
@patch("preset_cli.cli.superset.lib.write_logs_to_file")
@patch("preset_cli.cli.superset.lib.get_logs")
@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_ownership_skip_checkpoint(
    _MockContext, MockClient, mock_get_logs, _mock_write, _mock_clean
):
    from preset_cli.cli.superset.lib import LogType

    mock_client = MagicMock()
    mock_client.client.export_users.return_value = [
        {"id": 1, "email": "admin@example.com"},
    ]
    mock_client.client.get_uuids.return_value = {
        1: UUID("e4e6a14b-c3e8-4fdf-a850-183ba6ce15e0"),
    }
    MockClient.from_context.return_value = mock_client
    mock_get_logs.return_value = (
        "progress.log",
        {
            LogType.OWNERSHIP: [
                {"uuid": "e4e6a14b-c3e8-4fdf-a850-183ba6ce15e0", "status": "SUCCESS"}
            ],
            LogType.ASSETS: [],
        },
    )
    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            yaml.dump(SAMPLE_OWNERSHIP, f)
        with open("progress.log", "w") as f:
            pass
        result = runner.invoke(app, ["import", "ownership.yaml"])
        assert result.exit_code == 0
    assert mock_client.client.import_ownership.call_count == 1


@patch("preset_cli.cli.superset.lib.clean_logs")
@patch("preset_cli.cli.superset.lib.write_logs_to_file")
@patch("preset_cli.cli.superset.lib.get_logs")
@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_ownership_continue_on_error(
    _MockContext, MockClient, mock_get_logs, _mock_write, mock_clean
):
    _setup_import_mocks(
        MockClient,
        mock_get_logs,
        import_side_effect=[None, RuntimeError("permission denied")],
    )
    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            yaml.dump(SAMPLE_OWNERSHIP, f)
        with open("progress.log", "w") as f:
            pass
        result = runner.invoke(app, ["import", "ownership.yaml", "--continue-on-error"])
        assert result.exit_code == 0
        assert "1 failed" in result.output
    mock_clean.assert_not_called()


@patch("preset_cli.cli.superset.lib.clean_logs")
@patch("preset_cli.cli.superset.lib.write_logs_to_file")
@patch("preset_cli.cli.superset.lib.get_logs")
@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_ownership_continue_on_error_porcelain(
    _MockContext, MockClient, mock_get_logs, _mock_write, _mock_clean
):
    _setup_import_mocks(
        MockClient,
        mock_get_logs,
        import_side_effect=[None, RuntimeError("permission denied")],
    )
    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            yaml.dump(SAMPLE_OWNERSHIP, f)
        with open("progress.log", "w") as f:
            pass
        result = runner.invoke(
            app,
            ["import", "ownership.yaml", "--continue-on-error", "--porcelain"],
        )
        assert result.exit_code == 0
        assert "imported:1" in result.output
        assert "failed:1" in result.output


@patch("preset_cli.cli.superset.lib.clean_logs")
@patch("preset_cli.cli.superset.lib.write_logs_to_file")
@patch("preset_cli.cli.superset.lib.get_logs")
@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_ownership_error_no_continue(
    _MockContext, MockClient, mock_get_logs, _mock_write, _mock_clean
):
    _setup_import_mocks(
        MockClient,
        mock_get_logs,
        import_side_effect=RuntimeError("server error"),
    )
    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            yaml.dump(SAMPLE_OWNERSHIP, f)
        with open("progress.log", "w") as f:
            pass
        result = runner.invoke(app, ["import", "ownership.yaml"])
        assert result.exit_code == 1
        assert "Failed to import ownership" in result.output


@patch("preset_cli.cli.superset.lib.clean_logs")
@patch("preset_cli.cli.superset.lib.write_logs_to_file")
@patch("preset_cli.cli.superset.lib.get_logs")
@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_ownership_error_porcelain(
    _MockContext, MockClient, mock_get_logs, _mock_write, _mock_clean
):
    _setup_import_mocks(
        MockClient,
        mock_get_logs,
        import_side_effect=RuntimeError("server error"),
    )
    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            yaml.dump(SAMPLE_OWNERSHIP, f)
        with open("progress.log", "w") as f:
            pass
        result = runner.invoke(app, ["import", "ownership.yaml", "--porcelain"])
        assert result.exit_code == 1
        assert "Failed" not in result.output


def test_import_ownership_dry_run():
    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            yaml.dump(SAMPLE_OWNERSHIP, f)
        result = runner.invoke(app, ["import", "ownership.yaml", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output


def test_import_ownership_dry_run_porcelain():
    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            yaml.dump(SAMPLE_OWNERSHIP, f)
        result = runner.invoke(app, ["import", "ownership.yaml", "--dry-run", "--porcelain"])
        assert result.exit_code == 0
        assert "import\tdataset\ttest_table" in result.output
        assert "import\tchart\ttest_chart" in result.output


def test_import_ownership_file_not_found():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["import", "nonexistent.yaml"])
        assert result.exit_code == 1


def test_import_ownership_file_not_found_porcelain():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["import", "nonexistent.yaml", "--porcelain"])
        assert result.exit_code == 1
        assert "File not found" not in result.output


def test_import_ownership_empty_file():
    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            f.write("")
        result = runner.invoke(app, ["import", "ownership.yaml"])
        assert result.exit_code == 0
        assert "No ownership data" in result.output


def test_import_ownership_empty_file_porcelain():
    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            f.write("")
        result = runner.invoke(app, ["import", "ownership.yaml", "--porcelain"])
        assert result.exit_code == 0


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_ownership_typer_exit(_MockContext, MockClient):
    """Cover except typer.Exit: raise in export."""
    import typer

    MockClient.from_context.side_effect = typer.Exit(1)
    result = runner.invoke(app, ["export"])
    assert result.exit_code == 1


@patch("preset_cli.cli.superset.lib.clean_logs")
@patch("preset_cli.cli.superset.lib.write_logs_to_file")
@patch("preset_cli.cli.superset.lib.get_logs")
@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_ownership_typer_exit(
    _MockContext, MockClient, mock_get_logs, _mock_write, _mock_clean
):
    """Cover except typer.Exit: raise in import."""
    import typer

    MockClient.from_context.side_effect = typer.Exit(1)
    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            yaml.dump(SAMPLE_OWNERSHIP, f)
        result = runner.invoke(app, ["import", "ownership.yaml"])
        assert result.exit_code == 1


@patch("preset_cli.cli.superset.lib.clean_logs")
@patch("preset_cli.cli.superset.lib.write_logs_to_file")
@patch("preset_cli.cli.superset.lib.get_logs")
@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_ownership_continue_on_error_all_success(
    _MockContext, MockClient, mock_get_logs, _mock_write, mock_clean
):
    """Cover clean_logs path when continue_on_error=True and all succeed."""
    _setup_import_mocks(MockClient, mock_get_logs)
    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            yaml.dump(SAMPLE_OWNERSHIP, f)
        with open("progress.log", "w") as f:
            pass
        result = runner.invoke(app, ["import", "ownership.yaml", "--continue-on-error"])
        assert result.exit_code == 0
    mock_clean.assert_called_once()
