"""Tests for sup.commands.workspace module — 100% line coverage."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from sup.commands.workspace import (
    app,
    display_workspace_details,
    parse_workspace_identifier,
    safe_parse_workspace,
)

runner = CliRunner()

# Imports inside workspace.py functions come from their source modules.
CTX_PATH = "sup.config.settings.SupContext"
CLIENT_PATH = "sup.clients.preset.SupPresetClient"
SPINNER_PATH = "sup.output.spinners.data_spinner"
PORCELAIN_PATH = "sup.output.formatters.display_porcelain_list"
CONSOLE_PATH = "sup.commands.workspace.console"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ctx(**overrides):
    ctx = MagicMock()
    ctx.get_workspace_id.return_value = overrides.get("workspace_id", 123)
    ctx.get_target_workspace_id.return_value = overrides.get("target_workspace_id", None)
    ctx.get_database_id.return_value = overrides.get("database_id", None)
    return ctx


@contextmanager
def _fake_spinner(*a, **kw):
    """Replace data_spinner with a no-op context manager."""
    sp = MagicMock()
    yield sp


# ---------------------------------------------------------------------------
# parse_workspace_identifier
# ---------------------------------------------------------------------------


class TestParseWorkspaceIdentifier:
    def test_integer_string(self):
        assert parse_workspace_identifier("123") == 123

    def test_full_url(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [
            {"hostname": "myws.us1a.app.preset.io", "id": 42},
        ]
        assert parse_workspace_identifier("https://myws.us1a.app.preset.io/", client) == 42

    def test_hostname_without_scheme(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [
            {"hostname": "myws.us1a.app.preset.io", "id": 7},
        ]
        assert parse_workspace_identifier("myws.us1a.app.preset.io", client) == 7

    def test_no_hostname_parsed(self):
        # urlparse("https://") gives hostname=None, netloc=""
        with pytest.raises(ValueError, match="Could not parse"):
            parse_workspace_identifier("", None)

    def test_no_client_for_hostname(self):
        with pytest.raises(ValueError, match="without active client"):
            parse_workspace_identifier("myws.preset.io", None)

    def test_hostname_not_found(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [
            {"hostname": "other.preset.io", "id": 1},
        ]
        with pytest.raises(ValueError, match="No workspace found"):
            parse_workspace_identifier("myws.preset.io", client)


# ---------------------------------------------------------------------------
# safe_parse_workspace
# ---------------------------------------------------------------------------


class TestSafeParseWorkspace:
    def test_success(self):
        assert safe_parse_workspace("123", MagicMock()) == 123

    def test_value_error_porcelain_false(self):
        with patch(CONSOLE_PATH):
            with pytest.raises((SystemExit, typer.Exit)):
                safe_parse_workspace("not-a-host", None, porcelain=False)

    def test_value_error_porcelain_true(self):
        with patch(CONSOLE_PATH):
            with pytest.raises((SystemExit, typer.Exit)):
                safe_parse_workspace("not-a-host", None, porcelain=True)


# ---------------------------------------------------------------------------
# list_workspaces
# ---------------------------------------------------------------------------


class TestListWorkspaces:
    def test_table_output(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [{"id": 1, "title": "WS1"}]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
            patch(PORCELAIN_PATH),
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
            client.display_workspaces_table.assert_called_once()

    def test_json_output(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [{"id": 1}]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["list", "--json"])
            assert result.exit_code == 0

    def test_yaml_output(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [{"id": 1}]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["list", "--yaml"])
            assert result.exit_code == 0

    def test_porcelain_output(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [{"id": 1}]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
            patch(PORCELAIN_PATH) as mock_porcelain,
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["list", "--porcelain"])
            assert result.exit_code == 0
            mock_porcelain.assert_called_once()

    def test_team_filter(self):
        client = MagicMock()
        client.get_workspaces_for_team.return_value = [{"id": 1}]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["list", "--team", "myteam"])
            assert result.exit_code == 0
            client.get_workspaces_for_team.assert_called_once_with("myteam")

    def test_limit(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [{"id": i} for i in range(10)]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["list", "--limit", "3"])
            assert result.exit_code == 0
            call_args = client.display_workspaces_table.call_args[0][0]
            assert len(call_args) == 3

    def test_error_non_porcelain(self):
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH) as mock_console,
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.side_effect = RuntimeError("boom")
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 1
            prints = " ".join(str(c) for c in mock_console.print.call_args_list)
            assert "boom" in prints

    def test_error_porcelain(self):
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.side_effect = RuntimeError("boom")
            result = runner.invoke(app, ["list", "--porcelain"])
            assert result.exit_code == 1


# ---------------------------------------------------------------------------
# use_workspace
# ---------------------------------------------------------------------------


class TestUseWorkspace:
    def test_workspace_found_no_persist(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [
            {"id": 42, "hostname": "ws.preset.io"},
        ]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["use", "42"])
            assert result.exit_code == 0
            ctx.set_workspace_context.assert_called_once_with(
                42, hostname="ws.preset.io", persist=False
            )

    def test_workspace_found_persist(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [
            {"id": 42, "hostname": "ws.preset.io"},
        ]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["use", "42", "--persist"])
            assert result.exit_code == 0
            ctx.set_workspace_context.assert_called_once_with(
                42, hostname="ws.preset.io", persist=True
            )

    def test_workspace_not_found(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [
            {"id": 99, "hostname": "other.preset.io"},
        ]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["use", "42"])
            assert result.exit_code == 1

    def test_error(self):
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
        ):
            mock_cls.from_context.side_effect = RuntimeError("fail")
            result = runner.invoke(app, ["use", "42"])
            assert result.exit_code == 1


# ---------------------------------------------------------------------------
# workspace_info
# ---------------------------------------------------------------------------


class TestWorkspaceInfo:
    def _ws(self, **kw):
        ws = {"id": 123, "title": "TestWS", "status": "READY", "hostname": "ws.preset.io"}
        ws.update(kw)
        return ws

    def test_with_workspace_arg_table(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [self._ws()]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
            patch("sup.commands.workspace.display_workspace_details") as mock_display,
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["info", "123"])
            assert result.exit_code == 0
            mock_display.assert_called_once()

    def test_without_workspace_arg_from_context(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [self._ws()]
        ctx = _make_ctx(workspace_id=123)
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
            patch("sup.commands.workspace.display_workspace_details") as mock_display,
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["info"])
            assert result.exit_code == 0
            mock_display.assert_called_once()

    def test_no_workspace_configured(self):
        ctx = _make_ctx(workspace_id=None)
        client = MagicMock()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["info"])
            assert result.exit_code == 1

    def test_no_workspace_configured_porcelain(self):
        ctx = _make_ctx(workspace_id=None)
        client = MagicMock()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["info", "--porcelain"])
            assert result.exit_code == 1

    def test_workspace_not_found(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [{"id": 999, "title": "Other"}]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["info", "123"])
            assert result.exit_code == 1

    def test_workspace_not_found_porcelain(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [{"id": 999, "title": "Other"}]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["info", "123", "--porcelain"])
            assert result.exit_code == 1

    def test_porcelain_output(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [self._ws()]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["info", "123", "--porcelain"])
            assert result.exit_code == 0
            assert "123" in result.output

    def test_json_output(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [self._ws()]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["info", "123", "--json"])
            assert result.exit_code == 0

    def test_yaml_output(self):
        client = MagicMock()
        client.get_all_workspaces.return_value = [self._ws()]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["info", "123", "--yaml"])
            assert result.exit_code == 0

    def test_generic_exception(self):
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.side_effect = RuntimeError("fail")
            result = runner.invoke(app, ["info", "123"])
            assert result.exit_code == 1

    def test_generic_exception_porcelain(self):
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_fake_spinner),
        ):
            mock_cls.from_context.side_effect = RuntimeError("fail")
            result = runner.invoke(app, ["info", "123", "--porcelain"])
            assert result.exit_code == 1


# ---------------------------------------------------------------------------
# display_workspace_details
# ---------------------------------------------------------------------------


class TestDisplayWorkspaceDetails:
    @staticmethod
    def _get_panel_content(mock_console):
        """Extract the Panel content string from console.print calls."""
        for call in mock_console.print.call_args_list:
            args = call[0]
            if args and hasattr(args[0], "renderable"):
                # Rich Panel object
                return str(args[0].renderable)
        return ""

    def test_basic(self):
        ws = {
            "id": 1,
            "title": "WS",
            "hostname": "h.preset.io",
            "status": "READY",
            "team_name": "T",
            "region": "us-east-1",
        }
        with patch(CONSOLE_PATH) as mock_console:
            display_workspace_details(ws)
            content = self._get_panel_content(mock_console)
            assert "ID: 1" in content
            assert "Title: WS" in content
            assert "Team: T" in content
            assert "Status: READY" in content
            assert "Region: us-east-1" in content
            assert "https://h.preset.io/" in content

    def test_with_description(self):
        ws = {
            "id": 1,
            "title": "WS",
            "hostname": "h.preset.io",
            "status": "READY",
            "team_name": "T",
            "region": "us-east-1",
            "descr": "A workspace",
        }
        with patch(CONSOLE_PATH) as mock_console:
            display_workspace_details(ws)
            content = self._get_panel_content(mock_console)
            assert "Description: A workspace" in content

    def test_with_features(self):
        ws = {
            "id": 1,
            "title": "WS",
            "hostname": "h.preset.io",
            "status": "READY",
            "team_name": "T",
            "region": "us-east-1",
            "ai_assist_activated": True,
            "allow_public_dashboards": True,
            "enable_iframe_embedding": True,
        }
        with patch(CONSOLE_PATH) as mock_console:
            display_workspace_details(ws)
            content = self._get_panel_content(mock_console)
            assert "AI Assist" in content
            assert "Public Dashboards" in content
            assert "iFrame Embedding" in content

    def test_no_hostname(self):
        ws = {
            "id": 1,
            "title": "WS",
            "hostname": "",
            "status": "READY",
            "team_name": "T",
            "region": "us-east-1",
        }
        with patch(CONSOLE_PATH) as mock_console:
            display_workspace_details(ws)
            content = self._get_panel_content(mock_console)
            assert "URL: N/A" in content

    def test_no_features(self):
        ws = {
            "id": 1,
            "title": "WS",
            "hostname": "h.preset.io",
            "status": "READY",
            "team_name": "T",
            "region": "us-east-1",
            "ai_assist_activated": False,
            "allow_public_dashboards": False,
            "enable_iframe_embedding": False,
        }
        with patch(CONSOLE_PATH) as mock_console:
            display_workspace_details(ws)
            content = self._get_panel_content(mock_console)
            assert "Features" not in content


# ---------------------------------------------------------------------------
# set_import_target
# ---------------------------------------------------------------------------


class TestSetImportTarget:
    def test_persist(self):
        client = MagicMock()
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["set-target", "456", "--persist"])
            assert result.exit_code == 0
            ctx.set_target_workspace_id.assert_called_once_with(456, persist=True)

    def test_no_persist(self):
        client = MagicMock()
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["set-target", "456"])
            assert result.exit_code == 0
            ctx.set_target_workspace_id.assert_called_once_with(456, persist=False)

    def test_error(self):
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
        ):
            mock_cls.from_context.side_effect = RuntimeError("fail")
            result = runner.invoke(app, ["set-target", "456"])
            assert result.exit_code == 1


# ---------------------------------------------------------------------------
# show_workspace_context
# ---------------------------------------------------------------------------


class TestShowWorkspaceContext:
    @staticmethod
    def _prints(mock_console):
        return " ".join(str(c) for c in mock_console.print.call_args_list)

    def test_source_configured_no_target(self):
        ctx = _make_ctx(workspace_id=123, target_workspace_id=None)
        with (
            patch(CONSOLE_PATH) as mock_console,
            patch(CTX_PATH, return_value=ctx),
        ):
            result = runner.invoke(app, ["show"])
            assert result.exit_code == 0
            prints = self._prints(mock_console)
            assert "123" in prints
            assert "Source" in prints
            assert "Same as source" in prints

    def test_source_not_configured(self):
        ctx = _make_ctx(workspace_id=None, target_workspace_id=None)
        with (
            patch(CONSOLE_PATH) as mock_console,
            patch(CTX_PATH, return_value=ctx),
        ):
            result = runner.invoke(app, ["show"])
            assert result.exit_code == 0
            prints = self._prints(mock_console)
            assert "Not configured" in prints

    def test_target_different_from_source(self):
        ctx = _make_ctx(workspace_id=123, target_workspace_id=456)
        with (
            patch(CONSOLE_PATH) as mock_console,
            patch(CTX_PATH, return_value=ctx),
        ):
            result = runner.invoke(app, ["show"])
            assert result.exit_code == 0
            prints = self._prints(mock_console)
            assert "123" in prints
            assert "456" in prints
            assert "cross" in prints

    def test_target_same_as_source(self):
        ctx = _make_ctx(workspace_id=123, target_workspace_id=123)
        with (
            patch(CONSOLE_PATH) as mock_console,
            patch(CTX_PATH, return_value=ctx),
        ):
            result = runner.invoke(app, ["show"])
            assert result.exit_code == 0
            prints = self._prints(mock_console)
            assert "123" in prints
            assert "same as source" in prints

    def test_error(self):
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, side_effect=RuntimeError("fail")),
        ):
            result = runner.invoke(app, ["show"])
            assert result.exit_code == 1

    def test_spinner_yields_none(self):
        """Cover the `if sp:` false branch when spinner is silent."""

        @contextmanager
        def _silent_spinner(*a, **kw):
            yield None

        client = MagicMock()
        client.get_all_workspaces.return_value = [{"id": 1}]
        ctx = _make_ctx()
        with (
            patch(CONSOLE_PATH),
            patch(CTX_PATH, return_value=ctx),
            patch(CLIENT_PATH) as mock_cls,
            patch(SPINNER_PATH, side_effect=_silent_spinner),
        ):
            mock_cls.from_context.return_value = client
            result = runner.invoke(app, ["list"])
            assert result.exit_code == 0
