"""Tests for sup.commands.config module — 100% line coverage."""

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from sup.commands.config import app, format_config_help

runner = CliRunner()

# Since config.py uses `from sup.config.settings import SupContext` inside functions,
# we must patch at the *source* module: "sup.config.settings.SupContext".
# Similarly for test_auth_credentials: "sup.auth.preset.test_auth_credentials".
# Console is module-level so we patch "sup.commands.config.console".

CTX_PATH = "sup.config.settings.SupContext"
AUTH_PATH = "sup.auth.preset.test_auth_credentials"
CONSOLE_PATH = "sup.commands.config.console"
PATHS_GLOBAL = "sup.config.paths.get_global_config_file"
PATHS_PROJECT = "sup.config.paths.get_project_state_file"
RESET_CONSOLE = "sup.output.console.reset_console_cache"


# ---------------------------------------------------------------------------
# format_config_help
# ---------------------------------------------------------------------------

def test_format_config_help_returns_nonempty_string():
    result = format_config_help()
    assert isinstance(result, str)
    assert len(result) > 0
    assert "Configuration" in result


# ---------------------------------------------------------------------------
# show_config
# ---------------------------------------------------------------------------

def test_show_config_auth_configured():
    mock_ctx = MagicMock()
    mock_ctx.get_preset_credentials.return_value = ("tok", "sec")
    mock_ctx.get_workspace_id.return_value = 1
    mock_ctx.get_database_id.return_value = 2
    mock_ctx.get_target_workspace_id.return_value = 3
    mock_ctx.get_assets_folder.return_value = "./assets"
    mock_ctx.global_config.output_format.value = "table"
    mock_ctx.global_config.max_rows = 1000
    mock_ctx.global_config.show_query_time = True
    mock_ctx.global_config.monochrome = False

    with (
        patch(CONSOLE_PATH) as mock_console,
        patch(CTX_PATH, return_value=mock_ctx),
        patch(PATHS_GLOBAL, return_value="/g"),
        patch(PATHS_PROJECT, return_value="/p"),
    ):
        result = runner.invoke(app, ["show"])
        assert result.exit_code == 0
        # Extract Panel renderable content + plain prints
        all_text = []
        for call in mock_console.print.call_args_list:
            args = call[0]
            for arg in args:
                if hasattr(arg, "renderable"):
                    all_text.append(str(arg.renderable))
                else:
                    all_text.append(str(arg))
        combined = " ".join(all_text)
        assert "Configured" in combined
        assert "workspace-id" in combined
        assert "output-format" in combined


def test_show_config_auth_not_configured():
    mock_ctx = MagicMock()
    mock_ctx.get_preset_credentials.return_value = (None, None)
    mock_ctx.get_workspace_id.return_value = None
    mock_ctx.get_database_id.return_value = None
    mock_ctx.get_target_workspace_id.return_value = None
    mock_ctx.get_assets_folder.return_value = "./assets"
    mock_ctx.global_config.output_format.value = "table"
    mock_ctx.global_config.max_rows = 1000
    mock_ctx.global_config.show_query_time = True
    mock_ctx.global_config.monochrome = False

    with (
        patch(CONSOLE_PATH) as mock_console,
        patch(CTX_PATH, return_value=mock_ctx),
        patch(PATHS_GLOBAL, return_value="/g"),
        patch(PATHS_PROJECT, return_value="/p"),
    ):
        result = runner.invoke(app, ["show"])
        assert result.exit_code == 0
        prints = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "auth" in prints.lower()


def test_show_config_exception():
    with (
        patch(CONSOLE_PATH) as mock_console,
        patch(CTX_PATH, side_effect=RuntimeError("boom")),
    ):
        result = runner.invoke(app, ["show"])
        assert result.exit_code == 0
        prints = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "boom" in prints


# ---------------------------------------------------------------------------
# set_config — per-key branches
# ---------------------------------------------------------------------------

def _make_ctx():
    ctx = MagicMock()
    ctx.global_config = MagicMock()
    ctx.project_state = MagicMock()
    return ctx


def test_set_workspace_id():
    ctx = _make_ctx()
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "workspace-id", "42"])
        assert result.exit_code == 0
        ctx.set_workspace_context.assert_called_once_with(42, persist=False)


def test_set_workspace_id_global():
    ctx = _make_ctx()
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "workspace-id", "42", "--global"])
        assert result.exit_code == 0
        ctx.set_workspace_context.assert_called_once_with(42, persist=True)


