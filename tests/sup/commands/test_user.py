"""Tests for sup.commands.user - 100% coverage."""

import json
from unittest.mock import MagicMock, patch

import yaml
from typer.testing import CliRunner

from sup.commands.user import app, display_user_details

runner = CliRunner()

PATCH_PRESET_CLIENT = "preset_cli.api.clients.preset.PresetClient"
PATCH_AUTH = "sup.auth.preset.get_preset_auth"
PATCH_CONTEXT = "sup.config.settings.SupContext"
PATCH_FILTERED = "preset_cli.cli.export_users.get_filtered_teams"
PATCH_MEMBERS = "preset_cli.cli.export_users.process_team_members"
PATCH_WORKSPACES = "preset_cli.cli.export_users.process_team_workspaces"
PATCH_CONVERT = "preset_cli.cli.export_users.convert_user_data_to_list"

SAMPLE_USERS = [
    {
        "id": 1,
        "email": "alice@example.com",
        "first_name": "Alice",
        "last_name": "Smith",
        "username": "alice",
        "role": ["Admin"],
    },
    {
        "id": 2,
        "email": "bob@example.com",
        "first_name": "Bob",
        "last_name": "Jones",
        "username": "bob",
        "role": ["Creator"],
    },
]

SIMPLE_USERS = [
    {"email": "u1@x.com", "first_name": "U", "last_name": "1", "username": "u1"},
]

WS_ROLES_USERS = [
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

EXPORT_USERS_LIST = [
    {"email": "a@b.com", "first_name": "A", "last_name": "B", "username": "ab"},
    {"email": "c@d.com", "first_name": "C", "last_name": "D", "username": "cd"},
]


def _spinner_mocks():
    cm = MagicMock()
    obj = MagicMock()
    cm.__enter__ = MagicMock(return_value=obj)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, obj


# ---------------------------------------------------------------------------
# list_users
# ---------------------------------------------------------------------------


class TestListUsers:
    def test_table_output(self):
        cm, obj = _spinner_mocks()
        mc = MagicMock()
        mc.client.export_users.return_value = iter(SAMPLE_USERS)

        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT
        ), patch("sup.clients.superset.SupSupersetClient.from_context", return_value=mc):
            r = runner.invoke(app, ["list"])
        assert r.exit_code == 0
        mc.display_users_table.assert_called_once()
        assert obj.text == "Found 2 users"

    def test_json_output(self):
        cm, _ = _spinner_mocks()
        mc = MagicMock()
        mc.client.export_users.return_value = iter(SAMPLE_USERS)

        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT
        ), patch("sup.clients.superset.SupSupersetClient.from_context", return_value=mc):
            r = runner.invoke(app, ["list", "--json"])
        assert r.exit_code == 0
        assert len(json.loads(r.output)) == 2

    def test_yaml_output(self):
        cm, _ = _spinner_mocks()
        mc = MagicMock()
        mc.client.export_users.return_value = iter(SAMPLE_USERS)

        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT
        ), patch("sup.clients.superset.SupSupersetClient.from_context", return_value=mc):
            r = runner.invoke(app, ["list", "--yaml"])
        assert r.exit_code == 0
        assert len(yaml.safe_load(r.output)) == 2

    def test_porcelain_output(self):
        cm, _ = _spinner_mocks()
        mc = MagicMock()
        mc.client.export_users.return_value = iter(SAMPLE_USERS)

        with patch("sup.output.spinners.data_spinner", return_value=cm) as mock_ds, patch(
            PATCH_CONTEXT
        ), patch("sup.clients.superset.SupSupersetClient.from_context", return_value=mc), patch(
            "sup.output.formatters.display_porcelain_list"
        ) as mock_p:
            r = runner.invoke(app, ["list", "--porcelain"])
        assert r.exit_code == 0
        mock_p.assert_called_once()
        mock_ds.assert_called_once_with("users", silent=True)

    def test_with_limit(self):
        cm, obj = _spinner_mocks()
        mc = MagicMock()
        mc.client.export_users.return_value = iter(SAMPLE_USERS)

        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT
        ), patch("sup.clients.superset.SupSupersetClient.from_context", return_value=mc):
            r = runner.invoke(app, ["list", "--limit", "1"])
        assert r.exit_code == 0
        assert len(mc.display_users_table.call_args[0][0]) == 1

    def test_spinner_none(self):
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=None)
        cm.__exit__ = MagicMock(return_value=False)
        mc = MagicMock()
        mc.client.export_users.return_value = iter(SAMPLE_USERS)

        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT
        ), patch("sup.clients.superset.SupSupersetClient.from_context", return_value=mc):
            r = runner.invoke(app, ["list"])
        assert r.exit_code == 0

    def test_error(self):
        cm, _ = _spinner_mocks()
        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT, side_effect=RuntimeError("fail")
        ):
            r = runner.invoke(app, ["list"])
        assert r.exit_code == 1
        assert "Failed to list users" in r.output

    def test_error_porcelain(self):
        cm, _ = _spinner_mocks()
        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT, side_effect=RuntimeError("fail")
        ):
            r = runner.invoke(app, ["list", "--porcelain"])
        assert r.exit_code == 1
        assert "Failed to list users" not in r.output


