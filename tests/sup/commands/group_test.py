"""Tests for sup.commands.group module."""

import csv
import io
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml
from typer.testing import CliRunner

from sup.commands.group import (
    SCIM_INITIAL_TOTAL,
    SCIM_PAGE_SIZE,
    app,
    create_scim_group,
    delete_scim_group,
    display_groups_csv,
    display_groups_table,
    display_sync_plan,
    display_sync_results,
    execute_group_sync,
    get_all_groups,
    needs_update,
    plan_group_sync,
    save_groups_to_file,
    update_scim_group,
)

runner = CliRunner()


def _make_spinner_cm(obj=None):
    cm = MagicMock()
    sp = obj or MagicMock()
    cm.__enter__ = MagicMock(return_value=sp)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, sp


SAMPLE_GROUPS = [
    {
        "id": "g1",
        "displayName": "Engineers",
        "members": [
            {"value": "a@co.com", "display": "Alice"},
            {"value": "b@co.com", "display": "Bob"},
        ],
    },
    {
        "id": "g2",
        "displayName": "Analysts",
        "members": [],
    },
]


# Patch targets for local imports inside functions
_P_CTX = "sup.config.settings.SupContext"
_P_AUTH = "sup.auth.preset.get_preset_auth"
_P_PC = "preset_cli.api.clients.preset.PresetClient"
_P_DS = "sup.output.spinners.data_spinner"
_P_SP = "sup.output.spinners.spinner"


# ---------------------------------------------------------------------------
# list_groups
# ---------------------------------------------------------------------------


