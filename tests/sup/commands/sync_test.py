"""Tests for sup.commands.sync module."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from sup.commands.sync import (
    app,
    display_sync_summary,
    execute_pull,
    execute_push,
    format_sync_help,
)

runner = CliRunner()


# ---------------------------------------------------------------------------
# Helpers to build mock SyncConfig and related objects
# ---------------------------------------------------------------------------


def _make_asset_selection(selection="all", ids=None, include_dependencies=True):
    m = MagicMock()
    m.selection = selection
    m.ids = ids
    m.include_dependencies = include_dependencies
    return m


def _make_target(workspace_id=456, name=None, overwrite=False, jinja_context=None):
    t = MagicMock()
    t.workspace_id = workspace_id
    t.name = name
    t.get_effective_overwrite.return_value = overwrite
    t.get_effective_jinja_context.return_value = jinja_context or {}
    return t


def _make_sync_config(
    source_workspace_id=123,
    assets=None,
    targets=None,
    target_defaults=None,
):
    cfg = MagicMock()
    cfg.source.workspace_id = source_workspace_id
    if assets is None:
        assets = MagicMock()
        assets.charts = _make_asset_selection()
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
    cfg.source.assets = assets
    cfg.targets = targets or [_make_target()]
    cfg.target_defaults = target_defaults or MagicMock()
    cfg.get_target_by_name.return_value = None
    cfg.get_target_by_workspace_id.return_value = None
    cfg.assets_folder.return_value = Path("/tmp/sync_test/assets")
    cfg.sync_config_path.return_value = Path("/tmp/sync_test/sync_config.yml")
    return cfg


# ---------------------------------------------------------------------------
# format_sync_help
# ---------------------------------------------------------------------------


class TestFormatSyncHelp:
    def test_returns_string(self):
        result = format_sync_help()
        assert isinstance(result, str)
        assert "Multi-target" in result
        assert "Quick Start" in result


# ---------------------------------------------------------------------------
# run_sync command
# ---------------------------------------------------------------------------


class TestRunSync:
    @patch("sup.commands.sync.validate_sync_folder")
    def test_pull_only_and_push_only_error(self, mock_validate):
        result = runner.invoke(app, ["run", "/tmp/s", "--pull-only", "--push-only"])
        assert result.exit_code == 1

    @patch("sup.commands.sync.validate_sync_folder")
    def test_pull_only_and_push_only_porcelain(self, mock_validate):
        result = runner.invoke(app, ["run", "/tmp/s", "--pull-only", "--push-only", "--porcelain"])
        assert result.exit_code == 1

    @patch("sup.commands.sync.validate_sync_folder", return_value=False)
    def test_invalid_sync_folder(self, mock_validate):
        result = runner.invoke(app, ["run", "/tmp/s"])
        assert result.exit_code == 1
        assert "Invalid sync folder" in result.output

    @patch("sup.commands.sync.validate_sync_folder", return_value=False)
    def test_invalid_sync_folder_porcelain(self, mock_validate):
        result = runner.invoke(app, ["run", "/tmp/s", "--porcelain"])
        assert result.exit_code == 1
        assert "Invalid sync folder" not in result.output

    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_config_load_failure(self, mock_validate, mock_cfg_cls):
        mock_cfg_cls.from_yaml.side_effect = Exception("bad yaml")
        result = runner.invoke(app, ["run", "/tmp/s"])
        assert result.exit_code == 1
        assert "Failed to load sync config" in result.output

    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_config_load_failure_porcelain(self, mock_validate, mock_cfg_cls):
        mock_cfg_cls.from_yaml.side_effect = Exception("bad yaml")
        result = runner.invoke(app, ["run", "/tmp/s", "--porcelain"])
        assert result.exit_code == 1
        assert "Failed to load sync config" not in result.output

    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_target_found_by_name(self, mock_validate, mock_cfg_cls):
        cfg = _make_sync_config()
        target = _make_target(workspace_id=456, name="prod")
        cfg.get_target_by_name.return_value = target
        mock_cfg_cls.from_yaml.return_value = cfg

        with patch("sup.commands.sync.execute_pull"), patch(
            "sup.commands.sync.execute_push"
        ), patch("sup.commands.sync.display_sync_summary"):
            result = runner.invoke(app, ["run", "/tmp/s", "--target", "prod", "--force"])
        assert result.exit_code == 0

    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_target_found_by_workspace_id(self, mock_validate, mock_cfg_cls):
        cfg = _make_sync_config()
        target = _make_target(workspace_id=456)
        cfg.get_target_by_name.return_value = None
        cfg.get_target_by_workspace_id.return_value = target
        mock_cfg_cls.from_yaml.return_value = cfg

        with patch("sup.commands.sync.execute_pull"), patch(
            "sup.commands.sync.execute_push"
        ), patch("sup.commands.sync.display_sync_summary"):
            result = runner.invoke(app, ["run", "/tmp/s", "--target", "456", "--force"])
        assert result.exit_code == 0

    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_target_not_found(self, mock_validate, mock_cfg_cls):
        cfg = _make_sync_config()
        cfg.get_target_by_name.return_value = None
        cfg.get_target_by_workspace_id.return_value = None
        mock_cfg_cls.from_yaml.return_value = cfg

        result = runner.invoke(app, ["run", "/tmp/s", "--target", "nonexistent"])
        assert result.exit_code == 1
        assert "not found" in result.output

    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_target_not_found_porcelain(self, mock_validate, mock_cfg_cls):
        cfg = _make_sync_config()
        cfg.get_target_by_name.return_value = None
        cfg.get_target_by_workspace_id.return_value = None
        mock_cfg_cls.from_yaml.return_value = cfg

        result = runner.invoke(app, ["run", "/tmp/s", "--target", "nonexistent", "--porcelain"])
        assert result.exit_code == 1

    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_target_not_found_non_numeric(self, mock_validate, mock_cfg_cls):
        """Target that is not a valid int and not found by name."""
        cfg = _make_sync_config()
        cfg.get_target_by_name.return_value = None
        mock_cfg_cls.from_yaml.return_value = cfg

        result = runner.invoke(app, ["run", "/tmp/s", "--target", "abc"])
        assert result.exit_code == 1

    @patch("sup.commands.sync.execute_push")
    @patch("sup.commands.sync.execute_pull")
    @patch("sup.commands.sync.display_sync_summary")
    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_confirm_decline(self, mock_validate, mock_cfg_cls, mock_display, mock_pull, mock_push):
        cfg = _make_sync_config()
        mock_cfg_cls.from_yaml.return_value = cfg

        # 'n' to decline confirm
        result = runner.invoke(app, ["run", "/tmp/s"], input="n\n")
        assert result.exit_code == 0
        mock_pull.assert_not_called()
        mock_push.assert_not_called()

    @patch("sup.commands.sync.execute_push")
    @patch("sup.commands.sync.execute_pull")
    @patch("sup.commands.sync.display_sync_summary")
    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_confirm_accept(self, mock_validate, mock_cfg_cls, mock_display, mock_pull, mock_push):
        cfg = _make_sync_config()
        mock_cfg_cls.from_yaml.return_value = cfg

        result = runner.invoke(app, ["run", "/tmp/s"], input="y\n")
        assert result.exit_code == 0
        mock_pull.assert_called_once()
        mock_push.assert_called_once()

    @patch("sup.commands.sync.execute_push")
    @patch("sup.commands.sync.execute_pull")
    @patch("sup.commands.sync.display_sync_summary")
    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_pull_only(self, mock_validate, mock_cfg_cls, mock_display, mock_pull, mock_push):
        cfg = _make_sync_config()
        mock_cfg_cls.from_yaml.return_value = cfg

        result = runner.invoke(app, ["run", "/tmp/s", "--pull-only", "--force"])
        assert result.exit_code == 0
        mock_pull.assert_called_once()
        mock_push.assert_not_called()

    @patch("sup.commands.sync.execute_push")
    @patch("sup.commands.sync.execute_pull")
    @patch("sup.commands.sync.display_sync_summary")
    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_push_only(self, mock_validate, mock_cfg_cls, mock_display, mock_pull, mock_push):
        cfg = _make_sync_config()
        mock_cfg_cls.from_yaml.return_value = cfg

        result = runner.invoke(app, ["run", "/tmp/s", "--push-only", "--force"])
        assert result.exit_code == 0
        mock_pull.assert_not_called()
        mock_push.assert_called_once()

    @patch("sup.commands.sync.execute_push")
    @patch("sup.commands.sync.execute_pull")
    @patch("sup.commands.sync.display_sync_summary")
    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_dry_run_skips_confirm(
        self, mock_validate, mock_cfg_cls, mock_display, mock_pull, mock_push
    ):
        cfg = _make_sync_config()
        mock_cfg_cls.from_yaml.return_value = cfg

        result = runner.invoke(app, ["run", "/tmp/s", "--dry-run"])
        assert result.exit_code == 0
        mock_pull.assert_called_once()
        mock_push.assert_called_once()

    @patch("sup.commands.sync.execute_push")
    @patch("sup.commands.sync.execute_pull")
    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_porcelain_skips_display(self, mock_validate, mock_cfg_cls, mock_pull, mock_push):
        cfg = _make_sync_config()
        mock_cfg_cls.from_yaml.return_value = cfg

        result = runner.invoke(app, ["run", "/tmp/s", "--porcelain", "--force"])
        assert result.exit_code == 0

    @patch("sup.commands.sync.execute_pull", side_effect=Exception("pull failed"))
    @patch("sup.commands.sync.display_sync_summary")
    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_sync_exception(self, mock_validate, mock_cfg_cls, mock_display, mock_pull):
        cfg = _make_sync_config()
        mock_cfg_cls.from_yaml.return_value = cfg

        result = runner.invoke(app, ["run", "/tmp/s", "--force"])
        assert result.exit_code == 1
        assert "Sync operation failed" in result.output

    @patch("sup.commands.sync.execute_pull", side_effect=Exception("pull failed"))
    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_sync_exception_porcelain(self, mock_validate, mock_cfg_cls, mock_pull):
        cfg = _make_sync_config()
        mock_cfg_cls.from_yaml.return_value = cfg

        result = runner.invoke(app, ["run", "/tmp/s", "--force", "--porcelain"])
        assert result.exit_code == 1
        assert "Sync operation failed" not in result.output

    @patch("sup.commands.sync.execute_push")
    @patch("sup.commands.sync.execute_pull")
    @patch("sup.commands.sync.display_sync_summary")
    @patch("sup.commands.sync.SyncConfig")
    @patch("sup.commands.sync.validate_sync_folder", return_value=True)
    def test_success_message(self, mock_validate, mock_cfg_cls, mock_display, mock_pull, mock_push):
        cfg = _make_sync_config()
        mock_cfg_cls.from_yaml.return_value = cfg

        result = runner.invoke(app, ["run", "/tmp/s", "--force"])
        assert result.exit_code == 0
        assert "completed successfully" in result.output


# ---------------------------------------------------------------------------
# create_sync command
# ---------------------------------------------------------------------------


class TestCreateSync:
    @patch("sup.commands.sync.SyncConfig")
    def test_folder_exists_no_force(self, mock_cfg_cls, tmp_path):
        folder = tmp_path / "existing"
        folder.mkdir()
        result = runner.invoke(app, ["create", str(folder), "--source", "1", "--targets", "2"])
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_invalid_target_ids(self, tmp_path):
        folder = tmp_path / "newsync"
        result = runner.invoke(app, ["create", str(folder), "--source", "1", "--targets", "abc"])
        assert result.exit_code == 1
        assert "Invalid target workspace IDs" in result.output

    @patch("sup.commands.sync.SyncConfig")
    def test_success(self, mock_cfg_cls, tmp_path):
        folder = tmp_path / "newsync"
        cfg = _make_sync_config()
        cfg.assets_folder.return_value = folder / "assets"
        cfg.sync_config_path.return_value = folder / "sync_config.yml"
        mock_cfg_cls.create_example.return_value = cfg

        result = runner.invoke(
            app, ["create", str(folder), "--source", "123", "--targets", "456,789"]
        )
        assert result.exit_code == 0
        assert "Created sync folder" in result.output
        assert (folder / "assets" / "charts").exists()
        assert (folder / "assets" / "dashboards").exists()
        assert (folder / "assets" / "datasets").exists()
        assert (folder / "assets" / "databases").exists()
        cfg.to_yaml.assert_called_once()

    @patch("sup.commands.sync.SyncConfig")
    def test_force_overwrite(self, mock_cfg_cls, tmp_path):
        folder = tmp_path / "existing"
        folder.mkdir()
        cfg = _make_sync_config()
        cfg.assets_folder.return_value = folder / "assets"
        cfg.sync_config_path.return_value = folder / "sync_config.yml"
        mock_cfg_cls.create_example.return_value = cfg

        result = runner.invoke(
            app, ["create", str(folder), "--source", "1", "--targets", "2", "--force"]
        )
        assert result.exit_code == 0

    @patch("sup.commands.sync.SyncConfig")
    def test_create_exception(self, mock_cfg_cls, tmp_path):
        folder = tmp_path / "newsync"
        mock_cfg_cls.create_example.side_effect = Exception("boom")

        result = runner.invoke(app, ["create", str(folder), "--source", "1", "--targets", "2"])
        assert result.exit_code == 1
        assert "Failed to create sync folder" in result.output


# ---------------------------------------------------------------------------
# validate_sync command
# ---------------------------------------------------------------------------


class TestValidateSync:
    def test_folder_does_not_exist(self, tmp_path):
        result = runner.invoke(app, ["validate", str(tmp_path / "nope")])
        assert result.exit_code == 1
        assert "does not exist" in result.output

    def test_config_file_missing(self, tmp_path):
        folder = tmp_path / "empty"
        folder.mkdir()
        result = runner.invoke(app, ["validate", str(folder)])
        assert result.exit_code == 1
        assert "sync_config.yml not found" in result.output

    @patch("sup.commands.sync.display_sync_summary")
    @patch("sup.commands.sync.SyncConfig")
    def test_valid_config(self, mock_cfg_cls, mock_display, tmp_path):
        folder = tmp_path / "good"
        folder.mkdir()
        (folder / "sync_config.yml").write_text("dummy")
        cfg = _make_sync_config()
        mock_cfg_cls.from_yaml.return_value = cfg

        result = runner.invoke(app, ["validate", str(folder)])
        assert result.exit_code == 0
        assert "valid" in result.output
        mock_display.assert_called_once()

    @patch("sup.commands.sync.SyncConfig")
    def test_invalid_config(self, mock_cfg_cls, tmp_path):
        folder = tmp_path / "bad"
        folder.mkdir()
        (folder / "sync_config.yml").write_text("dummy")
        mock_cfg_cls.from_yaml.side_effect = Exception("parse error")

        result = runner.invoke(app, ["validate", str(folder)])
        assert result.exit_code == 1
        assert "Invalid sync configuration" in result.output


# ---------------------------------------------------------------------------
# display_sync_summary
# ---------------------------------------------------------------------------


class TestDisplaySyncSummary:
    @patch("sup.commands.sync.console")
    def test_pull_only(self, mock_console):
        cfg = _make_sync_config()
        targets = [_make_target(name="prod")]
        display_sync_summary(
            cfg, targets, pull_only=True, push_only=False, dry_run=False, sync_path=Path("/tmp/s")
        )
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("Pull Only" in c for c in calls)
        assert any("prod" in c for c in calls)

    @patch("sup.commands.sync.console")
    def test_push_only(self, mock_console):
        cfg = _make_sync_config()
        targets = [_make_target()]
        display_sync_summary(
            cfg, targets, pull_only=False, push_only=True, dry_run=False, sync_path=Path("/tmp/s")
        )
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("Push Only" in c for c in calls)

    @patch("sup.commands.sync.console")
    def test_full_sync(self, mock_console):
        cfg = _make_sync_config()
        targets = [_make_target()]
        display_sync_summary(
            cfg, targets, pull_only=False, push_only=False, dry_run=False, sync_path=Path("/tmp/s")
        )
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("Full Sync" in c for c in calls)

    @patch("sup.commands.sync.console")
    def test_dry_run_appends(self, mock_console):
        cfg = _make_sync_config()
        targets = [_make_target()]
        display_sync_summary(
            cfg, targets, pull_only=True, push_only=False, dry_run=True, sync_path=Path("/tmp/s")
        )
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("Dry Run" in c for c in calls)

    @patch("sup.commands.sync.console")
    def test_ids_selection(self, mock_console):
        assets = MagicMock()
        assets.charts = _make_asset_selection(selection="ids", ids=[1, 2, 3])
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)
        targets = [_make_target(name="staging")]
        display_sync_summary(cfg, targets, False, False, False, Path("/tmp/s"))
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("3 items" in c for c in calls)

    @patch("sup.commands.sync.console")
    def test_target_without_name(self, mock_console):
        cfg = _make_sync_config()
        targets = [_make_target(name=None)]
        display_sync_summary(cfg, targets, False, False, False, Path("/tmp/s"))
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("456" in c for c in calls)

    @patch("sup.commands.sync.console")
    def test_no_assets(self, mock_console):
        """All asset configs are None."""
        assets = MagicMock()
        assets.charts = None
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)
        display_sync_summary(cfg, [], False, False, False, Path("/tmp/s"))
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("123" in c for c in calls)  # source workspace id still printed


# ---------------------------------------------------------------------------
# execute_pull
# ---------------------------------------------------------------------------


class TestExecutePull:
    @patch("sup.commands.sync.console")
    def test_dry_run_ids(self, mock_console):
        assets = MagicMock()
        assets.charts = _make_asset_selection(selection="ids", ids=[1, 2])
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)

        execute_pull(cfg, Path("/tmp/s"), dry_run=True, porcelain=False)
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("DRY RUN" in c for c in calls)
        assert any("2 items" in c for c in calls)

    @patch("sup.commands.sync.console")
    def test_dry_run_all(self, mock_console):
        assets = MagicMock()
        assets.charts = _make_asset_selection(selection="all")
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)

        execute_pull(cfg, Path("/tmp/s"), dry_run=True, porcelain=False)
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("DRY RUN" in c for c in calls)
        assert any("charts" in c for c in calls)

    @patch("sup.commands.sync.console")
    def test_dry_run_porcelain(self, mock_console):
        assets = MagicMock()
        assets.charts = _make_asset_selection(selection="all")
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)

        execute_pull(cfg, Path("/tmp/s"), dry_run=True, porcelain=True)
        # porcelain dry_run should not print anything
        mock_console.print.assert_not_called()

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("preset_cli.cli.superset.export.export_resource")
    def test_real_pull_all(self, mock_export, mock_client_cls, mock_ctx_cls, tmp_path):
        mock_client = MagicMock()
        mock_client.client.get_resources.return_value = [{"id": 10}, {"id": 20}]
        mock_client_cls.from_context.return_value = mock_client

        assets = MagicMock()
        assets.charts = _make_asset_selection(selection="all")
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        execute_pull(cfg, tmp_path, dry_run=False, porcelain=False)
        mock_export.assert_called_once()
        call_kwargs = mock_export.call_args
        assert call_kwargs.kwargs["requested_ids"] == {10, 20}

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("preset_cli.cli.superset.export.export_resource")
    def test_real_pull_ids(self, mock_export, mock_client_cls, mock_ctx_cls, tmp_path):
        mock_client = MagicMock()
        mock_client_cls.from_context.return_value = mock_client

        assets = MagicMock()
        assets.charts = _make_asset_selection(selection="ids", ids=[5, 6])
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        execute_pull(cfg, tmp_path, dry_run=False, porcelain=False)
        mock_export.assert_called_once()
        call_kwargs = mock_export.call_args
        assert call_kwargs.kwargs["requested_ids"] == {5, 6}

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("preset_cli.cli.superset.export.export_resource")
    def test_real_pull_other_selection_skipped(
        self, mock_export, mock_client_cls, mock_ctx_cls, tmp_path
    ):
        mock_client = MagicMock()
        mock_client_cls.from_context.return_value = mock_client

        assets = MagicMock()
        assets.charts = _make_asset_selection(selection="mine")
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        execute_pull(cfg, tmp_path, dry_run=False, porcelain=False)
        mock_export.assert_not_called()

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("preset_cli.cli.superset.export.export_resource")
    def test_real_pull_no_requested_ids(self, mock_export, mock_client_cls, mock_ctx_cls, tmp_path):
        mock_client = MagicMock()
        mock_client.client.get_resources.return_value = []
        mock_client_cls.from_context.return_value = mock_client

        assets = MagicMock()
        assets.charts = _make_asset_selection(selection="all")
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        execute_pull(cfg, tmp_path, dry_run=False, porcelain=False)
        mock_export.assert_not_called()

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("preset_cli.cli.superset.export.export_resource")
    def test_real_pull_no_asset_config(self, mock_export, mock_client_cls, mock_ctx_cls, tmp_path):
        """Asset config is None -> continue."""
        mock_client = MagicMock()
        mock_client_cls.from_context.return_value = mock_client

        assets = MagicMock()
        assets.charts = None
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        execute_pull(cfg, tmp_path, dry_run=False, porcelain=False)
        mock_export.assert_not_called()

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("preset_cli.cli.superset.export.export_resource")
    def test_real_pull_porcelain(self, mock_export, mock_client_cls, mock_ctx_cls, tmp_path):
        mock_client = MagicMock()
        mock_client.client.get_resources.return_value = [{"id": 1}]
        mock_client_cls.from_context.return_value = mock_client

        assets = MagicMock()
        assets.charts = _make_asset_selection(selection="all")
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        execute_pull(cfg, tmp_path, dry_run=False, porcelain=True)
        mock_export.assert_called_once()

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    def test_real_pull_exception_reraise(self, mock_client_cls, mock_ctx_cls, tmp_path):
        mock_client_cls.from_context.side_effect = Exception("connection failed")

        assets = MagicMock()
        assets.charts = _make_asset_selection(selection="all")
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        with pytest.raises(Exception, match="connection failed"):
            execute_pull(cfg, tmp_path, dry_run=False, porcelain=False)

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    def test_real_pull_exception_porcelain(self, mock_client_cls, mock_ctx_cls, tmp_path):
        mock_client_cls.from_context.side_effect = Exception("fail")

        assets = MagicMock()
        assets.charts = _make_asset_selection(selection="all")
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        with pytest.raises(Exception, match="fail"):
            execute_pull(cfg, tmp_path, dry_run=False, porcelain=True)

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("preset_cli.cli.superset.export.export_resource")
    def test_real_pull_other_selection_porcelain(
        self, mock_export, mock_client_cls, mock_ctx_cls, tmp_path
    ):
        """Other selection with porcelain -> skip silently."""
        mock_client = MagicMock()
        mock_client_cls.from_context.return_value = mock_client

        assets = MagicMock()
        assets.charts = _make_asset_selection(selection="filter")
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        execute_pull(cfg, tmp_path, dry_run=False, porcelain=True)
        mock_export.assert_not_called()

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("preset_cli.cli.superset.export.export_resource")
    def test_real_pull_empty_ids_porcelain(
        self, mock_export, mock_client_cls, mock_ctx_cls, tmp_path
    ):
        """ids selection with empty list -> porcelain skip."""
        mock_client = MagicMock()
        mock_client_cls.from_context.return_value = mock_client

        assets = MagicMock()
        sel = MagicMock()
        sel.selection = "ids"
        sel.ids = []
        sel.include_dependencies = True
        assets.charts = sel
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        execute_pull(cfg, tmp_path, dry_run=False, porcelain=True)
        mock_export.assert_not_called()

    @patch("sup.commands.sync.console")
    def test_dry_run_none_asset_config(self, mock_console):
        """Asset config is None in dry_run path."""
        assets = MagicMock()
        assets.charts = None
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = None
        cfg = _make_sync_config(assets=assets)

        execute_pull(cfg, Path("/tmp/s"), dry_run=True, porcelain=False)
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("DRY RUN" in c for c in calls)


# ---------------------------------------------------------------------------
# execute_push
# ---------------------------------------------------------------------------


class TestExecutePush:
    @patch("sup.commands.sync.console")
    def test_dry_run(self, mock_console):
        cfg = _make_sync_config()
        target = _make_target(name="prod", jinja_context={"env": "prod"})

        execute_push(cfg, [target], Path("/tmp/s"), dry_run=True, porcelain=False)
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("DRY RUN" in c for c in calls)
        assert any("prod" in c for c in calls)

    @patch("sup.commands.sync.console")
    def test_dry_run_porcelain(self, mock_console):
        cfg = _make_sync_config()
        target = _make_target(jinja_context={"env": "staging"})

        execute_push(cfg, [target], Path("/tmp/s"), dry_run=True, porcelain=True)
        # porcelain dry_run should not print anything
        mock_console.print.assert_not_called()

    @patch("sup.commands.sync.console")
    def test_dry_run_no_name(self, mock_console):
        cfg = _make_sync_config()
        target = _make_target(name=None)

        execute_push(cfg, [target], Path("/tmp/s"), dry_run=True, porcelain=False)
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("DRY RUN" in c for c in calls)

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_assets_path_not_exist(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        cfg = _make_sync_config()
        nonexistent = tmp_path / "no_assets"
        cfg.assets_folder.return_value = nonexistent
        target = _make_target()

        with pytest.raises(Exception, match="Assets folder not found"):
            execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=False)

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_with_configs(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        # Create assets folder with a YAML file
        assets = tmp_path / "assets"
        charts_dir = assets / "charts"
        charts_dir.mkdir(parents=True)
        yaml_file = charts_dir / "chart_1.yaml"
        yaml_file.write_text("title: test")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        target = _make_target(name="prod")

        mock_is_yaml.return_value = True
        mock_render.return_value = {"title": "test"}
        mock_rt.ASSET.metadata_type = "assets"

        execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=False)
        mock_import.assert_called_once()

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_skip_metadata_yaml(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        (assets / "metadata.yaml").write_text("version: 1")
        (assets / "tags.yaml").write_text("tags: []")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        target = _make_target()

        mock_is_yaml.return_value = True
        mock_rt.ASSET.metadata_type = "assets"

        execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=False)
        mock_import.assert_not_called()

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_skip_hidden_dirs(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        assets = tmp_path / "assets"
        hidden = assets / ".hidden"
        hidden.mkdir(parents=True)
        (hidden / "secret.yaml").write_text("x: 1")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        target = _make_target()

        mock_is_yaml.return_value = False
        mock_rt.ASSET.metadata_type = "assets"

        execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=False)
        mock_import.assert_not_called()

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_non_yaml_skipped(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        (assets / "readme.txt").write_text("hello")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        target = _make_target()

        mock_is_yaml.return_value = False
        mock_rt.ASSET.metadata_type = "assets"

        execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=False)
        mock_import.assert_not_called()

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_no_configs_warning(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        assets = tmp_path / "assets"
        assets.mkdir(parents=True)

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        target = _make_target()

        mock_rt.ASSET.metadata_type = "assets"

        execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=False)
        mock_import.assert_not_called()

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_no_configs_porcelain(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        assets = tmp_path / "assets"
        assets.mkdir(parents=True)

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        target = _make_target()

        mock_rt.ASSET.metadata_type = "assets"

        execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=True)
        mock_import.assert_not_called()

    @patch("preset_cli.lib.dict_merge")
    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_with_overrides(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        mock_dict_merge,
        tmp_path,
    ):
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        assets = tmp_path / "assets"
        charts_dir = assets / "charts"
        charts_dir.mkdir(parents=True)
        yaml_file = charts_dir / "chart_1.yaml"
        yaml_file.write_text("title: test")
        override_file = charts_dir / "chart_1.overrides.yaml"
        override_file.write_text("title: override")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        target = _make_target()

        mock_is_yaml.return_value = True
        mock_render.side_effect = [{"title": "override"}, {"title": "test"}, {"title": "override"}]
        mock_rt.ASSET.metadata_type = "assets"

        execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=False)
        mock_dict_merge.assert_called_once()
        mock_import.assert_called_once()

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_import_failure_with_errors_attr(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        yaml_file = assets / "chart_1.yaml"
        yaml_file.write_text("title: test")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        target = _make_target()

        mock_is_yaml.return_value = True
        mock_render.return_value = {"title": "test"}
        mock_rt.ASSET.metadata_type = "assets"

        err = Exception("import failed")
        err.errors = ["err1", "err2"]
        mock_import.side_effect = err

        with pytest.raises(Exception, match="import failed"):
            execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=False)

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_import_failure_no_errors_attr(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        yaml_file = assets / "chart_1.yaml"
        yaml_file.write_text("title: test")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        target = _make_target()

        mock_is_yaml.return_value = True
        mock_render.return_value = {"title": "test"}
        mock_rt.ASSET.metadata_type = "assets"
        mock_import.side_effect = Exception("import failed")

        with pytest.raises(Exception, match="import failed"):
            execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=False)

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_porcelain_success(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        """Push with porcelain=True, configs present, no debug bundle."""
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        yaml_file = assets / "chart_1.yaml"
        yaml_file.write_text("title: test")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        target = _make_target()

        mock_is_yaml.return_value = True
        mock_render.return_value = {"title": "test"}
        mock_rt.ASSET.metadata_type = "assets"

        execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=True)
        mock_import.assert_called_once()

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_import_failure_porcelain(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        """Push failure with porcelain=True should reraise without console output."""
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        yaml_file = assets / "chart_1.yaml"
        yaml_file.write_text("title: test")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        target = _make_target()

        mock_is_yaml.return_value = True
        mock_render.return_value = {"title": "test"}
        mock_rt.ASSET.metadata_type = "assets"
        mock_import.side_effect = Exception("fail")

        with pytest.raises(Exception, match="fail"):
            execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=True)

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_multiple_targets(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        (assets / "chart.yaml").write_text("title: t")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        t1 = _make_target(workspace_id=100, name="a")
        t2 = _make_target(workspace_id=200, name=None)

        mock_is_yaml.return_value = True
        mock_render.return_value = {"title": "t"}
        mock_rt.ASSET.metadata_type = "assets"

        execute_push(cfg, [t1, t2], tmp_path, dry_run=False, porcelain=False)
        assert mock_import.call_count == 2

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_with_subdirectory_configs(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        """YAML files in subdirectories get included and asset_counts works."""
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        assets = tmp_path / "assets"
        charts = assets / "charts"
        charts.mkdir(parents=True)
        (charts / "c1.yaml").write_text("t: 1")
        (charts / "c2.yaml").write_text("t: 2")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        target = _make_target()

        mock_is_yaml.return_value = True
        mock_render.return_value = {"t": 1}
        mock_rt.ASSET.metadata_type = "assets"

        execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=False)
        mock_import.assert_called_once()

    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_exception_reraise(self, mock_ctx, mock_client_cls, tmp_path):
        """General exception during push is re-raised."""
        mock_client_cls.from_context.side_effect = Exception("auth fail")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = tmp_path / "assets"
        target = _make_target()

        with pytest.raises(Exception, match="auth fail"):
            execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=False)

    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_exception_porcelain_reraise(self, mock_ctx, mock_client_cls, tmp_path):
        mock_client_cls.from_context.side_effect = Exception("auth fail")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = tmp_path / "assets"
        target = _make_target()

        with pytest.raises(Exception, match="auth fail"):
            execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=True)

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_import_captures_stdout(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        """Verify stdout/stderr capture and restore during import."""
        import sys

        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        (assets / "chart.yaml").write_text("t: 1")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        target = _make_target()

        mock_is_yaml.return_value = True
        mock_render.return_value = {"t": 1}
        mock_rt.ASSET.metadata_type = "assets"

        original_stdout = sys.stdout
        original_stderr = sys.stderr

        def side_effect(*args, **kwargs):
            import sys

            sys.stdout.write("import output")

        mock_import.side_effect = side_effect

        execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=False)

        # Verify stdout/stderr are restored
        assert sys.stdout is original_stdout
        assert sys.stderr is original_stderr


# ---------------------------------------------------------------------------
# Theme sync pull path
# ---------------------------------------------------------------------------


class TestThemeSyncPull:
    """Tests for the theme-specific branch in execute_pull."""

    @staticmethod
    def _make_theme_zip(themes):
        """Build a minimal Superset theme export ZIP."""
        import io
        from zipfile import ZipFile

        import yaml

        buf = io.BytesIO()
        with ZipFile(buf, "w") as zf:
            for t in themes:
                name = t["theme_name"].replace(" ", "_")
                zf.writestr(
                    f"bundle/themes/{name}.yaml",
                    yaml.safe_dump({"theme_name": t["theme_name"]}),
                )
            zf.writestr("bundle/metadata.yaml", yaml.safe_dump({"version": "1.0.0"}))
        buf.seek(0)
        return buf

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("preset_cli.cli.superset.export.export_resource")
    def test_theme_pull_all(self, mock_export, mock_client_cls, mock_ctx_cls, tmp_path):
        """Themes with selection=all are pulled via export_zip."""
        mock_client = MagicMock()
        mock_client.client.get_resources.return_value = [{"id": 10}, {"id": 20}]
        mock_client.client.export_zip.return_value = self._make_theme_zip(
            [{"theme_name": "Dark"}, {"theme_name": "Light"}]
        )
        mock_client_cls.from_context.return_value = mock_client

        assets = MagicMock()
        assets.charts = None
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = _make_asset_selection(selection="all")
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        execute_pull(cfg, tmp_path, dry_run=False, porcelain=False)

        # Should NOT use export_resource for themes
        mock_export.assert_not_called()
        # Should use export_zip instead
        mock_client.client.export_zip.assert_called_once_with("theme", [10, 20])
        # Verify files were written
        themes_dir = tmp_path / "assets" / "themes"
        assert themes_dir.exists()
        assert (themes_dir / "Dark.yaml").exists()
        assert (themes_dir / "Light.yaml").exists()

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("preset_cli.cli.superset.export.export_resource")
    def test_theme_pull_ids(self, mock_export, mock_client_cls, mock_ctx_cls, tmp_path):
        """Themes with selection=ids passes the correct IDs to export_zip."""
        mock_client = MagicMock()
        mock_client.client.export_zip.return_value = self._make_theme_zip(
            [{"theme_name": "Custom"}]
        )
        mock_client_cls.from_context.return_value = mock_client

        assets = MagicMock()
        assets.charts = None
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = _make_asset_selection(selection="ids", ids=[5])
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        execute_pull(cfg, tmp_path, dry_run=False, porcelain=False)

        mock_client.client.export_zip.assert_called_once_with("theme", [5])

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("preset_cli.cli.superset.export.export_resource")
    def test_theme_pull_empty_ids(self, mock_export, mock_client_cls, mock_ctx_cls, tmp_path):
        """Themes with empty ID list skips export_zip."""
        mock_client = MagicMock()
        mock_client.client.get_resources.return_value = []
        mock_client_cls.from_context.return_value = mock_client

        assets = MagicMock()
        assets.charts = None
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = _make_asset_selection(selection="all")
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        execute_pull(cfg, tmp_path, dry_run=False, porcelain=False)

        mock_client.client.export_zip.assert_not_called()

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("preset_cli.cli.superset.export.export_resource")
    def test_theme_pull_path_traversal_blocked(
        self, mock_export, mock_client_cls, mock_ctx_cls, tmp_path
    ):
        """Themes with path-traversal ZIP entries raise ValueError."""
        import io
        from zipfile import ZipFile

        buf = io.BytesIO()
        with ZipFile(buf, "w") as zf:
            zf.writestr("bundle/../../../etc/passwd", "evil")
        buf.seek(0)

        mock_client = MagicMock()
        mock_client.client.get_resources.return_value = [{"id": 1}]
        mock_client.client.export_zip.return_value = buf
        mock_client_cls.from_context.return_value = mock_client

        assets = MagicMock()
        assets.charts = None
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = _make_asset_selection(selection="all")
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        with pytest.raises(Exception):
            execute_pull(cfg, tmp_path, dry_run=False, porcelain=False)

    @patch("sup.config.settings.SupContext")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("preset_cli.cli.superset.export.export_resource")
    def test_theme_pull_non_utf8_raises(self, mock_export, mock_client_cls, mock_ctx_cls, tmp_path):
        """Non-UTF-8 content in a theme ZIP entry raises ValueError."""
        import io
        from zipfile import ZipFile

        buf = io.BytesIO()
        with ZipFile(buf, "w") as zf:
            zf.writestr("bundle/themes/bad.yaml", b"\xff\xfe not valid utf-8")
        buf.seek(0)

        mock_client = MagicMock()
        mock_client.client.get_resources.return_value = [{"id": 1}]
        mock_client.client.export_zip.return_value = buf
        mock_client_cls.from_context.return_value = mock_client

        assets = MagicMock()
        assets.charts = None
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = _make_asset_selection(selection="all")
        cfg = _make_sync_config(assets=assets)
        cfg.assets_folder.return_value = tmp_path / "assets"

        with pytest.raises(ValueError, match="Non-UTF-8 content in theme export"):
            execute_pull(cfg, tmp_path, dry_run=False, porcelain=False)

    @patch("sup.commands.sync.console")
    def test_theme_pull_dry_run(self, mock_console):
        """Dry run with themes shows preview."""
        assets = MagicMock()
        assets.charts = None
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = _make_asset_selection(selection="all")
        cfg = _make_sync_config(assets=assets)

        execute_pull(cfg, Path("/tmp/s"), dry_run=True, porcelain=False)
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("themes" in c for c in calls)

    @patch("sup.commands.sync.console")
    def test_push_warns_about_themes(self, mock_console):
        """execute_push warns when themes are configured."""
        assets = MagicMock()
        assets.charts = None
        assets.dashboards = None
        assets.datasets = None
        assets.databases = None
        assets.themes = _make_asset_selection(selection="all")
        cfg = _make_sync_config(assets=assets)
        target = _make_target()

        execute_push(cfg, [target], Path("/tmp/s"), dry_run=True, porcelain=False)
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("pull-only" in c for c in calls)

    @patch("preset_cli.cli.superset.sync.native.command.raise_helper")
    @patch("preset_cli.cli.superset.sync.native.command.load_user_modules")
    @patch("preset_cli.cli.superset.sync.native.command.render_yaml")
    @patch("preset_cli.cli.superset.sync.native.command.is_yaml_config")
    @patch("preset_cli.cli.superset.sync.native.command.import_resources_individually")
    @patch("preset_cli.cli.superset.sync.native.command.ResourceType")
    @patch("sup.clients.superset.SupSupersetClient")
    @patch("sup.config.settings.SupContext")
    def test_push_skips_theme_yaml_files(
        self,
        mock_ctx,
        mock_client_cls,
        mock_rt,
        mock_import,
        mock_is_yaml,
        mock_render,
        mock_load,
        mock_raise,
        tmp_path,
    ):
        """Theme YAML files in assets/themes/ are skipped during push."""
        mock_client = MagicMock()
        mock_client.client.baseurl = "https://test.preset.io"
        mock_client_cls.from_context.return_value = mock_client

        assets = tmp_path / "assets"
        themes_dir = assets / "themes"
        themes_dir.mkdir(parents=True)
        (themes_dir / "dark.yaml").write_text("theme_name: Dark")

        cfg = _make_sync_config()
        cfg.assets_folder.return_value = assets
        target = _make_target()

        mock_is_yaml.return_value = True
        mock_render.return_value = {"theme_name": "Dark"}
        mock_rt.ASSET.metadata_type = "assets"

        execute_push(cfg, [target], tmp_path, dry_run=False, porcelain=False)
        # Theme files should be skipped, so import should not be called
        mock_import.assert_not_called()
