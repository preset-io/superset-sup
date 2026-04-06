"""Tests for push_helper.push_assets and dashboard/dataset push commands."""

from contextlib import ExitStack
from unittest.mock import MagicMock, patch

import click
import pytest
from typer.testing import CliRunner

from sup.commands.dashboard import app as dashboard_app
from sup.commands.dataset import app as dataset_app

runner = CliRunner()

PATCH_PUSH = "sup.commands.push_helper.push_assets"
PATCH_CTX = "sup.config.settings.SupContext"
PATCH_CLIENT = "sup.clients.preset.SupPresetClient"
PATCH_AUTH = "sup.auth.preset.SupPresetAuth"
PATCH_NATIVE = "preset_cli.cli.superset.sync.native.command.native"


def _make_ctx(assets_folder="./assets", workspace_id=100, target_workspace_id=200):
    ctx = MagicMock()
    ctx.get_assets_folder.return_value = assets_folder
    ctx.get_workspace_id.return_value = workspace_id
    ctx.get_target_workspace_id.return_value = target_workspace_id
    return ctx


def _call_push(**overrides):
    from sup.commands.push_helper import push_assets

    defaults = dict(
        asset_type_enum="DASHBOARD",
        asset_label="dashboards",
        assets_folder=None,
        workspace_id=None,
        overwrite=False,
        template_options=None,
        load_env=False,
        disable_jinja_templating=False,
        continue_on_error=False,
        force=True,
        porcelain=True,
    )
    defaults.update(overrides)
    push_assets(**defaults)


def _setup_success_mocks(stack, mock_ctx, hostname="ws200.preset.io", ws_id=200):
    stack.enter_context(patch(PATCH_CTX, return_value=mock_ctx))
    mock_client_cls = stack.enter_context(patch(PATCH_CLIENT))
    mock_auth_cls = stack.enter_context(patch(PATCH_AUTH))
    mock_native = stack.enter_context(patch(PATCH_NATIVE))
    mock_client = MagicMock()
    mock_client.get_all_workspaces.return_value = [{"id": ws_id, "hostname": hostname}]
    mock_client_cls.from_context.return_value = mock_client
    mock_auth_cls.from_sup_config.return_value = MagicMock()
    return mock_native


class TestPushAssetsFolder:
    def test_assets_folder_does_not_exist(self, tmp_path):
        mock_ctx = _make_ctx(assets_folder=str(tmp_path / "nonexistent"))
        with patch(PATCH_CTX, return_value=mock_ctx):
            with pytest.raises(click.exceptions.Exit):
                _call_push(porcelain=True)

    def test_assets_path_is_file_not_dir(self, tmp_path):
        fpath = tmp_path / "afile.txt"
        fpath.write_text("x")
        mock_ctx = _make_ctx(assets_folder=str(fpath))
        with patch(PATCH_CTX, return_value=mock_ctx):
            with pytest.raises(click.exceptions.Exit):
                _call_push(porcelain=True)

    def test_assets_folder_not_exist_non_porcelain(self, tmp_path):
        mock_ctx = _make_ctx(assets_folder=str(tmp_path / "missing"))
        with patch(PATCH_CTX, return_value=mock_ctx):
            with pytest.raises(click.exceptions.Exit):
                _call_push(porcelain=False)

    def test_assets_path_is_file_non_porcelain(self, tmp_path):
        fpath = tmp_path / "afile.txt"
        fpath.write_text("x")
        mock_ctx = _make_ctx(assets_folder=str(fpath))
        with patch(PATCH_CTX, return_value=mock_ctx):
            with pytest.raises(click.exceptions.Exit):
                _call_push(porcelain=False)


class TestPushAssetsWorkspaceConfig:
    def test_no_source_workspace(self, tmp_path):
        mock_ctx = _make_ctx(workspace_id=None)
        mock_ctx.get_assets_folder.return_value = str(tmp_path)
        with patch(PATCH_CTX, return_value=mock_ctx):
            with pytest.raises(click.exceptions.Exit):
                _call_push()

    def test_no_target_workspace(self, tmp_path):
        mock_ctx = _make_ctx(target_workspace_id=None)
        mock_ctx.get_assets_folder.return_value = str(tmp_path)
        with patch(PATCH_CTX, return_value=mock_ctx):
            with pytest.raises(click.exceptions.Exit):
                _call_push()