# ---------------------------------------------------------------------------
# user_info
# ---------------------------------------------------------------------------


class TestUserInfo:
    def test_found_table(self):
        cm, _ = _spinner_mocks()
        mc = MagicMock()
        mc.client.export_users.return_value = iter(SAMPLE_USERS)

        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT
        ), patch("sup.clients.superset.SupSupersetClient.from_context", return_value=mc), patch(
            "sup.commands.user.display_user_details"
        ) as md:
            r = runner.invoke(app, ["info", "1"])
        assert r.exit_code == 0
        md.assert_called_once()

    def test_found_porcelain(self):
        cm, _ = _spinner_mocks()
        mc = MagicMock()
        mc.client.export_users.return_value = iter(SAMPLE_USERS)

        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT
        ), patch("sup.clients.superset.SupSupersetClient.from_context", return_value=mc):
            r = runner.invoke(app, ["info", "1", "--porcelain"])
        assert r.exit_code == 0
        assert "1\talice@example.com\tAlice\tSmith" in r.output

    def test_found_json(self):
        cm, _ = _spinner_mocks()
        mc = MagicMock()
        mc.client.export_users.return_value = iter(SAMPLE_USERS)

        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT
        ), patch("sup.clients.superset.SupSupersetClient.from_context", return_value=mc):
            r = runner.invoke(app, ["info", "1", "--json"])
        assert r.exit_code == 0
        assert json.loads(r.output)["id"] == 1

    def test_found_yaml(self):
        cm, _ = _spinner_mocks()
        mc = MagicMock()
        mc.client.export_users.return_value = iter(SAMPLE_USERS)

        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT
        ), patch("sup.clients.superset.SupSupersetClient.from_context", return_value=mc):
            r = runner.invoke(app, ["info", "1", "--yaml"])
        assert r.exit_code == 0
        assert yaml.safe_load(r.output)["id"] == 1

    def test_not_found(self):
        cm, _ = _spinner_mocks()
        mc = MagicMock()
        mc.client.export_users.return_value = iter(SAMPLE_USERS)

        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT
        ), patch("sup.clients.superset.SupSupersetClient.from_context", return_value=mc):
            r = runner.invoke(app, ["info", "999"])
        assert r.exit_code == 1
        assert "User 999 not found" in r.output

    def test_not_found_porcelain(self):
        cm, _ = _spinner_mocks()
        mc = MagicMock()
        mc.client.export_users.return_value = iter(SAMPLE_USERS)

        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT
        ), patch("sup.clients.superset.SupSupersetClient.from_context", return_value=mc):
            r = runner.invoke(app, ["info", "999", "--porcelain"])
        assert r.exit_code == 1
        assert "not found" not in r.output

    def test_error(self):
        cm, _ = _spinner_mocks()
        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT, side_effect=RuntimeError("boom")
        ):
            r = runner.invoke(app, ["info", "1"])
        assert r.exit_code == 1
        assert "Failed to get user info" in r.output

    def test_error_porcelain(self):
        cm, _ = _spinner_mocks()
        with patch("sup.output.spinners.data_spinner", return_value=cm), patch(
            PATCH_CONTEXT, side_effect=RuntimeError("boom")
        ):
            r = runner.invoke(app, ["info", "1", "--porcelain"])
        assert r.exit_code == 1
        assert "Failed to get user info" not in r.output


# ---------------------------------------------------------------------------
# display_user_details
# ---------------------------------------------------------------------------