def test_set_target_workspace_id():
    ctx = _make_ctx()
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "target-workspace-id", "99"])
        assert result.exit_code == 0
        ctx.set_target_workspace_id.assert_called_once_with(99, persist=False)


def test_set_database_id():
    ctx = _make_ctx()
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "database-id", "7"])
        assert result.exit_code == 0
        ctx.set_database_context.assert_called_once_with(7, persist=False)


def test_set_assets_folder_local():
    ctx = _make_ctx()
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "assets-folder", "./my-assets"])
        assert result.exit_code == 0
        assert ctx.project_state.assets_folder == "./my-assets"
        ctx.project_state.save_to_file.assert_called_once()


def test_set_assets_folder_global():
    ctx = _make_ctx()
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "assets-folder", "./g-assets", "--global"])
        assert result.exit_code == 0
        assert ctx.global_config.assets_folder == "./g-assets"
        ctx.global_config.save_to_file.assert_called_once()


def test_set_output_format():
    ctx = _make_ctx()
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "output-format", "json"])
        assert result.exit_code == 0
        ctx.global_config.save_to_file.assert_called_once()


def test_set_max_rows():
    ctx = _make_ctx()
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "max-rows", "500"])
        assert result.exit_code == 0
        assert ctx.global_config.max_rows == 500


def test_set_show_query_time_true():
    ctx = _make_ctx()
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "show-query-time", "true"])
        assert result.exit_code == 0
        assert ctx.global_config.show_query_time is True


def test_set_show_query_time_false():
    ctx = _make_ctx()
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "show-query-time", "no"])
        assert result.exit_code == 0
        assert ctx.global_config.show_query_time is False


def test_set_monochrome_on():
    ctx = _make_ctx()
    with (
        patch(CONSOLE_PATH),
        patch(CTX_PATH, return_value=ctx),
        patch(RESET_CONSOLE) as mock_reset,
    ):
        result = runner.invoke(app, ["set", "monochrome", "true"])
        assert result.exit_code == 0
        assert ctx.global_config.color_output is False
        mock_reset.assert_called_once()


def test_set_monochrome_off():
    ctx = _make_ctx()
    with (
        patch(CONSOLE_PATH),
        patch(CTX_PATH, return_value=ctx),
        patch(RESET_CONSOLE) as mock_reset,
    ):
        result = runner.invoke(app, ["set", "monochrome", "off"])
        assert result.exit_code == 0
        assert ctx.global_config.color_output is True
        mock_reset.assert_called_once()


def test_set_color_output_on():
    ctx = _make_ctx()
    with (
        patch(CONSOLE_PATH),
        patch(CTX_PATH, return_value=ctx),
        patch(RESET_CONSOLE) as mock_reset,
    ):
        result = runner.invoke(app, ["set", "color-output", "yes"])
        assert result.exit_code == 0
        assert ctx.global_config.color_output is True
        mock_reset.assert_called_once()


def test_set_color_output_off():
    ctx = _make_ctx()
    with (
        patch(CONSOLE_PATH),
        patch(CTX_PATH, return_value=ctx),
        patch(RESET_CONSOLE) as mock_reset,
    ):
        result = runner.invoke(app, ["set", "color-output", "no"])
        assert result.exit_code == 0
        assert ctx.global_config.color_output is False
        mock_reset.assert_called_once()


def test_set_preset_api_token():
    ctx = _make_ctx()
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "preset-api-token", "mytoken"])
        assert result.exit_code == 0
        assert ctx.global_config.preset_api_token == "mytoken"


def test_set_preset_api_secret():
    ctx = _make_ctx()
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "preset-api-secret", "mysecret"])
        assert result.exit_code == 0
        assert ctx.global_config.preset_api_secret == "mysecret"


def test_set_unknown_key():
    ctx = _make_ctx()
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "bogus-key", "val"])
        assert result.exit_code == 1


def test_set_value_error():
    """workspace-id with non-int triggers int() ValueError."""
    ctx = _make_ctx()
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "workspace-id", "notanint"])
        assert result.exit_code == 1


