"""
Tests for the sup user export/import/invite commands.
"""

from unittest.mock import patch

import yaml
from typer.testing import CliRunner

from sup.commands.user import app

runner = CliRunner()

SAMPLE_USERS_SIMPLE = [
    {
        "email": "user1@example.com",
        "first_name": "User",
        "last_name": "One",
        "username": "user1",
    },
    {
        "email": "user2@example.com",
        "first_name": "User",
        "last_name": "Two",
        "username": "user2",
    },
]

SAMPLE_USERS_WORKSPACE_ROLES = [
    {
        "email": "admin@example.com",
        "first_name": "Admin",
        "last_name": "User",
        "username": "admin",
        "workspaces": {
            "Team/Workspace1": {
                "workspace_role": "workspace admin",
                "workspace_name": "workspace1",
                "team": "Team",
            },
        },
    },
]

PATCH_PRESET_CLIENT = "preset_cli.api.clients.preset.PresetClient"
PATCH_AUTH = "sup.auth.preset.get_preset_auth"
PATCH_CONTEXT = "sup.config.settings.SupContext"


# --- Export tests ---


@patch("preset_cli.cli.export_users.process_team_workspaces")
@patch("preset_cli.cli.export_users.process_team_members")
@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_export_users(_MockContext, _MockAuth, MockClient, _mock_members, _mock_workspaces):
    """Test exporting users to a YAML file."""
    mock_client = MockClient.return_value
    mock_client.get_teams.return_value = [{"name": "team1", "title": "Team 1"}]

    with runner.isolated_filesystem():
        result = runner.invoke(app, ["export", "users.yaml"])
        assert result.exit_code == 0


@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_export_users_no_teams(_MockContext, _MockAuth, MockClient):
    """Test exporting when no teams found."""
    mock_client = MockClient.return_value
    mock_client.get_teams.return_value = []

    result = runner.invoke(app, ["export"])
    assert result.exit_code == 0
    assert "No teams" in result.output


# --- Import tests ---


@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_import_users_simple(_MockContext, _MockAuth, MockClient):
    """Test importing users in simple format."""
    mock_client = MockClient.return_value
    mock_client.get_teams.return_value = [{"name": "team1", "title": "Team 1"}]

    with runner.isolated_filesystem():
        with open("users.yaml", "w") as f:
            yaml.dump(SAMPLE_USERS_SIMPLE, f)

        result = runner.invoke(app, ["import", "users.yaml"])
        assert result.exit_code == 0

    mock_client.import_users.assert_called_once()


@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_import_users_workspace_roles(_MockContext, _MockAuth, MockClient):
    """Test importing users with workspace roles format."""
    mock_client = MockClient.return_value
    mock_client.get_teams.return_value = [{"name": "team1", "title": "Team 1"}]
    mock_client.get_team_members.return_value = [
        {"user": {"email": "admin@example.com", "id": 1}},
    ]
    mock_client.get_workspaces.return_value = [
        {"name": "workspace1", "id": 100, "title": "Workspace1"},
    ]

    with runner.isolated_filesystem():
        with open("users.yaml", "w") as f:
            yaml.dump(SAMPLE_USERS_WORKSPACE_ROLES, f)

        result = runner.invoke(app, ["import", "users.yaml"])
        assert result.exit_code == 0


def test_import_users_dry_run():
    """Test importing with --dry-run."""
    with runner.isolated_filesystem():
        with open("users.yaml", "w") as f:
            yaml.dump(SAMPLE_USERS_SIMPLE, f)

        result = runner.invoke(app, ["import", "users.yaml", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "user1@example.com" in result.output


def test_import_users_file_not_found():
    """Test importing from non-existent file."""
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["import", "nonexistent.yaml"])
        assert result.exit_code == 1


# --- Invite tests ---


@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_invite_users(_MockContext, _MockAuth, MockClient):
    """Test inviting users from a YAML file."""
    mock_client = MockClient.return_value
    mock_client.get_teams.return_value = [{"name": "team1", "title": "Team 1"}]

    with runner.isolated_filesystem():
        with open("users.yaml", "w") as f:
            yaml.dump(SAMPLE_USERS_SIMPLE, f)

        result = runner.invoke(app, ["invite", "users.yaml"])
        assert result.exit_code == 0

    mock_client.invite_users.assert_called_once_with(
        ["team1"],
        ["user1@example.com", "user2@example.com"],
    )


def test_invite_users_dry_run():
    """Test inviting with --dry-run."""
    with runner.isolated_filesystem():
        with open("users.yaml", "w") as f:
            yaml.dump(SAMPLE_USERS_SIMPLE, f)

        result = runner.invoke(app, ["invite", "users.yaml", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "user1@example.com" in result.output


def test_invite_users_file_not_found():
    """Test inviting from non-existent file."""
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["invite", "nonexistent.yaml"])
        assert result.exit_code == 1


@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_invite_users_with_team(_MockContext, _MockAuth, MockClient):
    """Test inviting users to a specific team."""
    mock_client = MockClient.return_value
    mock_client.get_teams.return_value = [{"name": "team1", "title": "My Team"}]

    with runner.isolated_filesystem():
        with open("users.yaml", "w") as f:
            yaml.dump(SAMPLE_USERS_SIMPLE, f)

        result = runner.invoke(app, ["invite", "users.yaml", "--team", "My Team"])
        assert result.exit_code == 0

    mock_client.invite_users.assert_called_once_with(
        ["team1"],
        ["user1@example.com", "user2@example.com"],
    )