class TestDisplayUserDetails:
    def test_roles_as_list(self):
        user = {
            "id": 1,
            "email": "a@b.com",
            "first_name": "A",
            "last_name": "B",
            "username": "a",
            "role": ["Admin", "Creator"],
        }
        with patch("sup.commands.user.console") as mc:
            display_user_details(user)
            assert "Admin, Creator" in mc.print.call_args[0][0].renderable

    def test_roles_as_string(self):
        user = {
            "id": 2,
            "email": "b@b.com",
            "first_name": "B",
            "last_name": "J",
            "username": "b",
            "role": "Viewer",
        }
        with patch("sup.commands.user.console") as mc:
            display_user_details(user)
            assert "Viewer" in mc.print.call_args[0][0].renderable

    def test_empty_roles(self):
        user = {
            "id": 3,
            "email": "c@c.com",
            "first_name": "C",
            "last_name": "",
            "username": "c",
            "role": [],
        }
        with patch("sup.commands.user.console") as mc:
            display_user_details(user)
            assert "No roles" in mc.print.call_args[0][0].renderable

    def test_empty_name(self):
        user = {
            "id": 4,
            "email": "d@d.com",
            "first_name": "",
            "last_name": "",
            "username": "anon",
            "role": [],
        }
        with patch("sup.commands.user.console") as mc:
            display_user_details(user)
            panel = mc.print.call_args[0][0]
            assert "Name: Unknown" in panel.renderable
            assert "Unknown" in panel.title


# ---------------------------------------------------------------------------
# export_users
# ---------------------------------------------------------------------------


class TestPullUsers:
    @patch(PATCH_CONVERT, return_value=EXPORT_USERS_LIST)
    @patch(PATCH_WORKSPACES)
    @patch(PATCH_MEMBERS)
    @patch(PATCH_FILTERED, return_value=[{"name": "t1", "title": "T1"}])
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_default_yaml_file(self, _ctx, _auth, _c, _ft, _m, _w, _cv):
        with runner.isolated_filesystem():
            r = runner.invoke(app, ["pull", "out.yaml"])
            assert r.exit_code == 0
            assert "Pulled 2 users" in r.output
            with open("out.yaml") as f:
                assert len(yaml.safe_load(f)) == 2

    @patch(PATCH_CONVERT, return_value=EXPORT_USERS_LIST)
    @patch(PATCH_WORKSPACES)
    @patch(PATCH_MEMBERS)
    @patch(PATCH_FILTERED, return_value=[{"name": "t1", "title": "T1"}])
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_json_output(self, _ctx, _auth, _c, _ft, _m, _w, _cv):
        r = runner.invoke(app, ["pull", "--json"])
        assert r.exit_code == 0
        assert len(json.loads(r.output)) == 2

    @patch(PATCH_CONVERT, return_value=EXPORT_USERS_LIST)
    @patch(PATCH_WORKSPACES)
    @patch(PATCH_MEMBERS)
    @patch(PATCH_FILTERED, return_value=[{"name": "t1", "title": "T1"}])
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_yaml_stdout(self, _ctx, _auth, _c, _ft, _m, _w, _cv):
        r = runner.invoke(app, ["pull", "--yaml"])
        assert r.exit_code == 0
        assert len(yaml.safe_load(r.output)) == 2

    @patch(PATCH_CONVERT, return_value=EXPORT_USERS_LIST)
    @patch(PATCH_WORKSPACES)
    @patch(PATCH_MEMBERS)
    @patch(PATCH_FILTERED, return_value=[{"name": "t1", "title": "T1"}])
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_porcelain_output(self, _ctx, _auth, _c, _ft, _m, _w, _cv):
        r = runner.invoke(app, ["pull", "--porcelain"])
        assert r.exit_code == 0
        assert "a@b.com\tA\tB" in r.output
        assert "c@d.com\tC\tD" in r.output

    @patch(PATCH_FILTERED, return_value=[])
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_no_teams(self, _ctx, _auth, _c, _ft):
        r = runner.invoke(app, ["pull"])
        assert r.exit_code == 0
        assert "No teams" in r.output

    @patch(PATCH_FILTERED, return_value=[])
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_no_teams_porcelain(self, _ctx, _auth, _c, _ft):
        r = runner.invoke(app, ["pull", "--porcelain"])
        assert r.exit_code == 0
        assert "No teams" not in r.output

    @patch(PATCH_FILTERED, side_effect=RuntimeError("boom"))
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_error(self, _ctx, _auth, _c, _ft):
        r = runner.invoke(app, ["pull"])
        assert r.exit_code == 1
        assert "Failed to pull" in r.output

    @patch(PATCH_FILTERED, side_effect=RuntimeError("boom"))
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_error_porcelain(self, _ctx, _auth, _c, _ft):
        r = runner.invoke(app, ["pull", "--porcelain"])
        assert r.exit_code == 1
        assert "Failed to pull" not in r.output

    @patch(PATCH_CONVERT, return_value=EXPORT_USERS_LIST)
    @patch(PATCH_WORKSPACES)
    @patch(PATCH_MEMBERS)
    @patch(
        PATCH_FILTERED,
        return_value=[
            {"name": "t1", "title": "T1"},
            {"name": "t2", "title": "T2"},
        ],
    )
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_multiple_teams(self, _ctx, _auth, _c, _ft, _m, _w, _cv):
        with runner.isolated_filesystem():
            r = runner.invoke(app, ["pull", "out.yaml"])
            assert r.exit_code == 0

    @patch(PATCH_CONVERT, return_value=EXPORT_USERS_LIST)
    @patch(PATCH_WORKSPACES)
    @patch(PATCH_MEMBERS)
    @patch(PATCH_FILTERED, return_value=[{"name": "t1", "title": "T1"}])
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_team_filter(self, _ctx, _auth, _c, _ft, _m, _w, _cv):
        with runner.isolated_filesystem():
            r = runner.invoke(app, ["pull", "out.yaml", "--team", "T1"])
            assert r.exit_code == 0