class TestListGroups:

    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_no_teams(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm
        client = MagicMock()
        client.get_teams.return_value = []
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "No teams found" in result.output

    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_no_teams_porcelain(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm
        client = MagicMock()
        client.get_teams.return_value = []
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["list", "--porcelain"])
        assert result.exit_code == 0
        assert "No teams found" not in result.output

    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_single_team_auto_select(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm
        client = MagicMock()
        client.get_teams.return_value = [{"name": "myteam", "title": "My Team"}]
        client.get_group_membership.return_value = {
            "totalResults": 1,
            "Resources": SAMPLE_GROUPS[:1],
        }
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        assert "Engineers" in result.output

    @patch("sup.commands.group.typer.prompt", return_value="chosen")
    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_multiple_teams_prompt(
        self, mock_ctx, mock_auth, mock_pc_cls, mock_ds, mock_prompt
    ):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm
        client = MagicMock()
        client.get_teams.return_value = [
            {"name": "t1", "title": "Team 1"},
            {"name": "t2", "title": "Team 2"},
        ]
        client.get_group_membership.return_value = {
            "totalResults": 0,
            "Resources": [],
        }
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0

    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_pagination(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm
        client = MagicMock()
        page1 = [{"id": f"g{i}", "displayName": f"G{i}", "members": []} for i in range(100)]
        page2 = [{"id": "g100", "displayName": "G100", "members": []}]
        client.get_group_membership.side_effect = [
            {"totalResults": 101, "Resources": page1},
            {"totalResults": 101, "Resources": page2},
        ]
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["list", "--team", "t1"])
        assert result.exit_code == 0
        assert client.get_group_membership.call_count == 2

    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_with_limit(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm
        client = MagicMock()
        groups = [{"id": f"g{i}", "displayName": f"G{i}", "members": []} for i in range(5)]
        client.get_group_membership.return_value = {"totalResults": 5, "Resources": groups}
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["list", "--team", "t1", "--limit", "2"])
        assert result.exit_code == 0

    @patch("sup.commands.group.save_groups_to_file")
    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_save_file(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds, mock_save):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm
        client = MagicMock()
        client.get_group_membership.return_value = {
            "totalResults": 1,
            "Resources": SAMPLE_GROUPS[:1],
        }
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["list", "--team", "t1", "--save", "/tmp/groups.yaml"])
        assert result.exit_code == 0
        assert "Saved groups" in result.output
        mock_save.assert_called_once()

    @patch("sup.commands.group.save_groups_to_file")
    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_save_file_porcelain(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds, mock_save):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm
        client = MagicMock()
        client.get_group_membership.return_value = {
            "totalResults": 1,
            "Resources": SAMPLE_GROUPS[:1],
        }
        mock_pc_cls.return_value = client

        result = runner.invoke(
            app, ["list", "--team", "t1", "--save", "/tmp/groups.yaml", "--porcelain"]
        )
        assert result.exit_code == 0
        assert "Saved groups" not in result.output

    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_porcelain_output(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm
        client = MagicMock()
        client.get_group_membership.return_value = {
            "totalResults": 2,
            "Resources": SAMPLE_GROUPS,
        }
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["list", "--team", "t1", "--porcelain"])
        assert result.exit_code == 0
        assert "g1\tEngineers\t2" in result.output
        assert "g2\tAnalysts\t0" in result.output

    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_json_output(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm
        client = MagicMock()
        client.get_group_membership.return_value = {
            "totalResults": 1,
            "Resources": SAMPLE_GROUPS[:1],
        }
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["list", "--team", "t1", "--json"])
        assert result.exit_code == 0
        assert "Engineers" in result.output

    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_yaml_output(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm
        client = MagicMock()
        client.get_group_membership.return_value = {
            "totalResults": 1,
            "Resources": SAMPLE_GROUPS[:1],
        }
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["list", "--team", "t1", "--yaml"])
        assert result.exit_code == 0
        assert "Engineers" in result.output

    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_csv_output(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm
        client = MagicMock()
        client.get_group_membership.return_value = {
            "totalResults": 1,
            "Resources": SAMPLE_GROUPS[:1],
        }
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["list", "--team", "t1", "--csv"])
        assert result.exit_code == 0

    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_table_output(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm
        client = MagicMock()
        client.get_group_membership.return_value = {
            "totalResults": 2,
            "Resources": SAMPLE_GROUPS,
        }
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["list", "--team", "t1"])
        assert result.exit_code == 0

    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX, side_effect=RuntimeError("fail"))
    def test_error_handling(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm

        result = runner.invoke(app, ["list", "--team", "t1"])
        assert result.exit_code != 0
        assert "Failed to list groups" in result.output

    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX, side_effect=RuntimeError("fail"))
    def test_error_handling_porcelain(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds):
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm

        result = runner.invoke(app, ["list", "--team", "t1", "--porcelain"])
        assert result.exit_code != 0
        assert "Failed to list groups" not in result.output

    @patch("typer.prompt", return_value="t1")
    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_multiple_teams_porcelain(
        self, mock_ctx, mock_auth, mock_pc_cls, mock_ds, mock_prompt
    ):
        """Branch 75->82: multiple teams with porcelain skips prompt display."""
        cm, sp = _make_spinner_cm()
        mock_ds.return_value = cm
        client = MagicMock()
        client.get_teams.return_value = [
            {"name": "t1", "title": "Team 1"},
            {"name": "t2", "title": "Team 2"},
        ]
        client.get_group_membership.return_value = {
            "totalResults": 1,
            "Resources": [{"id": "g1", "displayName": "G1", "members": []}],
        }
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["list", "--porcelain"])
        assert result.exit_code == 0

    @patch(_P_DS)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_spinner_none(self, mock_ctx, mock_auth, mock_pc_cls, mock_ds):
        """Branch 100->58: spinner returns None (porcelain mode)."""
        cm, _ = _make_spinner_cm(obj=None)
        cm.__enter__ = MagicMock(return_value=None)
        mock_ds.return_value = cm
        client = MagicMock()
        client.get_group_membership.return_value = {
            "totalResults": 1,
            "Resources": [{"id": "g1", "displayName": "G1", "members": []}],
        }
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["list", "--team", "t1", "--porcelain"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# sync_groups
# ---------------------------------------------------------------------------


class TestSyncGroups:

    def test_config_not_found(self, tmp_path):
        result = runner.invoke(app, ["sync", str(tmp_path / "missing.yml")])
        assert result.exit_code != 0
        assert "Configuration file not found" in result.output

    def test_config_not_found_porcelain(self, tmp_path):
        result = runner.invoke(
            app, ["sync", str(tmp_path / "missing.yml"), "--porcelain"]
        )
        assert result.exit_code != 0
        assert "Configuration file not found" not in result.output

    def test_invalid_config_no_groups_key(self, tmp_path):
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"teams": []}))
        result = runner.invoke(app, ["sync", str(cfg)])
        assert result.exit_code != 0
        assert "Invalid configuration" in result.output

    def test_invalid_config_no_groups_key_porcelain(self, tmp_path):
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"teams": []}))
        result = runner.invoke(app, ["sync", str(cfg), "--porcelain"])
        assert result.exit_code != 0
        assert "Invalid configuration" not in result.output

    @patch("sup.commands.group.get_all_groups", return_value=[])
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_no_teams(self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_gag, tmp_path):
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "G1", "members": []}]}))
        client = MagicMock()
        client.get_teams.return_value = []
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["sync", str(cfg)])
        assert result.exit_code == 0
        assert "No teams found" in result.output

    @patch("sup.commands.group.get_all_groups", return_value=[])
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_no_teams_porcelain(self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_gag, tmp_path):
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "G1", "members": []}]}))
        client = MagicMock()
        client.get_teams.return_value = []
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["sync", str(cfg), "--porcelain"])
        assert result.exit_code == 0

    @patch("sup.commands.group.get_all_groups", return_value=[])
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_single_team_auto(self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_gag, tmp_path):
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "G1", "members": []}]}))
        client = MagicMock()
        client.get_teams.return_value = ["onlyteam"]
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["sync", str(cfg)])
        assert result.exit_code == 0

    @patch("sup.commands.group.typer.prompt", return_value="t1")
    @patch("sup.commands.group.get_all_groups", return_value=[])
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_multiple_teams_prompt(
        self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_gag, mock_prompt, tmp_path
    ):
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "G1", "members": []}]}))
        client = MagicMock()
        client.get_teams.return_value = ["t1", "t2"]
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["sync", str(cfg)])
        assert result.exit_code == 0

    @patch("sup.commands.group.get_all_groups")
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_all_in_sync(self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_gag, tmp_path):
        cfg = tmp_path / "config.yml"
        cfg.write_text(
            yaml.dump({"groups": [{"name": "Engineers", "members": [{"email": "a@co.com"}]}]})
        )
        mock_gag.return_value = [
            {"id": "g1", "displayName": "Engineers", "members": [{"value": "a@co.com"}]}
        ]
        mock_pc_cls.return_value = MagicMock()

        result = runner.invoke(app, ["sync", str(cfg), "--team", "t1"])
        assert result.exit_code == 0
        assert "already in sync" in result.output

    @patch("sup.commands.group.execute_group_sync")
    @patch("sup.commands.group.get_all_groups", return_value=[])
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_dry_run(self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_gag, mock_exec, tmp_path):
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "New", "members": []}]}))
        mock_pc_cls.return_value = MagicMock()

        result = runner.invoke(app, ["sync", str(cfg), "--team", "t1", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run complete" in result.output
        mock_exec.assert_not_called()

    @patch("sup.commands.group.typer.confirm", return_value=False)
    @patch("sup.commands.group.execute_group_sync")
    @patch("sup.commands.group.get_all_groups", return_value=[])
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_confirm_cancel(
        self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_gag, mock_exec, mock_confirm, tmp_path
    ):
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "New", "members": []}]}))
        mock_pc_cls.return_value = MagicMock()

        result = runner.invoke(app, ["sync", str(cfg), "--team", "t1"])
        assert "cancelled" in result.output

    @patch("sup.commands.group.display_sync_results")
    @patch("sup.commands.group.typer.confirm", return_value=True)
    @patch("sup.commands.group.execute_group_sync")
    @patch("sup.commands.group.get_all_groups", return_value=[])
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_confirm_accept(
        self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_gag, mock_exec, mock_confirm, mock_disp, tmp_path
    ):
        """Branch 255->260: user confirms (not force, not porcelain, confirm=True)."""
        cm, sp = _make_spinner_cm()
        mock_sp.return_value = cm
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "New", "members": []}]}))
        mock_pc_cls.return_value = MagicMock()
        mock_exec.return_value = {"created": 1, "updated": 0, "deleted": 0, "errors": 0, "total": 1}

        result = runner.invoke(app, ["sync", str(cfg), "--team", "t1"])
        assert result.exit_code == 0
        mock_exec.assert_called_once()

    @patch("sup.commands.group.display_sync_results")
    @patch("sup.commands.group.execute_group_sync")
    @patch("sup.commands.group.get_all_groups", return_value=[])
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_force_execute(
        self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_gag, mock_exec, mock_disp, tmp_path
    ):
        cm, sp = _make_spinner_cm()
        mock_sp.return_value = cm

        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "New", "members": []}]}))
        mock_pc_cls.return_value = MagicMock()
        mock_exec.return_value = {"created": 1, "updated": 0, "deleted": 0, "errors": 0, "total": 1}

        result = runner.invoke(app, ["sync", str(cfg), "--team", "t1", "--force"])
        assert result.exit_code == 0
        mock_exec.assert_called_once()
        mock_disp.assert_called_once()

    @patch("sup.commands.group.execute_group_sync")
    @patch("sup.commands.group.get_all_groups", return_value=[])
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_porcelain_results(
        self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_gag, mock_exec, tmp_path
    ):
        cm, sp = _make_spinner_cm()
        mock_sp.return_value = cm

        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "New", "members": []}]}))
        mock_pc_cls.return_value = MagicMock()
        mock_exec.return_value = {"created": 1, "updated": 2, "deleted": 0, "errors": 0, "total": 3}

        result = runner.invoke(
            app, ["sync", str(cfg), "--team", "t1", "--force", "--porcelain"]
        )
        assert result.exit_code == 0
        assert "created:1" in result.output
        assert "updated:2" in result.output
        assert "deleted:0" in result.output
        assert "errors:0" in result.output

    @patch(_P_PC, side_effect=RuntimeError("auth fail"))
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_error_handling(self, mock_ctx, mock_auth, mock_pc_cls, tmp_path):
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "G1", "members": []}]}))

        result = runner.invoke(app, ["sync", str(cfg), "--team", "t1"])
        assert result.exit_code != 0
        assert "Failed to sync groups" in result.output

    @patch(_P_PC, side_effect=RuntimeError("auth fail"))
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_error_handling_porcelain(self, mock_ctx, mock_auth, mock_pc_cls, tmp_path):
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "G1", "members": []}]}))

        result = runner.invoke(app, ["sync", str(cfg), "--team", "t1", "--porcelain"])
        assert result.exit_code != 0
        assert "Failed to sync groups" not in result.output

    @patch("sup.commands.group.get_all_groups", return_value=[])
    @patch("sup.commands.group.plan_group_sync", return_value={"create": [], "update": [], "delete": []})
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_multiple_teams_porcelain(
        self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_pgs, mock_gag, tmp_path
    ):
        """Branch 223->230: multiple teams with porcelain skips prompt."""
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "G1", "members": []}]}))
        client = MagicMock()
        client.get_teams.return_value = ["team_a", "team_b"]
        mock_pc_cls.return_value = client

        # porcelain=True and no --team: 'if not porcelain' is False -> skips to 230
        # team stays None, which is fine for mocked get_all_groups
        result = runner.invoke(app, ["sync", str(cfg), "--porcelain"])
        assert result.exit_code == 0

    @patch("sup.commands.group.get_all_groups", return_value=[])
    @patch("sup.commands.group.plan_group_sync", return_value={"create": [], "update": [], "delete": []})
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_all_in_sync_porcelain(
        self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_pgs, mock_gag, tmp_path
    ):
        """Branch 237->242: all in sync with porcelain."""
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "G1", "members": []}]}))
        mock_pc_cls.return_value = MagicMock()

        result = runner.invoke(app, ["sync", str(cfg), "--team", "t1", "--porcelain"])
        assert result.exit_code == 0
        assert "All groups are already in sync" not in result.output

    @patch("sup.commands.group.execute_group_sync", return_value={"created": 1, "updated": 0, "deleted": 0, "errors": 0, "total": 1})
    @patch("sup.commands.group.get_all_groups", return_value=[])
    @patch("sup.commands.group.plan_group_sync", return_value={"create": [{"name": "G1", "members": []}], "update": [], "delete": []})
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_dry_run_porcelain(
        self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_pgs, mock_gag, mock_exec, tmp_path
    ):
        """Branch 249->251: dry_run with porcelain."""
        cm, sp = _make_spinner_cm()
        mock_sp.return_value = cm
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "G1", "members": []}]}))
        mock_pc_cls.return_value = MagicMock()

        result = runner.invoke(
            app, ["sync", str(cfg), "--team", "t1", "--dry-run", "--porcelain"]
        )
        assert result.exit_code == 0
        assert "Dry run complete" not in result.output

    @patch("sup.commands.group.execute_group_sync", return_value={"created": 1, "updated": 0, "deleted": 0, "errors": 0, "total": 1})
    @patch("sup.commands.group.display_sync_results")
    @patch("sup.commands.group.get_all_groups", return_value=[])
    @patch("sup.commands.group.plan_group_sync", return_value={"create": [{"name": "G1", "members": []}], "update": [], "delete": []})
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_force_porcelain_spinner_none(
        self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_pgs, mock_gag, mock_dsr, mock_exec, tmp_path
    ):
        """Branches 263->260: porcelain with force, spinner returns None."""
        cm, _ = _make_spinner_cm()
        cm.__enter__ = MagicMock(return_value=None)
        mock_sp.return_value = cm
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "G1", "members": []}]}))
        mock_pc_cls.return_value = MagicMock()

        result = runner.invoke(
            app, ["sync", str(cfg), "--team", "t1", "--force", "--porcelain"]
        )
        assert result.exit_code == 0

    @patch("sup.commands.group.execute_group_sync", return_value={"created": 1, "updated": 0, "deleted": 0, "errors": 0, "total": 1})
    @patch("sup.commands.group.display_sync_results")
    @patch("sup.commands.group.get_all_groups", return_value=[])
    @patch("sup.commands.group.plan_group_sync", return_value={"create": [{"name": "G1", "members": []}], "update": [], "delete": []})
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_porcelain_skips_confirm(
        self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_pgs, mock_gag, mock_dsr, mock_exec, tmp_path
    ):
        """Branch 255->260: porcelain (no force) skips confirm prompt."""
        cm, _ = _make_spinner_cm()
        mock_sp.return_value = cm
        cfg = tmp_path / "config.yml"
        cfg.write_text(yaml.dump({"groups": [{"name": "G1", "members": []}]}))
        mock_pc_cls.return_value = MagicMock()

        # --porcelain without --force: 'not force and not porcelain' = True and False = False
        result = runner.invoke(
            app, ["sync", str(cfg), "--team", "t1", "--porcelain"]
        )
        assert result.exit_code == 0
        assert "created:1" in result.output


