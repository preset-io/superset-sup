"""
Tests for sup theme commands: list, pull, push.
"""

import json
from io import BytesIO
from unittest.mock import MagicMock, patch
from zipfile import ZipFile

import yaml
from typer.testing import CliRunner

from sup.commands.theme import app

runner = CliRunner()

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

THEME_1 = {
    "id": 1,
    "theme_name": "Dark Theme",
    "is_system_default": False,
    "is_system_dark": True,
    "changed_on_delta_humanized": "2 days ago",
    "json_data": '{"token": {"colorPrimary": "#000"}}',
}

THEME_2 = {
    "id": 2,
    "theme_name": "Light Theme",
    "is_system_default": True,
    "is_system_dark": False,
    "changed_on_delta_humanized": "1 hour ago",
    "json_data": '{"token": {"colorPrimary": "#fff"}}',
}


def _make_theme_zip(themes: list) -> BytesIO:
    """Build a ZIP that matches Superset's theme export format."""
    buf = BytesIO()
    with ZipFile(buf, "w") as zf:
        for theme in themes:
            name = theme["theme_name"].replace(" ", "_")
            content = yaml.safe_dump(
                {
                    "theme_name": theme["theme_name"],
                    "json_data": theme["json_data"],
                    "version": "1.0.0",
                }
            )
            zf.writestr(f"bundle/themes/{name}.yaml", content)
        zf.writestr(
            "bundle/metadata.yaml",
            yaml.safe_dump({"version": "1.0.0", "type": "Theme"}),
        )
    buf.seek(0)
    return buf


# ---------------------------------------------------------------------------
# sup theme list
# ---------------------------------------------------------------------------


def test_list_themes(tmp_path):
    """list command displays a table of themes."""
    mock_client = MagicMock()
    mock_client.get_themes.return_value = [THEME_1, THEME_2]
    mock_client.workspace_url = "https://example.preset.io/"

    with patch("sup.config.settings.SupContext"):
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            MockClient.from_context.return_value = mock_client
            result = runner.invoke(app, ["list"])

    assert result.exit_code == 0
    assert "Dark Theme" in result.output
    assert "Light Theme" in result.output


def test_list_themes_json(tmp_path):
    """list --json returns JSON output."""
    mock_client = MagicMock()
    mock_client.get_themes.return_value = [THEME_1]
    mock_client.workspace_url = "https://example.preset.io/"

    with patch("sup.config.settings.SupContext"):
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            MockClient.from_context.return_value = mock_client
            result = runner.invoke(app, ["list", "--json"])

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert isinstance(parsed, list)
    assert parsed[0]["theme_name"] == "Dark Theme"


def test_list_themes_porcelain(tmp_path):
    """list --porcelain returns machine-readable output."""
    mock_client = MagicMock()
    mock_client.get_themes.return_value = [THEME_1, THEME_2]
    mock_client.workspace_url = "https://example.preset.io/"

    with patch("sup.config.settings.SupContext"):
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            MockClient.from_context.return_value = mock_client
            result = runner.invoke(app, ["list", "--porcelain"])

    assert result.exit_code == 0


def test_list_themes_filter_by_id():
    """list --id filters to a single theme."""
    mock_client = MagicMock()
    mock_client.get_themes.return_value = [THEME_1, THEME_2]
    mock_client.workspace_url = "https://example.preset.io/"

    with patch("sup.config.settings.SupContext"):
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            MockClient.from_context.return_value = mock_client
            result = runner.invoke(app, ["list", "--id=1", "--json"])

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert len(parsed) == 1
    assert parsed[0]["id"] == 1


def test_list_themes_filter_by_ids():
    """list --ids filters to specified IDs."""
    mock_client = MagicMock()
    mock_client.get_themes.return_value = [THEME_1, THEME_2]
    mock_client.workspace_url = "https://example.preset.io/"

    with patch("sup.config.settings.SupContext"):
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            MockClient.from_context.return_value = mock_client
            result = runner.invoke(app, ["list", "--ids=1,2", "--json"])

    assert result.exit_code == 0
    parsed = json.loads(result.output)
    assert len(parsed) == 2