# ---------------------------------------------------------------------------
# import_users_cmd
# ---------------------------------------------------------------------------


class TestPushUsers:
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_simple_format(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = [{"name": "t1", "title": "T1"}]
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["push", "u.yaml"])
        assert r.exit_code == 0
        MC.return_value.import_users.assert_called_once()

    @patch("preset_cli.cli.main.import_users_with_workspace_roles")
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_workspace_roles_format(self, _ctx, _auth, MC, mock_iw):
        MC.return_value.get_teams.return_value = [{"name": "t1", "title": "T1"}]
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(WS_ROLES_USERS, f)
            r = runner.invoke(app, ["push", "u.yaml"])
        assert r.exit_code == 0
        mock_iw.assert_called_once()

    def test_dry_run(self):
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["push", "u.yaml", "--dry-run"])
        assert r.exit_code == 0
        assert "Dry run" in r.output
        assert "u1@x.com" in r.output

    def test_dry_run_porcelain(self):
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["push", "u.yaml", "--dry-run", "--porcelain"])
        assert r.exit_code == 0
        assert "push\tu1@x.com" in r.output

    def test_file_not_found(self):
        with runner.isolated_filesystem():
            r = runner.invoke(app, ["push", "missing.yaml"])
        assert r.exit_code == 1
        assert "File not found" in r.output

    def test_file_not_found_porcelain(self):
        with runner.isolated_filesystem():
            r = runner.invoke(app, ["push", "missing.yaml", "--porcelain"])
        assert r.exit_code == 1
        assert "File not found" not in r.output

    def test_empty_file(self):
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                f.write("")
            r = runner.invoke(app, ["push", "u.yaml"])
        assert r.exit_code == 0
        assert "No users" in r.output

    def test_empty_file_porcelain(self):
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                f.write("")
            r = runner.invoke(app, ["push", "u.yaml", "--porcelain"])
        assert r.exit_code == 0

    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_no_teams(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = []
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["push", "u.yaml"])
        assert r.exit_code == 0

    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_porcelain_success(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = [{"name": "t1", "title": "T1"}]
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["push", "u.yaml", "--porcelain"])
        assert r.exit_code == 0
        assert "pushed:1" in r.output

    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_error(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = [{"name": "t1", "title": "T1"}]
        MC.return_value.import_users.side_effect = RuntimeError("boom")
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["push", "u.yaml"])
        assert r.exit_code == 1
        assert "Failed to push" in r.output

    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_error_porcelain(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = [{"name": "t1", "title": "T1"}]
        MC.return_value.import_users.side_effect = RuntimeError("boom")
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["push", "u.yaml", "--porcelain"])
        assert r.exit_code == 1
        assert "Failed to push" not in r.output


# ---------------------------------------------------------------------------
# invite_users
# ---------------------------------------------------------------------------