# ---------------------------------------------------------------------------
# create_group
# ---------------------------------------------------------------------------


class TestCreateGroup:

    @patch("sup.commands.group.create_scim_group")
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_no_teams(self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_csg):
        cm, _ = _make_spinner_cm()
        mock_sp.return_value = cm
        client = MagicMock()
        client.get_teams.return_value = []
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["create", "MyGroup"])
        assert result.exit_code == 0
        assert "No teams found" in result.output

    @patch("sup.commands.group.create_scim_group")
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_no_teams_porcelain(self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_csg):
        cm, _ = _make_spinner_cm()
        mock_sp.return_value = cm
        client = MagicMock()
        client.get_teams.return_value = []
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["create", "MyGroup", "--porcelain"])
        assert result.exit_code == 0
        assert "No teams found" not in result.output

    @patch("sup.commands.group.create_scim_group", return_value={"id": "new1"})
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_single_team(self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_csg):
        cm, _ = _make_spinner_cm()
        mock_sp.return_value = cm
        client = MagicMock()
        client.get_teams.return_value = [{"name": "t1", "title": "T1"}]
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["create", "MyGroup"])
        assert result.exit_code == 0
        assert "Created group" in result.output
        assert "new1" in result.output

    @patch("sup.commands.group.typer.prompt", return_value="t2")
    @patch("sup.commands.group.create_scim_group", return_value={"id": "new2"})
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_multiple_teams_prompt(
        self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_csg, mock_prompt
    ):
        cm, _ = _make_spinner_cm()
        mock_sp.return_value = cm
        client = MagicMock()
        client.get_teams.return_value = [
            {"name": "t1", "title": "T1"},
            {"name": "t2", "title": "T2"},
        ]
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["create", "MyGroup"])
        assert result.exit_code == 0

    @patch("sup.commands.group.create_scim_group", return_value={"id": "new3"})
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_with_members_warning(self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_csg):
        cm, _ = _make_spinner_cm()
        mock_sp.return_value = cm
        mock_pc_cls.return_value = MagicMock()

        result = runner.invoke(
            app, ["create", "MyGroup", "--team", "t1", "--member", "a@co.com"]
        )
        assert result.exit_code == 0
        assert "not yet implemented" in result.output

    @patch("sup.commands.group.create_scim_group", return_value={"id": "p1"})
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_porcelain_output(self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_csg):
        cm, _ = _make_spinner_cm()
        mock_sp.return_value = cm
        mock_pc_cls.return_value = MagicMock()

        result = runner.invoke(
            app, ["create", "MyGroup", "--team", "t1", "--porcelain"]
        )
        assert result.exit_code == 0
        assert "p1\tMyGroup" in result.output

    @patch("sup.commands.group.typer.prompt", return_value="t1")
    @patch("sup.commands.group.create_scim_group", return_value={"id": "p2"})
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_multiple_teams_porcelain(
        self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_csg, mock_prompt
    ):
        """Branch 329->336: multiple teams with porcelain."""
        cm, _ = _make_spinner_cm()
        mock_sp.return_value = cm
        client = MagicMock()
        client.get_teams.return_value = [
            {"name": "t1", "title": "T1"},
            {"name": "t2", "title": "T2"},
        ]
        mock_pc_cls.return_value = client

        result = runner.invoke(app, ["create", "MyGroup", "--porcelain"])
        assert result.exit_code == 0

    @patch("sup.commands.group.create_scim_group", return_value={"id": "p3"})
    @patch(_P_SP)
    @patch(_P_PC)
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_with_members_porcelain(self, mock_ctx, mock_auth, mock_pc_cls, mock_sp, mock_csg):
        """Branch 346->354: members warning with porcelain."""
        cm, _ = _make_spinner_cm()
        mock_sp.return_value = cm
        mock_pc_cls.return_value = MagicMock()

        result = runner.invoke(
            app, ["create", "MyGroup", "--team", "t1", "--member", "a@co.com", "--porcelain"]
        )
        assert result.exit_code == 0
        assert "not yet implemented" not in result.output

    @patch(_P_SP)
    @patch(_P_PC, side_effect=RuntimeError("boom"))
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_error(self, mock_ctx, mock_auth, mock_pc_cls, mock_sp):
        cm, _ = _make_spinner_cm()
        mock_sp.return_value = cm

        result = runner.invoke(app, ["create", "MyGroup", "--team", "t1"])
        assert result.exit_code != 0
        assert "Failed to create group" in result.output

    @patch(_P_SP)
    @patch(_P_PC, side_effect=RuntimeError("boom"))
    @patch(_P_AUTH)
    @patch(_P_CTX)
    def test_error_porcelain(self, mock_ctx, mock_auth, mock_pc_cls, mock_sp):
        cm, _ = _make_spinner_cm()
        mock_sp.return_value = cm

        result = runner.invoke(
            app, ["create", "MyGroup", "--team", "t1", "--porcelain"]
        )
        assert result.exit_code != 0
        assert "Failed to create group" not in result.output