def test_list_themes_error_exits_nonzero():
    """list exits with code 1 on error."""
    with patch("sup.config.settings.SupContext"):
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            MockClient.from_context.side_effect = RuntimeError("auth failed")
            result = runner.invoke(app, ["list"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# sup theme pull
# ---------------------------------------------------------------------------


def test_pull_themes_creates_yaml_files(tmp_path):
    """pull writes theme YAML files to the output directory."""
    mock_client = MagicMock()
    mock_client.get_themes.return_value = [THEME_1, THEME_2]
    mock_client.client.export_zip.return_value = _make_theme_zip([THEME_1, THEME_2])

    with patch("sup.config.settings.SupContext") as MockCtx:
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            ctx_instance = MockCtx.return_value
            ctx_instance.get_assets_folder.return_value = str(tmp_path)
            MockClient.from_context.return_value = mock_client

            result = runner.invoke(app, ["pull", "--output", str(tmp_path), "--overwrite"])

    assert result.exit_code == 0
    yaml_files = list(tmp_path.rglob("*.yaml"))
    # Should have theme files (and optionally metadata)
    assert len(yaml_files) >= 1


def test_pull_themes_filter_by_id(tmp_path):
    """pull --id only exports the specified theme."""
    mock_client = MagicMock()
    mock_client.get_themes.return_value = [THEME_1, THEME_2]
    mock_client.client.export_zip.return_value = _make_theme_zip([THEME_1])

    with patch("sup.config.settings.SupContext") as MockCtx:
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            ctx_instance = MockCtx.return_value
            ctx_instance.get_assets_folder.return_value = str(tmp_path)
            MockClient.from_context.return_value = mock_client

            result = runner.invoke(
                app, ["pull", "--output", str(tmp_path), "--id=1", "--overwrite"]
            )

    assert result.exit_code == 0
    # export_zip should have been called with only ID 1
    mock_client.client.export_zip.assert_called_once_with("theme", [1])


def test_pull_themes_no_match(tmp_path):
    """pull with a filter that matches nothing warns and exits cleanly."""
    mock_client = MagicMock()
    mock_client.get_themes.return_value = []

    with patch("sup.config.settings.SupContext") as MockCtx:
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            ctx_instance = MockCtx.return_value
            ctx_instance.get_assets_folder.return_value = str(tmp_path)
            MockClient.from_context.return_value = mock_client

            result = runner.invoke(app, ["pull", "--output", str(tmp_path), "--id=999"])

    assert result.exit_code == 0
    mock_client.client.export_zip.assert_not_called()


def test_pull_themes_skips_existing_without_overwrite(tmp_path):
    """pull skips existing files when --overwrite is not set."""
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()
    existing = themes_dir / "Dark_Theme.yaml"
    existing.write_text("existing content")

    mock_client = MagicMock()
    mock_client.get_themes.return_value = [THEME_1]
    mock_client.client.export_zip.return_value = _make_theme_zip([THEME_1])

    with patch("sup.config.settings.SupContext") as MockCtx:
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            ctx_instance = MockCtx.return_value
            ctx_instance.get_assets_folder.return_value = str(tmp_path)
            MockClient.from_context.return_value = mock_client

            result = runner.invoke(app, ["pull", "--output", str(tmp_path)])

    assert result.exit_code == 0
    # Original file should be unchanged
    assert existing.read_text() == "existing content"


def test_pull_themes_error_exits_nonzero(tmp_path):
    """pull exits with code 1 on error."""
    with patch("sup.config.settings.SupContext") as MockCtx:
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            ctx_instance = MockCtx.return_value
            ctx_instance.get_assets_folder.return_value = str(tmp_path)
            MockClient.from_context.side_effect = RuntimeError("connection error")

            result = runner.invoke(app, ["pull", "--output", str(tmp_path)])

    assert result.exit_code == 1


def test_pull_themes_path_traversal_blocked(tmp_path):
    """pull rejects ZIP entries that escape the output directory."""
    buf = BytesIO()
    with ZipFile(buf, "w") as zf:
        zf.writestr("bundle/../../../etc/passwd", "evil")
    buf.seek(0)

    mock_client = MagicMock()
    mock_client.get_themes.return_value = [THEME_1]
    mock_client.client.export_zip.return_value = buf

    with patch("sup.config.settings.SupContext") as MockCtx:
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            ctx_instance = MockCtx.return_value
            ctx_instance.get_assets_folder.return_value = str(tmp_path)
            MockClient.from_context.return_value = mock_client

            result = runner.invoke(app, ["pull", "--output", str(tmp_path), "--overwrite"])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# sup theme push
# ---------------------------------------------------------------------------


def test_push_themes_from_yaml_file(tmp_path):
    """push accepts a single YAML file."""
    theme_file = tmp_path / "my_theme.yaml"
    theme_file.write_text(
        yaml.safe_dump(
            {
                "theme_name": "My Theme",
                "json_data": '{"token": {}}',
                "version": "1.0.0",
            }
        )
    )

    mock_client = MagicMock()
    mock_client.client.import_zip.return_value = True

    with patch("sup.config.settings.SupContext"):
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            MockClient.from_context.return_value = mock_client
            result = runner.invoke(app, ["push", str(theme_file)])

    assert result.exit_code == 0
    mock_client.client.import_zip.assert_called_once()
    call_args = mock_client.client.import_zip.call_args
    assert call_args[0][0] == "theme"


def test_push_themes_from_directory(tmp_path):
    """push discovers YAML files under themes/ subdirectory."""
    themes_dir = tmp_path / "themes"
    themes_dir.mkdir()
    (themes_dir / "theme_a.yaml").write_text(
        yaml.safe_dump({"theme_name": "A", "json_data": "{}", "version": "1.0.0"})
    )
    (themes_dir / "theme_b.yaml").write_text(
        yaml.safe_dump({"theme_name": "B", "json_data": "{}", "version": "1.0.0"})
    )

    mock_client = MagicMock()
    mock_client.client.import_zip.return_value = True

    with patch("sup.config.settings.SupContext"):
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            MockClient.from_context.return_value = mock_client
            result = runner.invoke(app, ["push", str(tmp_path)])

    assert result.exit_code == 0
    mock_client.client.import_zip.assert_called_once()
    # Should send a ZIP with both files
    call_args = mock_client.client.import_zip.call_args
    buf = call_args[0][1]
    buf.seek(0)
    with ZipFile(buf) as zf:
        names = zf.namelist()
    theme_files = [n for n in names if "themes/" in n and n.endswith(".yaml")]
    assert len(theme_files) == 2


def test_push_themes_with_overwrite(tmp_path):
    """push --overwrite passes overwrite=True to import_zip."""
    theme_file = tmp_path / "theme.yaml"
    theme_file.write_text(yaml.safe_dump({"theme_name": "T", "json_data": "{}"}))

    mock_client = MagicMock()
    mock_client.client.import_zip.return_value = True

    with patch("sup.config.settings.SupContext"):
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            MockClient.from_context.return_value = mock_client
            result = runner.invoke(app, ["push", str(theme_file), "--overwrite"])

    assert result.exit_code == 0
    call_kwargs = mock_client.client.import_zip.call_args[1]
    assert call_kwargs.get("overwrite") is True


def test_push_themes_path_not_found(tmp_path):
    """push exits with code 1 when path does not exist."""
    with patch("sup.config.settings.SupContext"):
        with patch("sup.clients.superset.SupSupersetClient"):
            result = runner.invoke(app, ["push", str(tmp_path / "nonexistent.yaml")])

    assert result.exit_code == 1


def test_push_themes_non_yaml_file(tmp_path):
    """push exits with code 1 when a non-YAML file is given."""
    bad_file = tmp_path / "theme.json"
    bad_file.write_text("{}")

    with patch("sup.config.settings.SupContext"):
        with patch("sup.clients.superset.SupSupersetClient"):
            result = runner.invoke(app, ["push", str(bad_file)])

    assert result.exit_code == 1


def test_push_themes_empty_directory(tmp_path):
    """push exits cleanly with a warning when no YAML files are found."""
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()

    mock_client = MagicMock()

    with patch("sup.config.settings.SupContext"):
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            MockClient.from_context.return_value = mock_client
            result = runner.invoke(app, ["push", str(empty_dir)])

    assert result.exit_code == 0
    mock_client.client.import_zip.assert_not_called()


def test_push_themes_error_exits_nonzero(tmp_path):
    """push exits with code 1 when import_zip raises an exception."""
    theme_file = tmp_path / "theme.yaml"
    theme_file.write_text(yaml.safe_dump({"theme_name": "T", "json_data": "{}"}))

    mock_client = MagicMock()
    mock_client.client.import_zip.side_effect = RuntimeError("server error")

    with patch("sup.config.settings.SupContext"):
        with patch("sup.clients.superset.SupSupersetClient") as MockClient:
            MockClient.from_context.return_value = mock_client
            result = runner.invoke(app, ["push", str(theme_file)])

    assert result.exit_code == 1


# ---------------------------------------------------------------------------
# sync config - themes in AssetTypes
# ---------------------------------------------------------------------------


def test_asset_types_includes_themes():
    """AssetTypes accepts a themes field."""
    from sup.config.sync import AssetSelection, AssetTypes

    assets = AssetTypes(
        themes=AssetSelection(selection="all"),
    )
    assert assets.themes is not None
    assert assets.themes.selection == "all"


def test_asset_types_themes_ids():
    """AssetTypes themes can use 'ids' selection."""
    from sup.config.sync import AssetSelection, AssetTypes

    assets = AssetTypes(
        themes=AssetSelection(selection="ids", ids=[1, 2, 3]),
    )
    assert assets.themes.ids == [1, 2, 3]


def test_asset_types_themes_default_none():
    """AssetTypes themes defaults to None (no themes synced by default)."""
    from sup.config.sync import AssetTypes

    assets = AssetTypes()
    assert assets.themes is None


# ---------------------------------------------------------------------------
# shared utilities
# ---------------------------------------------------------------------------


def test_remove_root_strips_first_component():
    """remove_root strips the first path component."""
    from sup.lib import remove_root

    assert remove_root("bundle/themes/dark.yaml") == "themes/dark.yaml"
    assert remove_root("single") == "single"


def test_safe_extract_path_allows_valid_path(tmp_path):
    """safe_extract_path allows paths within base."""
    from sup.lib import safe_extract_path

    result = safe_extract_path(tmp_path, "themes/dark.yaml")
    assert result == (tmp_path / "themes" / "dark.yaml").resolve()


def test_safe_extract_path_blocks_traversal(tmp_path):
    """safe_extract_path rejects paths that escape base."""
    import pytest

    from sup.lib import safe_extract_path

    with pytest.raises(ValueError, match="Path traversal detected"):
        safe_extract_path(tmp_path, "../../etc/passwd")
