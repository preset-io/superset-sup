"""Tests for sup.commands.dataset module - 100% line coverage."""

import io
import json
import zipfile
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from sup.commands.dataset import (
    app,
    display_dataset_details,
    display_datasets_table,
)

runner = CliRunner()

PATCH_CTX = "sup.config.settings.SupContext"
PATCH_CLIENT = "sup.clients.superset.SupSupersetClient"
PATCH_SPINNER = "sup.output.spinners.data_spinner"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_spinner_mock():
    cm = MagicMock()
    sp = MagicMock()
    cm.__enter__ = MagicMock(return_value=sp)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, sp


def _make_spinner_none():
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=None)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _make_zip(file_map: dict) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in file_map.items():
            zf.writestr(name, content)
    buf.seek(0)
    return buf


SAMPLE_DATASETS = [
    {
        "id": 1,
        "table_name": "sales",
        "database": {"database_name": "main_db"},
        "schema": "public",
        "kind": "physical",
        "columns": [{"column_name": "id", "type": "INT", "description": ""}],
        "owners": [{"id": 10}],
    },
    {
        "id": 2,
        "table_name": "users",
        "database": {"database_name": "main_db"},
        "schema": "public",
        "kind": "physical",
        "columns": [],
        "owners": [{"id": 20}],
    },
]


# ---------------------------------------------------------------------------
# list_datasets
# ---------------------------------------------------------------------------