# ---------------------------------------------------------------------------
# get_all_groups
# ---------------------------------------------------------------------------


class TestGetAllGroups:

    def test_single_page(self):
        client = MagicMock()
        client.get_group_membership.return_value = {
            "totalResults": 2,
            "Resources": SAMPLE_GROUPS,
        }
        result = get_all_groups(client, "t1")
        assert len(result) == 2

    def test_multi_page(self):
        client = MagicMock()
        client.get_group_membership.side_effect = [
            {"totalResults": 150, "Resources": [{"id": f"g{i}"} for i in range(100)]},
            {"totalResults": 150, "Resources": [{"id": f"g{i}"} for i in range(100, 150)]},
        ]
        result = get_all_groups(client, "t1")
        assert len(result) == 150

    def test_empty(self):
        client = MagicMock()
        client.get_group_membership.return_value = {"totalResults": 0}
        result = get_all_groups(client, "t1")
        assert result == []


# ---------------------------------------------------------------------------
# display_groups_table
# ---------------------------------------------------------------------------


class TestDisplayGroupsTable:

    def test_with_members_gt_3(self):
        groups = [
            {
                "id": "g1",
                "displayName": "Big",
                "members": [{"display": f"User{i}", "value": f"u{i}@co.com"} for i in range(5)],
            }
        ]
        display_groups_table(groups, "team1")

    def test_with_members_le_3(self):
        groups = [
            {"id": "g1", "displayName": "Small", "members": [{"display": "Alice", "value": "a@co.com"}]}
        ]
        display_groups_table(groups, "team1")

    def test_no_members(self):
        groups = [{"id": "g1", "displayName": "Empty", "members": []}]
        display_groups_table(groups, "team1")

    def test_empty_groups(self):
        display_groups_table([], "team1")


