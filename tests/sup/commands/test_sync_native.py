"""
Tests for the sup sync native command.
"""

import os
from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from sup.commands.sync import sync_native

test_app = typer.Typer()
test_app.command()(sync_native)

runner = CliRunner()

_CTX = "sup.config.settings.SupContext"
_PCLI = "sup.clients.preset.SupPresetClient"
_PAUTH = "sup.auth.preset.SupPresetAuth"
_NATIVE = "preset_cli.cli.superset.sync.native.command.native"


def _mock_ctx(target_workspace_id=None, workspace_id=42):
    m = MagicMock()
    m.get_target_workspace_id.return_value = target_workspace_id
    m.get_workspace_id.return_value = workspace_id
    return m


def _mock_preset_client(workspaces=None):
    cli = MagicMock()
    cli.get_all_workspaces.return_value = workspaces or []
    return cli


def test_sync_native_dir_not_found():
    """Test pushing from non-existent directory."""
    with runner.isolated_filesystem():
        result = runner.invoke(test_app, ["nonexistent_dir", "--force", "--porcelain"])
        assert result.exit_code == 1


def test_sync_native_not_a_directory():
    """Test pushing from a file instead of directory."""
    with runner.isolated_filesystem():
        with open("not_a_dir", "w") as f:
            f.write("hello")
        result = runner.invoke(test_app, ["not_a_dir", "--force", "--porcelain"])
        assert result.exit_code == 1


def test_sync_native_invalid_asset_type():
    """Test pushing with invalid asset type."""
    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(
            test_app,
            ["assets", "--asset-type", "invalid", "--force", "--porcelain"],
        )
        assert result.exit_code == 1


@patch(_CTX)
def test_sync_native_no_workspace(MockContext):
    """Test pushing without configured workspace."""
    mock_ctx = MockContext.return_value
    mock_ctx.get_target_workspace_id.return_value = None
    mock_ctx.get_workspace_id.return_value = None

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(
            test_app,
            ["assets", "--force", "--porcelain"],
        )
        assert result.exit_code == 1


@patch(_CTX)
def test_sync_native_fallback_to_source_workspace(MockContext):
    """Test fallback to source workspace when no target configured."""
    mock_ctx = MockContext.return_value
    mock_ctx.get_target_workspace_id.return_value = None
    mock_ctx.get_workspace_id.return_value = None

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(
            test_app,
            ["assets", "--force", "--porcelain"],
        )
        assert result.exit_code == 1
        mock_ctx.get_workspace_id.assert_called_once()


@patch(_NATIVE)
@patch(_PAUTH)
@patch(_PCLI)
@patch(_CTX)
def test_sync_native_success(MockContext, MockPresetClient, MockAuth, mock_native):
    """Test successful import invokes native() via click context."""
    MockContext.return_value = _mock_ctx(target_workspace_id=10)
    MockPresetClient.from_context.return_value = _mock_preset_client(
        workspaces=[{"id": 10, "hostname": "ws.preset.io"}]
    )
    MockAuth.from_sup_config.return_value = MagicMock()

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(
            test_app,
            ["assets", "--force", "--porcelain"],
        )
        assert result.exit_code == 0


@patch(_NATIVE)
@patch(_PAUTH)
@patch(_PCLI)
@patch(_CTX)
def test_sync_native_success_with_valid_asset_type(
    MockContext, MockPresetClient, MockAuth, mock_native
):
    """Test successful import with a valid --asset-type."""
    MockContext.return_value = _mock_ctx(target_workspace_id=10)
    MockPresetClient.from_context.return_value = _mock_preset_client(
        workspaces=[{"id": 10, "hostname": "ws.preset.io"}]
    )
    MockAuth.from_sup_config.return_value = MagicMock()

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(
            test_app,
            ["assets", "--asset-type", "chart", "--force", "--porcelain"],
        )
        assert result.exit_code == 0


@patch(_NATIVE)
@patch(_PAUTH)
@patch(_PCLI)
@patch(_CTX)
def test_sync_native_fallback_source_success(
    MockContext, MockPresetClient, MockAuth, mock_native
):
    """Test push uses source workspace when target is not set."""
    MockContext.return_value = _mock_ctx(target_workspace_id=None, workspace_id=42)
    MockPresetClient.from_context.return_value = _mock_preset_client(
        workspaces=[{"id": 42, "hostname": "ws.preset.io"}]
    )
    MockAuth.from_sup_config.return_value = MagicMock()

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(
            test_app,
            ["assets", "--force", "--porcelain"],
        )
        assert result.exit_code == 0


@patch(_PCLI)
@patch(_CTX)
def test_sync_native_workspace_not_found(MockContext, MockPresetClient):
    """Test push when target workspace ID not in workspace list."""
    MockContext.return_value = _mock_ctx(target_workspace_id=999)
    MockPresetClient.from_context.return_value = _mock_preset_client(
        workspaces=[{"id": 10, "hostname": "ws.preset.io"}]
    )

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(
            test_app,
            ["assets", "--force", "--porcelain"],
        )
        assert result.exit_code == 1


