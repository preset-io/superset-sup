"""Tests for sup.commands.dbt module."""

import json
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from sup.commands.dbt import app, format_dbt_help

runner = CliRunner()

_P_CTX = "sup.config.settings.SupContext"
_P_CLIENT = "sup.clients.superset.SupSupersetClient"
_P_LEGACY_CORE = "preset_cli.cli.superset.sync.dbt.command.dbt_core"
_P_LEGACY_CLOUD = "preset_cli.cli.superset.sync.dbt.command.dbt_cloud"


def _mock_click_runner(exit_code=0, output=""):
    """Patch click.testing.CliRunner so the legacy invoke returns a controlled result."""
    mock_result = MagicMock()
    mock_result.exit_code = exit_code
    mock_result.output = output
    mock_runner_inst = MagicMock()
    mock_runner_inst.invoke.return_value = mock_result
    return patch("click.testing.CliRunner", return_value=mock_runner_inst), mock_runner_inst


# ---------------------------------------------------------------------------
# format_dbt_help
# ---------------------------------------------------------------------------


def test_format_dbt_help():
    result = format_dbt_help()
    assert "dbt to Superset synchronization" in result
    assert "Key Features:" in result
    assert "Supported Sources:" in result
    assert "Common Workflows:" in result


# ---------------------------------------------------------------------------
# sync_dbt_core
# ---------------------------------------------------------------------------


