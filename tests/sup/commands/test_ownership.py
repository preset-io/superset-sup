"""
Tests for the sup ownership export/import commands.
"""

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


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_ownership(_MockContext, MockClient):
    """Test exporting ownership to a YAML file."""
    mock_client = MagicMock()

    def mock_export_ownership(resource_name):
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

    mock_client.client.export_ownership.side_effect = mock_export_ownership
    MockClient.from_context.return_value = mock_client

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["export", "ownership.yaml"])
        assert result.exit_code == 0

        with open("ownership.yaml") as f:
            exported = yaml.safe_load(f)
        assert "dataset" in exported
        assert "chart" in exported
        assert len(exported["dataset"]) == 1
        assert exported["dataset"][0]["name"] == "test_table"


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_ownership_json(_MockContext, MockClient):
    """Test exporting ownership as JSON."""
    mock_client = MagicMock()
    mock_client.client.export_ownership.return_value = iter([])
    MockClient.from_context.return_value = mock_client

    result = runner.invoke(app, ["export", "--json"])
    assert result.exit_code == 0


@patch("preset_cli.cli.superset.lib.clean_logs")
@patch("preset_cli.cli.superset.lib.write_logs_to_file")
@patch("preset_cli.cli.superset.lib.get_logs")
@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_ownership(
    _MockContext, MockClient, mock_get_logs, _mock_write_logs, _mock_clean_logs
):
    """Test importing ownership from a YAML file."""
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
        {LogType.OWNERSHIP: [], LogType.ASSETS: []},
    )

    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            yaml.dump(SAMPLE_OWNERSHIP, f)

        # Create the progress.log file that get_logs returns
        with open("progress.log", "w") as f:
            pass

        result = runner.invoke(app, ["import", "ownership.yaml"])
        assert result.exit_code == 0

    assert mock_client.client.import_ownership.call_count == 2


def test_import_ownership_dry_run():
    """Test importing ownership with --dry-run."""
    with runner.isolated_filesystem():
        with open("ownership.yaml", "w") as f:
            yaml.dump(SAMPLE_OWNERSHIP, f)

        result = runner.invoke(app, ["import", "ownership.yaml", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output


def test_import_ownership_file_not_found():
    """Test importing from non-existent file."""
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["import", "nonexistent.yaml"])
        assert result.exit_code == 1