class TestPushAssetsSafetyConfirmation:
    def test_cross_workspace_confirm_yes(self, tmp_path):
        mock_ctx = _make_ctx(workspace_id=100, target_workspace_id=200)
        mock_ctx.get_assets_folder.return_value = str(tmp_path)
        with ExitStack() as stack:
            _setup_success_mocks(stack, mock_ctx)
            stack.enter_context(patch("typer.confirm", return_value=True))
            _call_push(force=False, porcelain=False)

    def test_same_workspace_confirm_yes(self, tmp_path):
        mock_ctx = _make_ctx(workspace_id=100, target_workspace_id=100)
        mock_ctx.get_assets_folder.return_value = str(tmp_path)
        with ExitStack() as stack:
            _setup_success_mocks(stack, mock_ctx, ws_id=100, hostname="ws100.preset.io")
            stack.enter_context(patch("typer.confirm", return_value=True))
            _call_push(force=False, porcelain=False)

    def test_confirm_cancelled(self, tmp_path):
        mock_ctx = _make_ctx(workspace_id=100, target_workspace_id=200)
        mock_ctx.get_assets_folder.return_value = str(tmp_path)
        with ExitStack() as stack:
            stack.enter_context(patch(PATCH_CTX, return_value=mock_ctx))
            stack.enter_context(patch("typer.confirm", return_value=False))
            with pytest.raises(click.exceptions.Exit):
                _call_push(force=False, porcelain=False)


class TestPushAssetsWorkspaceResolution:
    def test_target_workspace_not_found(self, tmp_path):
        mock_ctx = _make_ctx()
        mock_ctx.get_assets_folder.return_value = str(tmp_path)
        mock_client = MagicMock()
        mock_client.get_all_workspaces.return_value = [{"id": 999, "hostname": "o.io"}]
        with ExitStack() as stack:
            stack.enter_context(patch(PATCH_CTX, return_value=mock_ctx))
            mc = stack.enter_context(patch(PATCH_CLIENT))
            mc.from_context.return_value = mock_client
            with pytest.raises(click.exceptions.Exit):
                _call_push()

    def test_target_workspace_no_hostname(self, tmp_path):
        mock_ctx = _make_ctx()
        mock_ctx.get_assets_folder.return_value = str(tmp_path)
        mock_client = MagicMock()
        mock_client.get_all_workspaces.return_value = [{"id": 200, "hostname": None}]
        with ExitStack() as stack:
            stack.enter_context(patch(PATCH_CTX, return_value=mock_ctx))
            mc = stack.enter_context(patch(PATCH_CLIENT))
            mc.from_context.return_value = mock_client
            with pytest.raises(click.exceptions.Exit):
                _call_push()


class TestPushAssetsSuccess:
    def test_successful_push_porcelain(self, tmp_path):
        mock_ctx = _make_ctx()
        mock_ctx.get_assets_folder.return_value = str(tmp_path)
        with ExitStack() as stack:
            mn = _setup_success_mocks(stack, mock_ctx)
            _call_push(porcelain=True)
            mn.assert_called_once()

    def test_successful_push_non_porcelain(self, tmp_path):
        mock_ctx = _make_ctx()
        mock_ctx.get_assets_folder.return_value = str(tmp_path)
        with ExitStack() as stack:
            mn = _setup_success_mocks(stack, mock_ctx)
            _call_push(porcelain=False)
            mn.assert_called_once()

    def test_push_with_template_options(self, tmp_path):
        mock_ctx = _make_ctx()
        mock_ctx.get_assets_folder.return_value = str(tmp_path)
        with ExitStack() as stack:
            mn = _setup_success_mocks(stack, mock_ctx)
            _call_push(
                overwrite=True,
                template_options=["env=prod"],
                load_env=True,
                disable_jinja_templating=True,
                continue_on_error=True,
            )
            mn.assert_called_once()


class TestDashboardPushCommand:
    def test_dashboard_push_calls_push_assets(self):
        with patch(PATCH_PUSH) as mp:
            runner.invoke(dashboard_app, ["push", "--force", "--porcelain"])
            mp.assert_called_once()
            assert mp.call_args.kwargs["asset_label"] == "dashboards"
            assert mp.call_args.kwargs["force"] is True
            assert mp.call_args.kwargs["porcelain"] is True

    def test_dashboard_push_with_overwrite(self):
        with patch(PATCH_PUSH) as mp:
            runner.invoke(dashboard_app, ["push", "--overwrite", "--force", "--porcelain"])
            mp.assert_called_once()
            assert mp.call_args.kwargs["overwrite"] is True

    def test_dashboard_push_with_assets_folder(self):
        with patch(PATCH_PUSH) as mp:
            runner.invoke(dashboard_app, ["push", "./my_assets", "--force", "--porcelain"])
            mp.assert_called_once()
            assert mp.call_args.kwargs["assets_folder"] == "./my_assets"


class TestDatasetPushCommand:
    def test_dataset_push_calls_push_assets(self):
        with patch(PATCH_PUSH) as mp:
            runner.invoke(dataset_app, ["push", "--force", "--porcelain"])
            mp.assert_called_once()
            assert mp.call_args.kwargs["asset_label"] == "datasets"
            assert mp.call_args.kwargs["force"] is True

    def test_dataset_push_with_continue_on_error(self):
        with patch(PATCH_PUSH) as mp:
            runner.invoke(dataset_app, ["push", "--continue-on-error", "--force", "--porcelain"])
            mp.assert_called_once()
            assert mp.call_args.kwargs["continue_on_error"] is True