@patch(_PCLI)
@patch(_CTX)
def test_sync_native_no_hostname(MockContext, MockPresetClient):
    """Test push when workspace has no hostname."""
    MockContext.return_value = _mock_ctx(target_workspace_id=10)
    MockPresetClient.from_context.return_value = _mock_preset_client(
        workspaces=[{"id": 10, "hostname": None}]
    )

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(
            test_app,
            ["assets", "--force", "--porcelain"],
        )
        assert result.exit_code == 1


@patch(_NATIVE)
@patch(_PAUTH)
@patch(_PCLI)
@patch(_CTX)
def test_sync_native_confirmation_cancelled(MockContext, MockPresetClient, MockAuth, mock_native):
    """Test push cancelled at confirmation prompt."""
    MockContext.return_value = _mock_ctx(target_workspace_id=10)
    MockPresetClient.from_context.return_value = _mock_preset_client(
        workspaces=[{"id": 10, "hostname": "ws.preset.io"}]
    )

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(test_app, ["assets"], input="n\n")
        assert result.exit_code == 0


@patch(_NATIVE)
@patch(_PAUTH)
@patch(_PCLI)
@patch(_CTX)
def test_sync_native_confirmation_accepted(MockContext, MockPresetClient, MockAuth, mock_native):
    """Test push accepted at confirmation prompt."""
    MockContext.return_value = _mock_ctx(target_workspace_id=10)
    MockPresetClient.from_context.return_value = _mock_preset_client(
        workspaces=[{"id": 10, "hostname": "ws.preset.io"}]
    )
    MockAuth.from_sup_config.return_value = MagicMock()

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(test_app, ["assets"], input="y\n")
        assert result.exit_code == 0


@patch(_NATIVE)
@patch(_PAUTH)
@patch(_PCLI)
@patch(_CTX)
def test_sync_native_confirmation_with_overwrite(
    MockContext, MockPresetClient, MockAuth, mock_native
):
    """Test confirmation prompt displays overwrite warning."""
    MockContext.return_value = _mock_ctx(target_workspace_id=10)
    MockPresetClient.from_context.return_value = _mock_preset_client(
        workspaces=[{"id": 10, "hostname": "ws.preset.io"}]
    )

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(test_app, ["assets", "--overwrite"], input="n\n")
        assert result.exit_code == 0


@patch(_NATIVE)
@patch(_PAUTH)
@patch(_PCLI)
@patch(_CTX)
def test_sync_native_confirmation_with_asset_type(
    MockContext, MockPresetClient, MockAuth, mock_native
):
    """Test confirmation prompt displays asset type."""
    MockContext.return_value = _mock_ctx(target_workspace_id=10)
    MockPresetClient.from_context.return_value = _mock_preset_client(
        workspaces=[{"id": 10, "hostname": "ws.preset.io"}]
    )

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(test_app, ["assets", "--asset-type", "dashboard"], input="n\n")
        assert result.exit_code == 0


@patch(_NATIVE)
@patch(_PAUTH)
@patch(_PCLI)
@patch(_CTX)
def test_sync_native_success_not_porcelain(MockContext, MockPresetClient, MockAuth, mock_native):
    """Test successful import with human-readable output."""
    MockContext.return_value = _mock_ctx(target_workspace_id=10)
    MockPresetClient.from_context.return_value = _mock_preset_client(
        workspaces=[{"id": 10, "hostname": "ws.preset.io"}]
    )
    MockAuth.from_sup_config.return_value = MagicMock()

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(test_app, ["assets", "--force"])
        assert result.exit_code == 0


@patch(_CTX)
def test_sync_native_exception_porcelain(MockContext):
    """Test exception handling in porcelain mode."""
    MockContext.side_effect = RuntimeError("boom")

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(
            test_app,
            ["assets", "--force", "--porcelain"],
        )
        assert result.exit_code == 1


@patch(_CTX)
def test_sync_native_exception_not_porcelain(MockContext):
    """Test exception handling with human-readable output."""
    MockContext.side_effect = RuntimeError("boom")

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(test_app, ["assets", "--force"])
        assert result.exit_code == 1


@patch(_NATIVE)
@patch(_PAUTH)
@patch(_PCLI)
@patch(_CTX)
def test_sync_native_with_db_password(MockContext, MockPresetClient, MockAuth, mock_native):
    """Test push with --db-password option."""
    MockContext.return_value = _mock_ctx(target_workspace_id=10)
    MockPresetClient.from_context.return_value = _mock_preset_client(
        workspaces=[{"id": 10, "hostname": "ws.preset.io"}]
    )
    MockAuth.from_sup_config.return_value = MagicMock()

    with runner.isolated_filesystem():
        os.mkdir("assets")
        result = runner.invoke(
            test_app,
            ["assets", "--db-password", "uuid1=pass1", "--force", "--porcelain"],
        )
        assert result.exit_code == 0