# ---------------------------------------------------------------------------
# display_groups_csv
# ---------------------------------------------------------------------------


class TestDisplayGroupsCsv:

    def test_basic(self, capsys):
        display_groups_csv(SAMPLE_GROUPS)
        out = capsys.readouterr().out
        assert "ID,Name,Member Count,Members" in out
        assert "Engineers" in out


# ---------------------------------------------------------------------------
# save_groups_to_file
# ---------------------------------------------------------------------------


class TestSaveGroupsToFile:

    def test_csv(self, tmp_path):
        fp = tmp_path / "out.csv"
        save_groups_to_file(SAMPLE_GROUPS, fp, "team1")
        content = fp.read_text()
        assert "ID,Name,Member Count,Members" in content
        assert "Engineers" in content

    def test_yaml(self, tmp_path):
        fp = tmp_path / "out.yaml"
        save_groups_to_file(SAMPLE_GROUPS, fp, "team1")
        data = yaml.safe_load(fp.read_text())
        assert data["team"] == "team1"
        assert len(data["groups"]) == 2


# ---------------------------------------------------------------------------
# plan_group_sync
# ---------------------------------------------------------------------------


class TestPlanGroupSync:

    def test_create(self):
        desired = [{"name": "New", "members": []}]
        ops = plan_group_sync(desired, {})
        assert len(ops["create"]) == 1
        assert len(ops["update"]) == 0

    def test_update(self):
        desired = [{"name": "Eng", "members": [{"email": "new@co.com"}]}]
        existing = {"Eng": {"id": "g1", "displayName": "Eng", "members": [{"value": "old@co.com"}]}}
        ops = plan_group_sync(desired, existing)
        assert len(ops["update"]) == 1
        assert ops["update"][0]["id"] == "g1"

    def test_no_op(self):
        desired = [{"name": "Eng", "members": [{"email": "a@co.com"}]}]
        existing = {"Eng": {"id": "g1", "displayName": "Eng", "members": [{"value": "a@co.com"}]}}
        ops = plan_group_sync(desired, existing)
        assert len(ops["create"]) == 0
        assert len(ops["update"]) == 0
        assert len(ops["delete"]) == 0


