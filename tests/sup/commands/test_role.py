"""
Tests for the sup role export/import/sync commands.
"""

from unittest.mock import MagicMock, patch

import yaml
from typer.testing import CliRunner

from sup.commands.role import app

runner = CliRunner()

SAMPLE_ROLES = [
    {
        "name": "Admin",
        "permissions": ["can read on Database", "can write on Database"],
    },
    {
        "name": "Gamma",
        "permissions": ["can read on Database"],
    },
]

SAMPLE_USER_ROLES = [
    {
        "email": "user1@example.com",
        "team_role": "admin",
        "workspaces": {
            "Workspace 1": {
                "workspace_role": "primary creator",
            },
        },
    },
]

PATCH_CLIENT = "sup.clients.superset.SupSupersetClient"
PATCH_CONTEXT = "sup.config.settings.SupContext"
PATCH_PRESET_CLIENT = "preset_cli.api.clients.preset.PresetClient"
PATCH_AUTH = "sup.auth.preset.get_preset_auth"


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_roles(_MockContext, MockClient):
    """Test exporting roles to a YAML file."""
    mock_client = MagicMock()
    mock_client.client.export_roles.return_value = iter(SAMPLE_ROLES)
    MockClient.from_context.return_value = mock_client

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["export", "roles.yaml"])
        assert result.exit_code == 0

        with open("roles.yaml") as f:
            exported = yaml.safe_load(f)
        assert len(exported) == 2
        assert exported[0]["name"] == "Admin"


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_roles_json(_MockContext, MockClient):
    """Test exporting roles as JSON to stdout."""
    mock_client = MagicMock()
    mock_client.client.export_roles.return_value = iter(SAMPLE_ROLES)
    MockClient.from_context.return_value = mock_client

    result = runner.invoke(app, ["export", "--json"])
    assert result.exit_code == 0
    assert "Admin" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_export_roles_porcelain(_MockContext, MockClient):
    """Test exporting roles in porcelain mode."""
    mock_client = MagicMock()
    mock_client.client.export_roles.return_value = iter(SAMPLE_ROLES)
    MockClient.from_context.return_value = mock_client

    result = runner.invoke(app, ["export", "--porcelain"])
    assert result.exit_code == 0
    assert "Admin\t2" in result.output
    assert "Gamma\t1" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_import_roles(_MockContext, MockClient):
    """Test importing roles from a YAML file."""
    mock_client = MagicMock()
    MockClient.from_context.return_value = mock_client

    with runner.isolated_filesystem():
        with open("roles.yaml", "w") as f:
            yaml.dump(SAMPLE_ROLES, f)

        result = runner.invoke(app, ["import", "roles.yaml"])
        assert result.exit_code == 0

    assert mock_client.client.import_role.call_count == 2
    mock_client.client.import_role.assert_any_call(SAMPLE_ROLES[0])
    mock_client.client.import_role.assert_any_call(SAMPLE_ROLES[1])


def test_import_roles_dry_run():
    """Test importing roles with --dry-run."""
    with runner.isolated_filesystem():
        with open("roles.yaml", "w") as f:
            yaml.dump(SAMPLE_ROLES, f)

        result = runner.invoke(app, ["import", "roles.yaml", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output


def test_import_roles_file_not_found():
    """Test importing from non-existent file."""
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["import", "nonexistent.yaml"])
        assert result.exit_code == 1


# --- Sync tests ---


@patch("preset_cli.cli.main.sync_all_user_roles_to_team")
@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_sync_roles(_MockContext, _MockAuth, MockClient, mock_sync_all):
    """Test syncing user roles."""
    mock_client = MockClient.return_value
    mock_client.get_teams.return_value = [{"name": "team1", "title": "Team 1"}]
    mock_client.get_workspaces.return_value = [
        {"name": "ws1", "title": "Workspace 1", "id": 100, "hostname": "ws1.preset.io"},
    ]

    with runner.isolated_filesystem():
        with open("user_roles.yaml", "w") as f:
            yaml.dump(SAMPLE_USER_ROLES, f)

        result = runner.invoke(app, ["sync", "user_roles.yaml"])
        assert result.exit_code == 0

    mock_sync_all.assert_called_once()


def test_sync_roles_dry_run():
    """Test syncing with --dry-run."""
    with runner.isolated_filesystem():
        with open("user_roles.yaml", "w") as f:
            yaml.dump(SAMPLE_USER_ROLES, f)

        result = runner.invoke(app, ["sync", "user_roles.yaml", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "user1@example.com" in result.output


def test_sync_roles_file_not_found():
    """Test syncing from non-existent file."""
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["sync", "nonexistent.yaml"])
        assert result.exit_code == 1


@patch("preset_cli.cli.main.sync_all_user_roles_to_team")
@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_sync_roles_with_team(_MockContext, _MockAuth, MockClient, mock_sync_all):
    """Test syncing to a specific team."""
    mock_client = MockClient.return_value
    mock_client.get_teams.return_value = [{"name": "team1", "title": "My Team"}]
    mock_client.get_workspaces.return_value = []

    with runner.isolated_filesystem():
        with open("user_roles.yaml", "w") as f:
            yaml.dump(SAMPLE_USER_ROLES, f)

        result = runner.invoke(app, ["sync", "user_roles.yaml", "--team", "My Team"])
        assert result.exit_code == 0

    mock_sync_all.assert_called_once()
