"""Regression tests for SupContext.set_workspace_context hostname caching.

Covers the ticket "Switching workspaces does not update the workspace hostname":
when the workspace id changes without a hostname (e.g. `sup config set
workspace-id <ID>`), the previously cached hostname must NOT remain pointing at
the old workspace. It is cleared so the Superset client re-resolves it for the
new workspace on the next command.
"""

from unittest.mock import MagicMock, patch

import pytest

from sup.config.settings import SupContext, SupProjectState


@pytest.fixture
def temp_state(tmp_path, monkeypatch):
    """Point project state at a temp state.yml for real save/load round trips.

    SupProjectState/SupGlobalConfig are Pydantic BaseSettings, so they read
    field values from the environment (bare names like CURRENT_WORKSPACE_ID,
    and SUP_* for the global config). Clear the environment so these tests
    assert on file state alone and don't break when the host shell/CI exports
    those names. Mirrors the isolation pattern in tests/sup/commands/dbt_test.py.
    """
    with patch.dict("os.environ", {}, clear=True):
        state_file = tmp_path / "state.yml"
        # settings.py imports the helper by name, so patch it where it's used.
        monkeypatch.setattr(
            "sup.config.settings.get_project_state_file",
            lambda: state_file,
        )
        yield state_file


def test_switching_workspace_clears_stale_hostname(temp_state):
    # Workspace A: id + hostname cached together.
    ctx = SupContext()
    ctx.set_workspace_context(1, hostname="a.preset.io", persist=False)
    assert "a.preset.io" in temp_state.read_text()

    # Switch to workspace B via the config-set path: no hostname supplied.
    ctx2 = SupContext()
    ctx2.set_workspace_context(2, persist=False)

    reloaded = SupProjectState.load_from_file()
    assert reloaded.current_workspace_id == 2
    # The core of the ticket: the old hostname must be gone, not stale.
    assert reloaded.current_workspace_hostname is None
    assert "a.preset.io" not in temp_state.read_text()


def test_setting_hostname_persists_it(temp_state):
    ctx = SupContext()
    ctx.set_workspace_context(7, hostname="ws7.preset.io", persist=False)

    reloaded = SupProjectState.load_from_file()
    assert reloaded.current_workspace_id == 7
    assert reloaded.current_workspace_hostname == "ws7.preset.io"


def test_none_hostname_dropped_from_yaml(temp_state):
    # A None hostname should be omitted from state.yml entirely (clean file),
    # not written as an empty/null value.
    ctx = SupContext()
    ctx.set_workspace_context(3, persist=False)

    contents = temp_state.read_text()
    assert "current_workspace_id" in contents
    assert "current_workspace_hostname" not in contents


def test_global_persist_leaves_project_hostname_untouched(temp_state, monkeypatch):
    # `--global` (persist=True) writes only global config; it must not corrupt
    # an existing project-local hostname cache. get_workspace_id() prefers the
    # project id, so the cached project hostname stays consistent with it.
    global_file = temp_state.parent / "config.yml"
    monkeypatch.setattr(
        "sup.config.settings.get_global_config_file",
        lambda: global_file,
    )

    ctx = SupContext()
    ctx.set_workspace_context(1, hostname="a.preset.io", persist=False)

    ctx2 = SupContext()
    ctx2.set_workspace_context(99, persist=True)  # global only

    # The global write must actually have happened (guard against the test
    # passing purely because project id wins precedence below).
    assert global_file.exists()
    assert "99" in global_file.read_text()

    ctx3 = SupContext()
    # Project id wins precedence, so id and cached hostname stay paired even
    # though a different workspace id was written to the global config.
    assert ctx3.global_config.current_workspace_id == 99
    assert ctx3.get_workspace_id() == 1
    assert ctx3.get_workspace_hostname() == "a.preset.io"


def test_resolve_and_set_workspace_caches_hostname(temp_state):
    # The shared helper (used by config set / workspace use) resolves the
    # hostname from the Preset API and stores both id and hostname together.
    ctx = SupContext()
    fake_client = MagicMock()
    fake_client.get_workspace_hostname.return_value = "ws5.preset.io"

    with patch(
        "sup.clients.preset.SupPresetClient.from_context",
        return_value=fake_client,
    ):
        returned = ctx.resolve_and_set_workspace(5, persist=False)

    assert returned == "ws5.preset.io"
    fake_client.get_workspace_hostname.assert_called_once_with(5, silent=True)

    reloaded = SupProjectState.load_from_file()
    assert reloaded.current_workspace_id == 5
    assert reloaded.current_workspace_hostname == "ws5.preset.io"


def test_resolve_and_set_workspace_offline_fallback(temp_state):
    # If the Preset API is unreachable, the helper still switches the id and
    # clears the stale hostname (re-resolved lazily on next Superset use).
    seed = SupContext()
    seed.set_workspace_context(1, hostname="a.preset.io", persist=False)

    ctx = SupContext()
    with patch(
        "sup.clients.preset.SupPresetClient.from_context",
        side_effect=RuntimeError("network down"),
    ):
        returned = ctx.resolve_and_set_workspace(2, persist=False)

    assert returned is None
    reloaded = SupProjectState.load_from_file()
    assert reloaded.current_workspace_id == 2
    assert reloaded.current_workspace_hostname is None