# ---------------------------------------------------------------------------
# needs_update
# ---------------------------------------------------------------------------


class TestNeedsUpdate:

    def test_same_members(self):
        assert needs_update({"members": [{"email": "a@co.com"}]}, {"members": [{"value": "a@co.com"}]}) is False

    def test_different_members(self):
        assert needs_update({"members": [{"email": "b@co.com"}]}, {"members": [{"value": "a@co.com"}]}) is True

    def test_empty_both(self):
        assert needs_update({}, {}) is False


# ---------------------------------------------------------------------------
# display_sync_plan
# ---------------------------------------------------------------------------


class TestDisplaySyncPlan:

    def test_create_ops(self):
        ops = {"create": [{"name": "New", "members": [{"email": "x@co.com"}]}], "update": [], "delete": []}
        display_sync_plan(ops, dry_run=False)

    def test_update_ops(self):
        ops = {"create": [], "update": [{"name": "Eng"}], "delete": []}
        display_sync_plan(ops, dry_run=True)

    def test_delete_ops(self):
        ops = {"create": [], "update": [], "delete": [{"name": "Old"}]}
        display_sync_plan(ops, dry_run=False)

    def test_empty_ops(self):
        ops = {"create": [], "update": [], "delete": []}
        display_sync_plan(ops, dry_run=False)