class TestSyncDbtCore:

    def test_manifest_not_found(self, tmp_path):
        result = runner.invoke(app, ["core", str(tmp_path / "missing.json")])
        assert result.exit_code != 0
        assert "Manifest file not found" in result.output

    def test_manifest_not_found_porcelain(self, tmp_path):
        result = runner.invoke(
            app, ["core", str(tmp_path / "missing.json"), "--porcelain"]
        )
        assert result.exit_code != 0
        assert "Manifest file not found" not in result.output

    def test_normal_output_messages(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")
        result = runner.invoke(
            app,
            [
                "core", str(manifest),
                "--select", "tag:mart",
                "--exclude", "tag:staging",
                "--import-db",
                "--exposures", "/tmp/exposures.yml",
                "--dry-run",
            ],
        )
        assert "Syncing dbt Core project" in result.output
        assert "Selected: tag:mart" in result.output
        assert "Excluded: tag:staging" in result.output
        assert "Will import database" in result.output
        assert "Will write exposures to" in result.output
        assert "DRY RUN" in result.output
        assert result.exit_code == 0

    def test_dry_run_returns_early(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")
        result = runner.invoke(app, ["core", str(manifest), "--dry-run"])
        assert result.exit_code == 0
        assert "DRY RUN" in result.output

    def test_dry_run_porcelain(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")
        result = runner.invoke(
            app, ["core", str(manifest), "--dry-run", "--porcelain"]
        )
        assert result.exit_code == 0
        assert "DRY RUN" not in result.output

    def test_success_with_workspace_id(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")

        click_patch, mock_runner_inst = _mock_click_runner(0, "sync output")

        with patch(_P_CTX) as mock_ctx_cls, \
             patch(_P_CLIENT) as mock_client_cls, \
             click_patch:
            mock_ctx_cls.return_value = MagicMock()
            mock_client_cls.from_context.return_value = MagicMock()
            result = runner.invoke(
                app, ["core", str(manifest), "--workspace-id", "42"]
            )

        assert result.exit_code == 0
        assert "Using workspace: 42" in result.output

    def test_success_without_workspace_id(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")

        click_patch, mock_runner_inst = _mock_click_runner(0, "")

        with patch(_P_CTX) as mock_ctx_cls, \
             patch(_P_CLIENT) as mock_client_cls, \
             click_patch:
            mock_ctx_cls.return_value = MagicMock()
            mock_client_cls.from_context.return_value = MagicMock()
            result = runner.invoke(app, ["core", str(manifest)])

        assert result.exit_code == 0

    def test_all_option_flags_in_cmd_args(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")

        click_patch, mock_runner_inst = _mock_click_runner(0, "")

        with patch(_P_CTX), \
             patch(_P_CLIENT), \
             click_patch:
            runner.invoke(
                app,
                [
                    "core", str(manifest),
                    "--project", "myproj",
                    "--target", "dev",
                    "--profiles", "/profiles.yml",
                    "--exposures", "/exposures.yml",
                    "--import-db",
                    "--disallow-edits",
                    "--external-url-prefix", "http://example.com",
                    "--select", "tag:a",
                    "--select", "tag:b",
                    "--exclude", "tag:c",
                    "--exposures-only",
                    "--preserve-metadata",
                    "--merge-metadata",
                    "--raise-failures",
                ],
            )

        call_args = mock_runner_inst.invoke.call_args
        cmd_args = call_args[0][1]  # second positional arg is the args list
        assert "--project" in cmd_args
        assert "myproj" in cmd_args
        assert "--target" in cmd_args
        assert "--profiles" in cmd_args
        assert "--import-db" in cmd_args
        assert "--disallow-edits" in cmd_args
        assert "--external-url-prefix" in cmd_args
        assert "--exposures-only" in cmd_args
        assert "--preserve-metadata" in cmd_args
        assert "--merge-metadata" in cmd_args
        assert "--raise-failures" in cmd_args
        assert cmd_args.count("--select") == 2
        assert cmd_args.count("--exclude") == 1

    def test_runner_fail_not_porcelain(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")

        click_patch, _ = _mock_click_runner(1, "some error")

        with patch(_P_CTX), patch(_P_CLIENT), click_patch:
            result = runner.invoke(app, ["core", str(manifest)])

        assert result.exit_code != 0
        assert "dbt sync failed" in result.output

    def test_runner_fail_porcelain(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")

        click_patch, _ = _mock_click_runner(2, "err")

        with patch(_P_CTX), patch(_P_CLIENT), click_patch:
            result = runner.invoke(app, ["core", str(manifest), "--porcelain"])

        assert result.exit_code != 0
        assert "dbt sync failed" not in result.output

    def test_success_with_output(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")

        click_patch, _ = _mock_click_runner(0, "Synced 3 models")

        with patch(_P_CTX), patch(_P_CLIENT), click_patch:
            result = runner.invoke(app, ["core", str(manifest)])

        assert result.exit_code == 0
        assert "dbt Core sync completed" in result.output

    def test_success_without_output(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")

        click_patch, _ = _mock_click_runner(0, "")

        with patch(_P_CTX), patch(_P_CLIENT), click_patch:
            result = runner.invoke(app, ["core", str(manifest)])

        assert result.exit_code == 0
        assert "dbt Core sync completed" in result.output

    @patch(_P_CTX, side_effect=RuntimeError("config broken"))
    def test_exception_not_porcelain(self, mock_ctx_cls, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")
        result = runner.invoke(app, ["core", str(manifest)])
        assert result.exit_code != 0
        assert "Sync failed" in result.output

    @patch(_P_CTX, side_effect=RuntimeError("config broken"))
    def test_exception_porcelain(self, mock_ctx_cls, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text("{}")
        result = runner.invoke(app, ["core", str(manifest), "--porcelain"])
        assert result.exit_code != 0
        assert "Sync failed" not in result.output


# ---------------------------------------------------------------------------
# sync_dbt_cloud
# ---------------------------------------------------------------------------


class TestSyncDbtCloud:

    @patch(_P_CTX)
    def test_no_token_not_porcelain(self, mock_ctx_cls):
        mock_ctx = MagicMock()
        mock_ctx.config.dbt_cloud_api_token = None
        mock_ctx.config.dbt_cloud_account_id = None
        mock_ctx.config.dbt_cloud_project_id = None
        mock_ctx.config.dbt_cloud_job_id = None
        mock_ctx_cls.return_value = mock_ctx

        with patch.dict("os.environ", {}, clear=True):
            result = runner.invoke(app, ["cloud"])
        assert result.exit_code != 0
        assert "dbt Cloud API token required" in result.output

    @patch(_P_CTX)
    def test_no_token_porcelain(self, mock_ctx_cls):
        mock_ctx = MagicMock()
        mock_ctx.config.dbt_cloud_api_token = None
        mock_ctx.config.dbt_cloud_account_id = None
        mock_ctx.config.dbt_cloud_project_id = None
        mock_ctx.config.dbt_cloud_job_id = None
        mock_ctx_cls.return_value = mock_ctx

        with patch.dict("os.environ", {}, clear=True):
            result = runner.invoke(app, ["cloud", "--porcelain"])
        assert result.exit_code != 0
        assert "dbt Cloud API token required" not in result.output

    @patch(_P_CTX)
    def test_token_from_arg(self, mock_ctx_cls):
        mock_ctx = MagicMock()
        mock_ctx.config.dbt_cloud_api_token = None
        mock_ctx.config.dbt_cloud_account_id = None
        mock_ctx.config.dbt_cloud_project_id = None
        mock_ctx.config.dbt_cloud_job_id = None
        mock_ctx_cls.return_value = mock_ctx

        result = runner.invoke(app, ["cloud", "my-token", "--dry-run"])
        assert result.exit_code == 0

    @patch(_P_CTX)
    def test_token_from_config(self, mock_ctx_cls):
        mock_ctx = MagicMock()
        mock_ctx.config.dbt_cloud_api_token = "config-token"
        mock_ctx.config.dbt_cloud_account_id = None
        mock_ctx.config.dbt_cloud_project_id = None
        mock_ctx.config.dbt_cloud_job_id = None
        mock_ctx_cls.return_value = mock_ctx

        result = runner.invoke(app, ["cloud", "--dry-run"])
        assert result.exit_code == 0

    @patch(_P_CTX)
    def test_token_from_env(self, mock_ctx_cls):
        mock_ctx = MagicMock()
        mock_ctx.config.dbt_cloud_api_token = None
        mock_ctx.config.dbt_cloud_account_id = None
        mock_ctx.config.dbt_cloud_project_id = None
        mock_ctx.config.dbt_cloud_job_id = None
        mock_ctx_cls.return_value = mock_ctx

        with patch.dict("os.environ", {"DBT_CLOUD_API_TOKEN": "env-token"}):
            result = runner.invoke(app, ["cloud", "--dry-run"])
        assert result.exit_code == 0

    @patch(_P_CTX)
    def test_normal_output_with_details(self, mock_ctx_cls):
        mock_ctx = MagicMock()
        mock_ctx.config.dbt_cloud_api_token = "tok"
        mock_ctx.config.dbt_cloud_account_id = 111
        mock_ctx.config.dbt_cloud_project_id = 222
        mock_ctx.config.dbt_cloud_job_id = 333
        mock_ctx_cls.return_value = mock_ctx

        result = runner.invoke(
            app,
            [
                "cloud", "--dry-run",
                "--select", "tag:a",
                "--exclude", "tag:b",
                "--exposures", "/exp.yml",
            ],
        )
        assert "Syncing dbt Cloud" in result.output
        assert "Account: 111" in result.output
        assert "Project: 222" in result.output
        assert "Job: 333" in result.output
        assert "Selected: tag:a" in result.output
        assert "Excluded: tag:b" in result.output
        assert "Will write exposures" in result.output
        assert "DRY RUN" in result.output

    @patch(_P_CTX)
    def test_dry_run_porcelain(self, mock_ctx_cls):
        mock_ctx = MagicMock()
        mock_ctx.config.dbt_cloud_api_token = "tok"
        mock_ctx.config.dbt_cloud_account_id = None
        mock_ctx.config.dbt_cloud_project_id = None
        mock_ctx.config.dbt_cloud_job_id = None
        mock_ctx_cls.return_value = mock_ctx

        result = runner.invoke(app, ["cloud", "--dry-run", "--porcelain"])
        assert result.exit_code == 0
        assert "DRY RUN" not in result.output

    def test_success_with_workspace_id(self):
        click_patch, _ = _mock_click_runner(0, "done")

        with patch(_P_CTX) as mock_ctx_cls, \
             patch(_P_CLIENT) as mock_client_cls, \
             click_patch:
            mock_ctx = MagicMock()
            mock_ctx.config.dbt_cloud_api_token = "tok"
            mock_ctx.config.dbt_cloud_account_id = None
            mock_ctx.config.dbt_cloud_project_id = None
            mock_ctx.config.dbt_cloud_job_id = None
            mock_ctx_cls.return_value = mock_ctx
            mock_client_cls.from_context.return_value = MagicMock()

            result = runner.invoke(app, ["cloud", "--workspace-id", "99"])
        assert result.exit_code == 0
        assert "Using workspace: 99" in result.output

    def test_success_without_workspace_id(self):
        click_patch, _ = _mock_click_runner(0, "")

        with patch(_P_CTX) as mock_ctx_cls, \
             patch(_P_CLIENT) as mock_client_cls, \
             click_patch:
            mock_ctx = MagicMock()
            mock_ctx.config.dbt_cloud_api_token = "tok"
            mock_ctx.config.dbt_cloud_account_id = None
            mock_ctx.config.dbt_cloud_project_id = None
            mock_ctx.config.dbt_cloud_job_id = None
            mock_ctx_cls.return_value = mock_ctx
            mock_client_cls.from_context.return_value = MagicMock()

            result = runner.invoke(app, ["cloud"])
        assert result.exit_code == 0

    def test_all_option_flags(self):
        click_patch, mock_runner_inst = _mock_click_runner(0, "")

        with patch(_P_CTX) as mock_ctx_cls, \
             patch(_P_CLIENT), \
             click_patch:
            mock_ctx = MagicMock()
            mock_ctx.config.dbt_cloud_api_token = "tok"
            mock_ctx.config.dbt_cloud_account_id = None
            mock_ctx.config.dbt_cloud_project_id = None
            mock_ctx.config.dbt_cloud_job_id = None
            mock_ctx_cls.return_value = mock_ctx

            runner.invoke(
                app,
                [
                    "cloud", "mytoken", "111", "222", "333",
                    "--exposures", "/exp.yml",
                    "--disallow-edits",
                    "--external-url-prefix", "http://x.com",
                    "--select", "a",
                    "--exclude", "b",
                    "--exposures-only",
                    "--preserve-metadata",
                    "--merge-metadata",
                    "--access-url", "http://cloud.example.com",
                    "--raise-failures",
                    "--database-id", "5",
                    "--database-name", "mydb",
                ],
            )

        call_args = mock_runner_inst.invoke.call_args
        cmd_args = call_args[0][1]
        assert "mytoken" in cmd_args
        assert "111" in cmd_args
        assert "222" in cmd_args
        assert "333" in cmd_args
        assert "--exposures" in cmd_args
        assert "--disallow-edits" in cmd_args
        assert "--external-url-prefix" in cmd_args
        assert "--exposures-only" in cmd_args
        assert "--preserve-metadata" in cmd_args
        assert "--merge-metadata" in cmd_args
        assert "--access-url" in cmd_args
        assert "--raise-failures" in cmd_args
        assert "--database-id" in cmd_args
        assert "--database-name" in cmd_args

    def test_runner_fail_not_porcelain(self):
        click_patch, _ = _mock_click_runner(1, "cloud error")

        with patch(_P_CTX) as mock_ctx_cls, \
             patch(_P_CLIENT), \
             click_patch:
            mock_ctx = MagicMock()
            mock_ctx.config.dbt_cloud_api_token = "tok"
            mock_ctx.config.dbt_cloud_account_id = None
            mock_ctx.config.dbt_cloud_project_id = None
            mock_ctx.config.dbt_cloud_job_id = None
            mock_ctx_cls.return_value = mock_ctx

            result = runner.invoke(app, ["cloud"])
        assert result.exit_code != 0
        assert "dbt Cloud sync failed" in result.output

    def test_runner_fail_porcelain(self):
        click_patch, _ = _mock_click_runner(1, "err")

        with patch(_P_CTX) as mock_ctx_cls, \
             patch(_P_CLIENT), \
             click_patch:
            mock_ctx = MagicMock()
            mock_ctx.config.dbt_cloud_api_token = "tok"
            mock_ctx.config.dbt_cloud_account_id = None
            mock_ctx.config.dbt_cloud_project_id = None
            mock_ctx.config.dbt_cloud_job_id = None
            mock_ctx_cls.return_value = mock_ctx

            result = runner.invoke(app, ["cloud", "--porcelain"])
        assert result.exit_code != 0
        assert "dbt Cloud sync failed" not in result.output

    def test_success_with_output(self):
        click_patch, _ = _mock_click_runner(0, "Synced 5 models")

        with patch(_P_CTX) as mock_ctx_cls, \
             patch(_P_CLIENT), \
             click_patch:
            mock_ctx = MagicMock()
            mock_ctx.config.dbt_cloud_api_token = "tok"
            mock_ctx.config.dbt_cloud_account_id = None
            mock_ctx.config.dbt_cloud_project_id = None
            mock_ctx.config.dbt_cloud_job_id = None
            mock_ctx_cls.return_value = mock_ctx

            result = runner.invoke(app, ["cloud"])
        assert result.exit_code == 0
        assert "dbt Cloud sync completed" in result.output

    def test_exception_not_porcelain(self):
        with patch(_P_CTX) as mock_ctx_cls, \
             patch(_P_CLIENT) as mock_client_cls, \
             patch("sup.commands.dbt.console") as mock_console:
            mock_ctx = MagicMock()
            mock_ctx.config.dbt_cloud_api_token = "tok"
            mock_ctx.config.dbt_cloud_account_id = None
            mock_ctx.config.dbt_cloud_project_id = None
            mock_ctx.config.dbt_cloud_job_id = None
            mock_ctx_cls.return_value = mock_ctx
            mock_client_cls.from_context.side_effect = RuntimeError("boom")

            result = runner.invoke(app, ["cloud"])
        assert result.exit_code != 0
        # console.print writes to Rich console (not captured by CliRunner),
        # so verify via the mock instead of result.output
        # console.print writes to Rich console (not captured by CliRunner),
        # so verify via the mock instead of result.output
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("Sync failed" in c for c in calls)

    def test_exception_porcelain(self):
        with patch(_P_CTX) as mock_ctx_cls, \
             patch(_P_CLIENT) as mock_client_cls:
            mock_ctx = MagicMock()
            mock_ctx.config.dbt_cloud_api_token = "tok"
            mock_ctx.config.dbt_cloud_account_id = None
            mock_ctx.config.dbt_cloud_project_id = None
            mock_ctx.config.dbt_cloud_job_id = None
            mock_ctx_cls.return_value = mock_ctx
            mock_client_cls.from_context.side_effect = RuntimeError("boom")

            result = runner.invoke(app, ["cloud", "--porcelain"])
        assert result.exit_code != 0
        assert "Sync failed" not in result.output


# ---------------------------------------------------------------------------
# list_models
# ---------------------------------------------------------------------------


class TestListModels:

    def test_manifest_not_found(self, tmp_path):
        result = runner.invoke(app, ["list-models", str(tmp_path / "nope.json")])
        assert result.exit_code != 0
        assert "Manifest file not found" in result.output

    @patch("preset_cli.cli.superset.sync.dbt.lib.apply_select")
    @patch("preset_cli.cli.superset.sync.dbt.schemas.ModelSchema")
    def test_table_format(self, mock_schema_cls, mock_apply, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "nodes": {
                        "model.proj.orders": {
                            "resource_type": "model",
                            "unique_id": "model.proj.orders",
                            "name": "orders",
                            "schema": "public",
                            "database": "analytics",
                            "tags": ["mart"],
                            "config": {"materialized": "table"},
                        }
                    },
                    "child_map": {"model.proj.orders": ["test.proj.test1"]},
                }
            )
        )

        mock_schema = MagicMock()
        mock_schema.load.return_value = {
            "name": "orders",
            "schema": "public",
            "database": "analytics",
            "tags": ["mart"],
            "config": {"materialized": "table"},
        }
        mock_schema_cls.return_value = mock_schema
        mock_apply.return_value = [mock_schema.load.return_value]

        result = runner.invoke(app, ["list-models", str(manifest)])
        assert result.exit_code == 0
        assert "orders" in result.output
        assert "Found 1 models" in result.output

    @patch("preset_cli.cli.superset.sync.dbt.lib.apply_select")
    @patch("preset_cli.cli.superset.sync.dbt.schemas.ModelSchema")
    def test_json_format(self, mock_schema_cls, mock_apply, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({"nodes": {}, "child_map": {}}))
        mock_schema_cls.return_value = MagicMock()
        mock_apply.return_value = []

        result = runner.invoke(app, ["list-models", str(manifest), "--format", "json"])
        assert result.exit_code == 0
        assert "[]" in result.output

    @patch("preset_cli.cli.superset.sync.dbt.lib.apply_select")
    @patch("preset_cli.cli.superset.sync.dbt.schemas.ModelSchema")
    def test_yaml_format(self, mock_schema_cls, mock_apply, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({"nodes": {}, "child_map": {}}))
        mock_schema_cls.return_value = MagicMock()
        mock_apply.return_value = []

        result = runner.invoke(app, ["list-models", str(manifest), "--format", "yaml"])
        assert result.exit_code == 0

    @patch("preset_cli.cli.superset.sync.dbt.lib.apply_select")
    @patch("preset_cli.cli.superset.sync.dbt.schemas.ModelSchema")
    def test_with_select_and_exclude(self, mock_schema_cls, mock_apply, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(json.dumps({"nodes": {}, "child_map": {}}))
        mock_schema_cls.return_value = MagicMock()
        mock_apply.return_value = []

        result = runner.invoke(
            app,
            ["list-models", str(manifest), "--select", "tag:mart", "--exclude", "tag:staging"],
        )
        assert result.exit_code == 0
        mock_apply.assert_called_once()
        call_args = mock_apply.call_args
        assert call_args[0][1] == ("tag:mart",)
        assert call_args[0][2] == ("tag:staging",)

    @patch("preset_cli.cli.superset.sync.dbt.lib.apply_select")
    @patch("preset_cli.cli.superset.sync.dbt.schemas.ModelSchema")
    def test_non_model_nodes_filtered(self, mock_schema_cls, mock_apply, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text(
            json.dumps(
                {
                    "nodes": {
                        "test.proj.test1": {"resource_type": "test", "unique_id": "test.proj.test1"},
                        "model.proj.m1": {"resource_type": "model", "unique_id": "model.proj.m1", "name": "m1"},
                    },
                    "child_map": {},
                }
            )
        )

        mock_schema = MagicMock()
        mock_schema.load.return_value = {
            "name": "m1", "schema": "public", "database": "db", "tags": [], "config": {"materialized": "view"},
        }
        mock_schema_cls.return_value = mock_schema
        mock_apply.return_value = [mock_schema.load.return_value]

        result = runner.invoke(app, ["list-models", str(manifest)])
        assert result.exit_code == 0
        assert mock_schema.load.call_count == 1

    def test_exception_handling(self, tmp_path):
        manifest = tmp_path / "manifest.json"
        manifest.write_text("not valid json {{{")

        result = runner.invoke(app, ["list-models", str(manifest)])
        assert result.exit_code != 0
        assert "Failed to parse manifest" in result.output