class TestInviteUsers:
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_success(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = [{"name": "t1", "title": "T1"}]
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["invite", "u.yaml"])
        assert r.exit_code == 0
        MC.return_value.invite_users.assert_called_once_with(["t1"], ["u1@x.com"])

    def test_dry_run(self):
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["invite", "u.yaml", "--dry-run"])
        assert r.exit_code == 0
        assert "Dry run" in r.output
        assert "u1@x.com" in r.output

    def test_dry_run_porcelain(self):
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["invite", "u.yaml", "--dry-run", "--porcelain"])
        assert r.exit_code == 0
        assert "invite\tu1@x.com" in r.output

    def test_file_not_found(self):
        with runner.isolated_filesystem():
            r = runner.invoke(app, ["invite", "missing.yaml"])
        assert r.exit_code == 1
        assert "File not found" in r.output

    def test_file_not_found_porcelain(self):
        with runner.isolated_filesystem():
            r = runner.invoke(app, ["invite", "missing.yaml", "--porcelain"])
        assert r.exit_code == 1
        assert "File not found" not in r.output

    def test_empty_file(self):
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                f.write("")
            r = runner.invoke(app, ["invite", "u.yaml"])
        assert r.exit_code == 0
        assert "No users" in r.output

    def test_empty_file_porcelain(self):
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                f.write("")
            r = runner.invoke(app, ["invite", "u.yaml", "--porcelain"])
        assert r.exit_code == 0

    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_with_team(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = [{"name": "t1", "title": "T1"}]
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["invite", "u.yaml", "--team", "T1"])
        assert r.exit_code == 0
        MC.return_value.invite_users.assert_called_once_with(["t1"], ["u1@x.com"])

    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_no_teams(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = []
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["invite", "u.yaml"])
        assert r.exit_code == 0

    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_porcelain_success(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = [{"name": "t1", "title": "T1"}]
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["invite", "u.yaml", "--porcelain"])
        assert r.exit_code == 0
        assert "invited:1" in r.output

    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_error(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = [{"name": "t1", "title": "T1"}]
        MC.return_value.invite_users.side_effect = RuntimeError("boom")
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["invite", "u.yaml"])
        assert r.exit_code == 1
        assert "Failed to invite" in r.output

    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_error_porcelain(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = [{"name": "t1", "title": "T1"}]
        MC.return_value.invite_users.side_effect = RuntimeError("boom")
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["invite", "u.yaml", "--porcelain"])
        assert r.exit_code == 1
        assert "Failed to invite" not in r.output


# ---------------------------------------------------------------------------
# _resolve_teams (exercised via import/invite)
# ---------------------------------------------------------------------------


class TestResolveTeams:
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_team_not_found(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = [{"name": "t1", "title": "T1"}]
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["push", "u.yaml", "--team", "NoSuch"])
        assert r.exit_code == 0

    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_no_teams_non_porcelain(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = []
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["invite", "u.yaml"])
        assert r.exit_code == 0
        assert "No teams" in r.output

    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_no_teams_porcelain(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = []
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["invite", "u.yaml", "--porcelain"])
        assert r.exit_code == 0
        assert "No teams" not in r.output

    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_single_team_auto(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = [{"name": "only", "title": "Only"}]
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["invite", "u.yaml"])
        assert r.exit_code == 0
        MC.return_value.invite_users.assert_called_once_with(["only"], ["u1@x.com"])

    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_multiple_teams_porcelain(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = [
            {"name": "t1", "title": "T1"},
            {"name": "t2", "title": "T2"},
        ]
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["invite", "u.yaml", "--porcelain"])
        assert r.exit_code == 0
        MC.return_value.invite_users.assert_called_once_with(["t1", "t2"], ["u1@x.com"])

    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_multiple_teams_interactive(self, _ctx, _auth, MC):
        MC.return_value.get_teams.return_value = [
            {"name": "t1", "title": "T1"},
            {"name": "t2", "title": "T2"},
        ]
        with runner.isolated_filesystem():
            with open("u.yaml", "w") as f:
                yaml.dump(SIMPLE_USERS, f)
            r = runner.invoke(app, ["invite", "u.yaml"], input="t1\n")
        assert r.exit_code == 0
        assert "Available teams" in r.output
        MC.return_value.invite_users.assert_called_once_with(["t1"], ["u1@x.com"])


class TestPullEdgeCases:
    """Cover remaining branches in export_users."""

    @patch(PATCH_CONVERT, return_value=EXPORT_USERS_LIST)
    @patch(PATCH_WORKSPACES)
    @patch(PATCH_MEMBERS)
    @patch(PATCH_FILTERED, return_value=[{"name": "t1", "title": "T1"}])
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_defaultdict_lambda(self, _ctx, _auth, _c, _ft, mock_members, _w, _cv):
        """Trigger the defaultdict factory lambda (256->exit branch)."""

        def populate_user_data(client, team_name, team_title, user_data, role_map):
            _ = user_data["new_user@example.com"]

        mock_members.side_effect = populate_user_data
        with runner.isolated_filesystem():
            r = runner.invoke(app, ["pull", "out.yaml"])
            assert r.exit_code == 0

    @patch(PATCH_FILTERED)
    @patch(PATCH_PRESET_CLIENT)
    @patch(PATCH_AUTH)
    @patch(PATCH_CONTEXT)
    def test_typer_exit_reraise(self, _ctx, _auth, _c, mock_ft):
        """Cover except typer.Exit: raise (line 327)."""
        import typer as _typer

        mock_ft.side_effect = _typer.Exit(1)
        r = runner.invoke(app, ["pull"])
        assert r.exit_code == 1