# ---------------------------------------------------------------------------
# execute_group_sync
# ---------------------------------------------------------------------------


class TestExecuteGroupSync:

    def test_create_success(self):
        client = MagicMock()
        ops = {"create": [{"name": "New", "members": []}], "update": [], "delete": []}
        with patch("sup.commands.group.create_scim_group"):
            results = execute_group_sync(client, "t1", ops)
        assert results["created"] == 1
        assert results["total"] == 1

    def test_create_error(self):
        client = MagicMock()
        with patch("sup.commands.group.create_scim_group", side_effect=RuntimeError("fail")):
            ops = {"create": [{"name": "New", "members": []}], "update": [], "delete": []}
            results = execute_group_sync(client, "t1", ops)
        assert results["errors"] == 1

    def test_update_success(self):
        client = MagicMock()
        ops = {
            "create": [],
            "update": [{"id": "g1", "name": "Eng", "desired": {"members": [{"email": "a@co.com"}]}, "existing": {}}],
            "delete": [],
        }
        with patch("sup.commands.group.update_scim_group"):
            results = execute_group_sync(client, "t1", ops)
        assert results["updated"] == 1

    def test_update_error(self):
        client = MagicMock()
        ops = {
            "create": [],
            "update": [{"id": "g1", "name": "Eng", "desired": {"members": []}, "existing": {}}],
            "delete": [],
        }
        with patch("sup.commands.group.update_scim_group", side_effect=RuntimeError("fail")):
            results = execute_group_sync(client, "t1", ops)
        assert results["errors"] == 1

    def test_delete_success(self):
        client = MagicMock()
        ops = {"create": [], "update": [], "delete": [{"id": "g1", "name": "Old"}]}
        with patch("sup.commands.group.delete_scim_group"):
            results = execute_group_sync(client, "t1", ops)
        assert results["deleted"] == 1

    def test_delete_error(self):
        client = MagicMock()
        ops = {"create": [], "update": [], "delete": [{"id": "g1", "name": "Old"}]}
        with patch("sup.commands.group.delete_scim_group", side_effect=RuntimeError("fail")):
            results = execute_group_sync(client, "t1", ops)
        assert results["errors"] == 1