def test_set_generic_exception():
    ctx = _make_ctx()
    ctx.set_workspace_context.side_effect = RuntimeError("fail")
    with patch(CONSOLE_PATH), patch(CTX_PATH, return_value=ctx):
        result = runner.invoke(app, ["set", "workspace-id", "42"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# auth_setup
# ---------------------------------------------------------------------------

def test_auth_existing_valid_decline_update():
    ctx = _make_ctx()
    ctx.get_preset_credentials.return_value = ("tok", "sec")

    with (
        patch(CONSOLE_PATH),
        patch(CTX_PATH, return_value=ctx),
        patch(AUTH_PATH, return_value=True),
        patch("builtins.input", return_value="n"),
    ):
        result = runner.invoke(app, ["auth"])
        assert result.exit_code == 0


def test_auth_existing_valid_wants_update_then_valid_store_global():
    ctx = _make_ctx()
    ctx.get_preset_credentials.return_value = ("tok", "sec")

    inputs = iter(["y", "newtoken", "newsecret", "1"])

    with (
        patch(CONSOLE_PATH),
        patch(CTX_PATH, return_value=ctx),
        patch(AUTH_PATH, return_value=True),
        patch("builtins.input", side_effect=inputs),
    ):
        result = runner.invoke(app, ["auth"])
        assert result.exit_code == 0
        assert ctx.global_config.preset_api_token == "newtoken"
        assert ctx.global_config.preset_api_secret == "newsecret"
        ctx.global_config.save_to_file.assert_called_once()


def test_auth_existing_invalid_new_valid_env_vars():
    ctx = _make_ctx()
    ctx.get_preset_credentials.return_value = ("tok", "sec")

    inputs = iter(["newtoken", "newsecret", "2"])

    with (
        patch(CONSOLE_PATH),
        patch(CTX_PATH, return_value=ctx),
        patch(AUTH_PATH, side_effect=[False, True]),
        patch("builtins.input", side_effect=inputs),
    ):
        result = runner.invoke(app, ["auth"])
        assert result.exit_code == 0


def test_auth_no_existing_new_valid_skip_storage():
    ctx = _make_ctx()
    ctx.get_preset_credentials.return_value = (None, None)

    inputs = iter(["newtoken", "newsecret", "3"])

    with (
        patch(CONSOLE_PATH),
        patch(CTX_PATH, return_value=ctx),
        patch(AUTH_PATH, return_value=True),
        patch("builtins.input", side_effect=inputs),
    ):
        result = runner.invoke(app, ["auth"])
        assert result.exit_code == 0


def test_auth_new_creds_invalid():
    ctx = _make_ctx()
    ctx.get_preset_credentials.return_value = (None, None)

    inputs = iter(["newtoken", "newsecret"])

    with (
        patch(CONSOLE_PATH) as mock_console,
        patch(CTX_PATH, return_value=ctx),
        patch(AUTH_PATH, return_value=False),
        patch("builtins.input", side_effect=inputs),
    ):
        result = runner.invoke(app, ["auth"])
        assert result.exit_code == 0
        prints = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "Invalid" in prints


def test_auth_empty_token():
    ctx = _make_ctx()
    ctx.get_preset_credentials.return_value = (None, None)

    with (
        patch(CONSOLE_PATH) as mock_console,
        patch(CTX_PATH, return_value=ctx),
        patch("builtins.input", return_value=""),
    ):
        result = runner.invoke(app, ["auth"])
        assert result.exit_code == 0
        prints = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "required" in prints.lower()


def test_auth_empty_secret():
    ctx = _make_ctx()
    ctx.get_preset_credentials.return_value = (None, None)

    inputs = iter(["sometoken", ""])

    with (
        patch(CONSOLE_PATH) as mock_console,
        patch(CTX_PATH, return_value=ctx),
        patch("builtins.input", side_effect=inputs),
    ):
        result = runner.invoke(app, ["auth"])
        assert result.exit_code == 0
        prints = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "required" in prints.lower()


# ---------------------------------------------------------------------------
# init_project
# ---------------------------------------------------------------------------

def test_init_project():
    with patch(CONSOLE_PATH) as mock_console:
        result = runner.invoke(app, ["init"])
        assert result.exit_code == 0
        assert mock_console.print.call_count >= 2
        prints = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "Initializing" in prints
        assert "initialized" in prints.lower() or "Project" in prints


# ---------------------------------------------------------------------------
# show_env_vars
# ---------------------------------------------------------------------------

def test_show_env_vars():
    with (
        patch(CONSOLE_PATH) as mock_console,
        patch(PATHS_GLOBAL, return_value="/g"),
        patch(PATHS_PROJECT, return_value="/p"),
    ):
        result = runner.invoke(app, ["env"])
        assert result.exit_code == 0
        assert mock_console.print.call_count > 0
        prints = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "SUP_PRESET_API_TOKEN" in prints
        assert "SUP_WORKSPACE_ID" in prints
        assert "SUP_OUTPUT_FORMAT" in prints