class TestListDatasets:
    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_porcelain(self, mock_ctx_cls, mock_client_cls, mock_spinner):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        mock_ctx_cls.return_value = MagicMock()
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_datasets.return_value = SAMPLE_DATASETS

        result = runner.invoke(app, ["list", "--porcelain"])
        assert result.exit_code == 0
        assert "1" in result.output

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_json_output(self, mock_ctx_cls, mock_client_cls, mock_spinner):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        mock_ctx_cls.return_value = MagicMock()
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_datasets.return_value = SAMPLE_DATASETS

        result = runner.invoke(app, ["list", "--json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert len(parsed) == 2
        assert parsed[0]["table_name"] == "sales"

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_yaml_output(self, mock_ctx_cls, mock_client_cls, mock_spinner):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        mock_ctx_cls.return_value = MagicMock()
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_datasets.return_value = SAMPLE_DATASETS

        result = runner.invoke(app, ["list", "--yaml"])
        assert result.exit_code == 0

    @patch("sup.commands.dataset.display_datasets_table")
    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_table_output(self, mock_ctx_cls, mock_client_cls, mock_spinner, mock_table):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm

        ctx = MagicMock()
        ctx.get_workspace_hostname.return_value = "ws.preset.io"
        mock_ctx_cls.return_value = ctx
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_datasets.return_value = SAMPLE_DATASETS

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 0
        mock_table.assert_called_once()

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_spinner_none(self, mock_ctx_cls, mock_client_cls, mock_spinner):
        mock_spinner.return_value = _make_spinner_none()
        mock_ctx_cls.return_value = MagicMock()
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_datasets.return_value = []

        result = runner.invoke(app, ["list", "--porcelain"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CTX)
    def test_error_non_porcelain(self, mock_ctx_cls, mock_spinner):
        mock_ctx_cls.side_effect = RuntimeError("boom")
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm

        result = runner.invoke(app, ["list"])
        assert result.exit_code == 1

    @patch(PATCH_SPINNER)
    @patch(PATCH_CTX)
    def test_error_porcelain(self, mock_ctx_cls, mock_spinner):
        mock_ctx_cls.side_effect = RuntimeError("boom")
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm

        result = runner.invoke(app, ["list", "--porcelain"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# dataset_info
# ---------------------------------------------------------------------------


class TestDatasetInfo:
    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_porcelain(self, mock_ctx_cls, mock_client_cls, mock_spinner):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        mock_ctx_cls.return_value = MagicMock()
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_dataset.return_value = {
            "id": 1,
            "table_name": "sales",
            "database_name": "main_db",
        }

        result = runner.invoke(app, ["info", "1", "--porcelain"])
        assert result.exit_code == 0
        assert "1\tsales\tmain_db" in result.output

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_json_output(self, mock_ctx_cls, mock_client_cls, mock_spinner):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        mock_ctx_cls.return_value = MagicMock()
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_dataset.return_value = {"id": 1, "table_name": "sales"}

        result = runner.invoke(app, ["info", "1", "--json"])
        assert result.exit_code == 0
        parsed = json.loads(result.output)
        assert parsed["id"] == 1
        assert parsed["table_name"] == "sales"

    @patch("sup.commands.dataset.display_dataset_details")
    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_table_output(self, mock_ctx_cls, mock_client_cls, mock_spinner, mock_details):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        mock_ctx_cls.return_value = MagicMock()
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        dataset = {"id": 1, "table_name": "sales"}
        client.get_dataset.return_value = dataset

        result = runner.invoke(app, ["info", "1"])
        assert result.exit_code == 0
        mock_details.assert_called_once_with(dataset)

    @patch(PATCH_SPINNER)
    @patch(PATCH_CTX)
    def test_error_non_porcelain(self, mock_ctx_cls, mock_spinner):
        mock_ctx_cls.side_effect = RuntimeError("fail")
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm

        result = runner.invoke(app, ["info", "1"])
        assert result.exit_code == 1

    @patch(PATCH_SPINNER)
    @patch(PATCH_CTX)
    def test_error_porcelain(self, mock_ctx_cls, mock_spinner):
        mock_ctx_cls.side_effect = RuntimeError("fail")
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm

        result = runner.invoke(app, ["info", "1", "--porcelain"])
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# display_datasets_table
# ---------------------------------------------------------------------------


class TestDisplayDatasetsTable:
    @patch("sup.commands.dataset.console")
    def test_empty_datasets(self, mock_console):
        display_datasets_table([])
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("No datasets" in c for c in calls)

    @patch("sup.commands.dataset.console")
    def test_with_hostname_and_explore_url(self, mock_console):
        datasets = [
            {
                "id": 1,
                "table_name": "sales",
                "database": {"database_name": "db"},
                "schema": "public",
                "kind": "physical",
                "columns": [{"column_name": "id"}],
                "explore_url": "/explore/?datasource_type=table&datasource_id=1",
            },
        ]
        display_datasets_table(datasets, "ws.preset.io")
        table = mock_console.print.call_args_list[0][0][0]
        # Name column should contain link with "sales"
        name_cells = table.columns[1]._cells
        assert any("sales" in cell for cell in name_cells)
        # Hostname should appear in links
        assert any("ws.preset.io" in cell for cell in name_cells)

    @patch("sup.commands.dataset.console")
    def test_with_hostname_no_explore_url(self, mock_console):
        datasets = [
            {
                "id": 2,
                "table_name": "users",
                "database": {"database_name": "db"},
                "schema": "",
                "kind": "virtual",
                "columns": [],
            },
        ]
        display_datasets_table(datasets, "ws.preset.io")
        table = mock_console.print.call_args_list[0][0][0]
        name_cells = table.columns[1]._cells
        assert any("users" in cell for cell in name_cells)

    @patch("sup.commands.dataset.console")
    def test_without_hostname(self, mock_console):
        datasets = [
            {
                "id": 3,
                "table_name": "orders",
                "database": {"database_name": "db"},
                "schema": "public",
                "kind": "physical",
                "columns": [],
            },
        ]
        display_datasets_table(datasets, None)
        table = mock_console.print.call_args_list[0][0][0]
        name_cells = table.columns[1]._cells
        assert "orders" in name_cells

    @patch("sup.commands.dataset.console")
    def test_dataset_missing_fields(self, mock_console):
        datasets = [{"id": 4}]
        display_datasets_table(datasets)
        table = mock_console.print.call_args_list[0][0][0]
        name_cells = table.columns[1]._cells
        assert "Unknown" in name_cells

    @patch("sup.commands.dataset.console")
    def test_dataset_with_name_fallback(self, mock_console):
        datasets = [
            {
                "id": 5,
                "name": "fallback_name",
                "database": {},
                "columns": [],
            },
        ]
        display_datasets_table(datasets)
        table = mock_console.print.call_args_list[0][0][0]
        name_cells = table.columns[1]._cells
        assert "fallback_name" in name_cells


# ---------------------------------------------------------------------------
# display_dataset_details
# ---------------------------------------------------------------------------


class TestDisplayDatasetDetails:
    @patch("sup.commands.dataset.console")
    def test_basic(self, mock_console):
        dataset = {
            "id": 1,
            "table_name": "sales",
            "database": {"database_name": "main_db"},
            "schema": "public",
            "kind": "physical",
            "columns": [],
        }
        display_dataset_details(dataset)
        assert mock_console.print.called

    @patch("sup.commands.dataset.console")
    def test_with_description(self, mock_console):
        dataset = {
            "id": 1,
            "table_name": "sales",
            "database": {"database_name": "main_db"},
            "schema": "public",
            "kind": "physical",
            "columns": [],
            "description": "Sales table",
        }
        display_dataset_details(dataset)
        panel = mock_console.print.call_args_list[0][0][0]
        assert "Sales table" in str(panel.renderable)

    @patch("sup.commands.dataset.console")
    def test_with_columns_under_20(self, mock_console):
        cols = [
            {"column_name": f"col_{i}", "type": "VARCHAR", "description": f"desc {i}"}
            for i in range(5)
        ]
        dataset = {
            "id": 1,
            "table_name": "sales",
            "database": {},
            "columns": cols,
        }
        display_dataset_details(dataset)

    @patch("sup.commands.dataset.console")
    def test_with_columns_over_20(self, mock_console):
        cols = [
            {"column_name": f"col_{i}", "type": "VARCHAR", "description": ""} for i in range(25)
        ]
        dataset = {
            "id": 1,
            "table_name": "wide_table",
            "database": {},
            "columns": cols,
        }
        display_dataset_details(dataset)
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("5 more" in c for c in calls)

    @patch("sup.commands.dataset.console")
    def test_no_columns(self, mock_console):
        dataset = {
            "id": 1,
            "table_name": "empty",
            "database": {},
            "columns": [],
        }
        display_dataset_details(dataset)
        panel = mock_console.print.call_args_list[0][0][0]
        assert "empty" in str(panel.title)
        # Only the Panel should be printed (no column section)
        assert mock_console.print.call_count == 1

    @patch("sup.commands.dataset.console")
    def test_column_no_description(self, mock_console):
        cols = [{"column_name": "c1", "type": "INT", "description": None}]
        dataset = {
            "id": 1,
            "table_name": "t",
            "database": {},
            "columns": cols,
        }
        display_dataset_details(dataset)
        # Should have Panel + column header + column table = 3 prints
        assert mock_console.print.call_count == 3
        all_text = " ".join(str(c) for c in mock_console.print.call_args_list)
        assert "Columns" in all_text

    @patch("sup.commands.dataset.console")
    def test_name_fallback(self, mock_console):
        dataset = {
            "id": 1,
            "name": "fallback",
            "database": {},
            "columns": [],
        }
        display_dataset_details(dataset)
        panel = mock_console.print.call_args_list[0][0][0]
        assert "fallback" in str(panel.title)


# ---------------------------------------------------------------------------
# pull_datasets
# ---------------------------------------------------------------------------


class TestPullDatasets:
    def _setup_pull_mocks(
        self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path, datasets=None, zip_files=None
    ):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm

        ctx = MagicMock()
        ctx.get_assets_folder.return_value = str(tmp_path / "assets")
        mock_ctx_cls.return_value = ctx

        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_datasets.return_value = datasets if datasets is not None else SAMPLE_DATASETS

        if zip_files is None:
            zip_files = {
                "root/datasets/sales.yaml": "table_name: sales",
                "root/databases/main_db.yaml": "name: main_db",
            }
        client.client.export_zip.return_value = _make_zip(zip_files)

        return ctx, client, sp

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_creates_output_dir(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls,
            mock_client_cls,
            mock_spinner,
            tmp_path,
        )
        assets = tmp_path / "assets"
        assert not assets.exists()

        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_path_not_dir_error(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm

        file_path = tmp_path / "assets"
        file_path.write_text("not a dir")

        ctx = MagicMock()
        ctx.get_assets_folder.return_value = str(file_path)
        mock_ctx_cls.return_value = ctx

        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 1

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_id_filter(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls,
            mock_client_cls,
            mock_spinner,
            tmp_path,
        )

        result = runner.invoke(app, ["pull", "--id=1"])
        assert result.exit_code == 0
        client.client.export_zip.assert_called_once_with("dataset", [1])

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_ids_filter(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls,
            mock_client_cls,
            mock_spinner,
            tmp_path,
        )

        result = runner.invoke(app, ["pull", "--ids=1,2"])
        assert result.exit_code == 0
        client.client.export_zip.assert_called_once_with("dataset", [1, 2])

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_mine_filter_success(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls,
            mock_client_cls,
            mock_spinner,
            tmp_path,
        )
        client.client.get_me.return_value = {"id": 10}

        result = runner.invoke(app, ["pull", "--mine"])
        assert result.exit_code == 0
        client.client.export_zip.assert_called_once_with("dataset", [1])

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_mine_filter_get_me_failure(
        self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path
    ):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls,
            mock_client_cls,
            mock_spinner,
            tmp_path,
        )
        client.client.get_me.side_effect = RuntimeError("unauthorized")

        result = runner.invoke(app, ["pull", "--mine"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_limit(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls,
            mock_client_cls,
            mock_spinner,
            tmp_path,
        )

        result = runner.invoke(app, ["pull", "--limit=1"])
        assert result.exit_code == 0
        client.client.export_zip.assert_called_once_with("dataset", [1])

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_no_datasets_warning(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls,
            mock_client_cls,
            mock_spinner,
            tmp_path,
            datasets=[],
        )

        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_skip_dependencies(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls,
            mock_client_cls,
            mock_spinner,
            tmp_path,
            zip_files={
                "root/datasets/sales.yaml": "table_name: sales",
                "root/databases/main_db.yaml": "name: main_db",
            },
        )

        result = runner.invoke(app, ["pull", "--skip-dependencies"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_file_exists_no_overwrite(
        self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path
    ):
        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        datasets_dir = assets / "datasets"
        datasets_dir.mkdir()
        (datasets_dir / "sales.yaml").write_text("old content")

        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls,
            mock_client_cls,
            mock_spinner,
            tmp_path,
        )
        ctx.get_assets_folder.return_value = str(assets)

        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 0
        assert (datasets_dir / "sales.yaml").read_text() == "old content"

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_file_exists_overwrite(
        self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path
    ):
        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        datasets_dir = assets / "datasets"
        datasets_dir.mkdir()
        (datasets_dir / "sales.yaml").write_text("old content")

        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls,
            mock_client_cls,
            mock_spinner,
            tmp_path,
        )
        ctx.get_assets_folder.return_value = str(assets)

        result = runner.invoke(app, ["pull", "--overwrite"])
        assert result.exit_code == 0
        content = (datasets_dir / "sales.yaml").read_text()
        assert "table_name: sales" in content

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_creates_parent_dirs(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        assets = tmp_path / "assets"
        assets.mkdir(parents=True)

        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls,
            mock_client_cls,
            mock_spinner,
            tmp_path,
            zip_files={"root/datasets/deep/nested/file.yaml": "content"},
        )
        ctx.get_assets_folder.return_value = str(assets)

        result = runner.invoke(app, ["pull", "--overwrite"])
        assert result.exit_code == 0
        assert (assets / "datasets" / "deep" / "nested" / "file.yaml").exists()

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_porcelain_output(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls,
            mock_client_cls,
            mock_spinner,
            tmp_path,
        )

        result = runner.invoke(app, ["pull", "--porcelain"])
        assert result.exit_code == 0
        assert "\t" in result.output

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_normal_output_with_deps(
        self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path
    ):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls,
            mock_client_cls,
            mock_spinner,
            tmp_path,
        )

        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_error_non_porcelain(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        ctx = MagicMock()
        ctx.get_assets_folder.return_value = "/tmp/test_assets"
        mock_ctx_cls.return_value = ctx
        mock_client_cls.from_context.side_effect = RuntimeError("connection failed")

        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 1

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_error_porcelain(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        ctx = MagicMock()
        ctx.get_assets_folder.return_value = "/tmp/test_assets"
        mock_ctx_cls.return_value = ctx
        mock_client_cls.from_context.side_effect = RuntimeError("connection failed")

        result = runner.invoke(app, ["pull", "--porcelain"])
        assert result.exit_code == 1

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_spinner_none(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        mock_spinner.return_value = _make_spinner_none()

        ctx = MagicMock()
        ctx.get_assets_folder.return_value = str(tmp_path / "assets")
        mock_ctx_cls.return_value = ctx

        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_datasets.return_value = SAMPLE_DATASETS
        client.client.export_zip.return_value = _make_zip(
            {"root/datasets/sales.yaml": "table_name: sales"},
        )

        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_file_exists_no_overwrite_porcelain(
        self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path
    ):
        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        datasets_dir = assets / "datasets"
        datasets_dir.mkdir()
        (datasets_dir / "sales.yaml").write_text("old")

        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        ctx = MagicMock()
        ctx.get_assets_folder.return_value = str(assets)
        mock_ctx_cls.return_value = ctx
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_datasets.return_value = SAMPLE_DATASETS
        client.client.export_zip.return_value = _make_zip(
            {"root/datasets/sales.yaml": "new"},
        )

        result = runner.invoke(app, ["pull", "--porcelain"])
        assert result.exit_code == 0
        assert (datasets_dir / "sales.yaml").read_text() == "old"