# ---------------------------------------------------------------------------
# display_sync_results
# ---------------------------------------------------------------------------


class TestDisplaySyncResults:

    def test_all_types(self):
        display_sync_results({"created": 1, "updated": 2, "deleted": 1, "errors": 1, "total": 4})

    def test_no_errors(self):
        display_sync_results({"created": 1, "updated": 0, "deleted": 0, "errors": 0, "total": 1})

    def test_only_errors(self):
        display_sync_results({"created": 0, "updated": 0, "deleted": 0, "errors": 2, "total": 0})


# ---------------------------------------------------------------------------
# create_scim_group
# ---------------------------------------------------------------------------


class TestCreateScimGroup:

    def test_success(self):
        client = MagicMock()
        url_mock = MagicMock()
        client.get_base_url.return_value = url_mock
        resp = MagicMock()
        resp.json.return_value = {"id": "new1"}
        client.session.post.return_value = resp

        result = create_scim_group(client, "t1", {"displayName": "Test"})
        assert result["id"] == "new1"
        resp.raise_for_status.assert_called_once()


# ---------------------------------------------------------------------------
# update_scim_group
# ---------------------------------------------------------------------------


class TestUpdateScimGroup:

    def test_success(self):
        client = MagicMock()
        url_mock = MagicMock()
        client.get_base_url.return_value = url_mock
        resp = MagicMock()
        resp.json.return_value = {"id": "g1"}
        client.session.patch.return_value = resp

        result = update_scim_group(client, "t1", "g1", {"Operations": []})
        assert result["id"] == "g1"
        resp.raise_for_status.assert_called_once()


# ---------------------------------------------------------------------------
# delete_scim_group
# ---------------------------------------------------------------------------


class TestDeleteScimGroup:

    def test_success(self):
        client = MagicMock()
        url_mock = MagicMock()
        client.get_base_url.return_value = url_mock
        resp = MagicMock()
        client.session.delete.return_value = resp

        delete_scim_group(client, "t1", "g1")
        resp.raise_for_status.assert_called_once()
