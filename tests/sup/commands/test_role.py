"""Tests for the sup role pull/push/sync commands."""

from unittest.mock import MagicMock, patch

import yaml
from typer.testing import CliRunner

from sup.commands.role import _resolve_teams, app

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
def test_pull_roles(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.export_roles.return_value = iter(SAMPLE_ROLES)
    MockClient.from_context.return_value = mock_client
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["pull", "roles.yaml"])
        assert result.exit_code == 0
        with open("roles.yaml") as f:
            pulled = yaml.safe_load(f)
        assert len(pulled) == 2
        assert pulled[0]["name"] == "Admin"


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_pull_roles_json(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.export_roles.return_value = iter(SAMPLE_ROLES)
    MockClient.from_context.return_value = mock_client
    result = runner.invoke(app, ["pull", "--json"])
    assert result.exit_code == 0
    assert "Admin" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_pull_roles_yaml(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.export_roles.return_value = iter(SAMPLE_ROLES)
    MockClient.from_context.return_value = mock_client
    result = runner.invoke(app, ["pull", "--yaml"])
    assert result.exit_code == 0
    assert "Admin" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_pull_roles_porcelain(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.export_roles.return_value = iter(SAMPLE_ROLES)
    MockClient.from_context.return_value = mock_client
    result = runner.invoke(app, ["pull", "--porcelain"])
    assert result.exit_code == 0
    assert "Admin\t2" in result.output
    assert "Gamma\t1" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_pull_roles_error(_MockContext, MockClient):
    MockClient.from_context.side_effect = RuntimeError("boom")
    result = runner.invoke(app, ["pull"])
    assert result.exit_code == 1
    assert "Failed to pull roles" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_pull_roles_error_porcelain(_MockContext, MockClient):
    MockClient.from_context.side_effect = RuntimeError("boom")
    result = runner.invoke(app, ["pull", "--porcelain"])
    assert result.exit_code == 1
    assert "Failed" not in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_push_roles(_MockContext, MockClient):
    mock_client = MagicMock()
    MockClient.from_context.return_value = mock_client
    with runner.isolated_filesystem():
        with open("roles.yaml", "w") as f:
            yaml.dump(SAMPLE_ROLES, f)
        result = runner.invoke(app, ["push", "roles.yaml"])
        assert result.exit_code == 0
    assert mock_client.client.import_role.call_count == 2


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_push_roles_porcelain(_MockContext, MockClient):
    mock_client = MagicMock()
    MockClient.from_context.return_value = mock_client
    with runner.isolated_filesystem():
        with open("roles.yaml", "w") as f:
            yaml.dump(SAMPLE_ROLES, f)
        result = runner.invoke(app, ["push", "roles.yaml", "--porcelain"])
        assert result.exit_code == 0
        assert "pushed:2" in result.output


def test_push_roles_dry_run():
    with runner.isolated_filesystem():
        with open("roles.yaml", "w") as f:
            yaml.dump(SAMPLE_ROLES, f)
        result = runner.invoke(app, ["push", "roles.yaml", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output


def test_push_roles_dry_run_porcelain():
    with runner.isolated_filesystem():
        with open("roles.yaml", "w") as f:
            yaml.dump(SAMPLE_ROLES, f)
        result = runner.invoke(app, ["push", "roles.yaml", "--dry-run", "--porcelain"])
        assert result.exit_code == 0
        assert "import\tAdmin" in result.output


def test_push_roles_file_not_found():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["push", "nonexistent.yaml"])
        assert result.exit_code == 1


def test_push_roles_file_not_found_porcelain():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["push", "nonexistent.yaml", "--porcelain"])
        assert result.exit_code == 1
        assert "File not found" not in result.output


def test_push_roles_empty_file():
    with runner.isolated_filesystem():
        with open("roles.yaml", "w") as f:
            f.write("")
        result = runner.invoke(app, ["push", "roles.yaml"])
        assert result.exit_code == 0
        assert "No roles found" in result.output


def test_push_roles_empty_file_porcelain():
    with runner.isolated_filesystem():
        with open("roles.yaml", "w") as f:
            f.write("")
        result = runner.invoke(app, ["push", "roles.yaml", "--porcelain"])
        assert result.exit_code == 0


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_push_roles_error(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.import_role.side_effect = RuntimeError("boom")
    MockClient.from_context.return_value = mock_client
    with runner.isolated_filesystem():
        with open("roles.yaml", "w") as f:
            yaml.dump(SAMPLE_ROLES, f)
        result = runner.invoke(app, ["push", "roles.yaml"])
        assert result.exit_code == 1
        assert "Failed to push roles" in result.output


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_push_roles_error_porcelain(_MockContext, MockClient):
    mock_client = MagicMock()
    mock_client.client.import_role.side_effect = RuntimeError("boom")
    MockClient.from_context.return_value = mock_client
    with runner.isolated_filesystem():
        with open("roles.yaml", "w") as f:
            yaml.dump(SAMPLE_ROLES, f)
        result = runner.invoke(app, ["push", "roles.yaml", "--porcelain"])
        assert result.exit_code == 1
        assert "Failed" not in result.output


# --- Sync tests ---


@patch("preset_cli.cli.main.sync_all_user_roles_to_team")
@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_sync_roles(_MockContext, _MockAuth, MockClient, mock_sync_all):
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


@patch("preset_cli.cli.main.sync_all_user_roles_to_team")
@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_sync_roles_porcelain(_MockContext, _MockAuth, MockClient, mock_sync_all):
    mock_client = MockClient.return_value
    mock_client.get_teams.return_value = [{"name": "team1", "title": "Team 1"}]
    mock_client.get_workspaces.return_value = []
    with runner.isolated_filesystem():
        with open("user_roles.yaml", "w") as f:
            yaml.dump(SAMPLE_USER_ROLES, f)
        result = runner.invoke(app, ["sync", "user_roles.yaml", "--porcelain"])
        assert result.exit_code == 0
        assert "synced:1" in result.output


def test_sync_roles_dry_run():
    with runner.isolated_filesystem():
        with open("user_roles.yaml", "w") as f:
            yaml.dump(SAMPLE_USER_ROLES, f)
        result = runner.invoke(app, ["sync", "user_roles.yaml", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output
        assert "user1@example.com" in result.output


def test_sync_roles_dry_run_porcelain():
    with runner.isolated_filesystem():
        with open("user_roles.yaml", "w") as f:
            yaml.dump(SAMPLE_USER_ROLES, f)
        result = runner.invoke(app, ["sync", "user_roles.yaml", "--dry-run", "--porcelain"])
        assert result.exit_code == 0
        assert "sync\tuser1@example.com" in result.output


def test_sync_roles_file_not_found():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["sync", "nonexistent.yaml"])
        assert result.exit_code == 1


def test_sync_roles_file_not_found_porcelain():
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["sync", "nonexistent.yaml", "--porcelain"])
        assert result.exit_code == 1
        assert "File not found" not in result.output


def test_sync_roles_empty_file():
    with runner.isolated_filesystem():
        with open("user_roles.yaml", "w") as f:
            f.write("")
        result = runner.invoke(app, ["sync", "user_roles.yaml"])
        assert result.exit_code == 0
        assert "No role definitions" in result.output


def test_sync_roles_empty_file_porcelain():
    with runner.isolated_filesystem():
        with open("user_roles.yaml", "w") as f:
            f.write("")
        result = runner.invoke(app, ["sync", "user_roles.yaml", "--porcelain"])
        assert result.exit_code == 0


@patch("preset_cli.cli.main.sync_all_user_roles_to_team")
@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_sync_roles_with_team(_MockContext, _MockAuth, MockClient, mock_sync_all):
    mock_client = MockClient.return_value
    mock_client.get_teams.return_value = [{"name": "team1", "title": "My Team"}]
    mock_client.get_workspaces.return_value = []
    with runner.isolated_filesystem():
        with open("user_roles.yaml", "w") as f:
            yaml.dump(SAMPLE_USER_ROLES, f)
        result = runner.invoke(app, ["sync", "user_roles.yaml", "--team", "My Team"])
        assert result.exit_code == 0
    mock_sync_all.assert_called_once()


@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_sync_roles_resolve_empty(_MockContext, _MockAuth, MockClient):
    mock_client = MockClient.return_value
    mock_client.get_teams.return_value = []
    with runner.isolated_filesystem():
        with open("user_roles.yaml", "w") as f:
            yaml.dump(SAMPLE_USER_ROLES, f)
        result = runner.invoke(app, ["sync", "user_roles.yaml"])
        assert result.exit_code == 0


@patch("preset_cli.cli.main.sync_all_user_roles_to_team")
@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_sync_roles_error(_MockContext, _MockAuth, MockClient, mock_sync_all):
    mock_client = MockClient.return_value
    mock_client.get_teams.return_value = [{"name": "team1", "title": "Team 1"}]
    mock_sync_all.side_effect = RuntimeError("sync failed")
    with runner.isolated_filesystem():
        with open("user_roles.yaml", "w") as f:
            yaml.dump(SAMPLE_USER_ROLES, f)
        result = runner.invoke(app, ["sync", "user_roles.yaml"])
        assert result.exit_code == 1
        assert "Failed to sync roles" in result.output


@patch("preset_cli.cli.main.sync_all_user_roles_to_team")
@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_sync_roles_error_porcelain(_MockContext, _MockAuth, MockClient, mock_sync_all):
    mock_client = MockClient.return_value
    mock_client.get_teams.return_value = [{"name": "team1", "title": "Team 1"}]
    mock_sync_all.side_effect = RuntimeError("sync failed")
    with runner.isolated_filesystem():
        with open("user_roles.yaml", "w") as f:
            yaml.dump(SAMPLE_USER_ROLES, f)
        result = runner.invoke(app, ["sync", "user_roles.yaml", "--porcelain"])
        assert result.exit_code == 1
        assert "Failed" not in result.output


# --- _resolve_teams tests ---


def test_resolve_teams_with_names():
    client = MagicMock()
    client.get_teams.return_value = [
        {"name": "team1", "title": "My Team"},
        {"name": "team2", "title": "Other"},
    ]
    result = _resolve_teams(client, ["My Team"], porcelain=False)
    assert result == ["team1"]


def test_resolve_teams_not_found():
    client = MagicMock()
    client.get_teams.return_value = [{"name": "team1", "title": "My Team"}]
    result = _resolve_teams(client, ["Nonexistent"], porcelain=False)
    assert result == []


def test_resolve_teams_no_teams():
    client = MagicMock()
    client.get_teams.return_value = []
    result = _resolve_teams(client, None, porcelain=False)
    assert result == []


def test_resolve_teams_no_teams_porcelain():
    client = MagicMock()
    client.get_teams.return_value = []
    result = _resolve_teams(client, None, porcelain=True)
    assert result == []


def test_resolve_teams_single():
    client = MagicMock()
    client.get_teams.return_value = [{"name": "team1", "title": "Only"}]
    result = _resolve_teams(client, None, porcelain=False)
    assert result == ["team1"]


@patch("sup.commands.role.typer.prompt", return_value="team1")
def test_resolve_teams_multiple_prompt(mock_prompt):
    client = MagicMock()
    client.get_teams.return_value = [
        {"name": "team1", "title": "A"},
        {"name": "team2", "title": "B"},
    ]
    result = _resolve_teams(client, None, porcelain=False)
    assert result == ["team1"]
    mock_prompt.assert_called_once()


def test_resolve_teams_multiple_porcelain():
    client = MagicMock()
    client.get_teams.return_value = [
        {"name": "team1", "title": "A"},
        {"name": "team2", "title": "B"},
    ]
    result = _resolve_teams(client, None, porcelain=True)
    assert result == ["team1", "team2"]


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_pull_roles_typer_exit(_MockContext, MockClient):
    """Cover except typer.Exit: raise in pull."""
    import typer

    MockClient.from_context.side_effect = typer.Exit(1)
    result = runner.invoke(app, ["pull"])
    assert result.exit_code == 1


@patch(PATCH_CLIENT)
@patch(PATCH_CONTEXT)
def test_push_roles_typer_exit(_MockContext, MockClient):
    """Cover except typer.Exit: raise in push."""
    import typer

    MockClient.from_context.side_effect = typer.Exit(1)
    with runner.isolated_filesystem():
        with open("roles.yaml", "w") as f:
            yaml.dump(SAMPLE_ROLES, f)
        result = runner.invoke(app, ["push", "roles.yaml"])
        assert result.exit_code == 1


@patch("preset_cli.cli.main.sync_all_user_roles_to_team")
@patch(PATCH_PRESET_CLIENT)
@patch(PATCH_AUTH)
@patch(PATCH_CONTEXT)
def test_sync_roles_typer_exit(_MockContext, _MockAuth, MockClient, mock_sync_all):
    """Cover except typer.Exit: raise in sync."""
    import typer

    mock_client = MockClient.return_value
    mock_client.get_teams.return_value = [{"name": "team1", "title": "Team 1"}]
    mock_sync_all.side_effect = typer.Exit(1)
    with runner.isolated_filesystem():
        with open("user_roles.yaml", "w") as f:
            yaml.dump(SAMPLE_USER_ROLES, f)
        result = runner.invoke(app, ["sync", "user_roles.yaml"])
        assert result.exit_code == 1
