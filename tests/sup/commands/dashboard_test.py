"""Tests for sup.commands.dashboard module - 100% line coverage."""

import io
import json
import zipfile
from unittest.mock import MagicMock, patch

import typer
from typer.testing import CliRunner

from sup.commands.dashboard import app, display_dashboard_details

runner = CliRunner()

# The imports happen INSIDE the command functions, so we patch at the source:
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


SAMPLE_DASHBOARDS = [
    {
        "id": 1,
        "dashboard_title": "Sales",
        "published": True,
        "created_on": "2024-01-01T00:00:00",
        "owners": [{"id": 10}],
    },
    {
        "id": 2,
        "dashboard_title": "Marketing",
        "published": False,
        "created_on": "2024-02-01T00:00:00",
        "owners": [{"id": 20}],
    },
]


# ---------------------------------------------------------------------------
# list_dashboards
# ---------------------------------------------------------------------------

class TestListDashboards:

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_porcelain(self, mock_ctx_cls, mock_client_cls, mock_spinner):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        mock_ctx_cls.return_value = MagicMock()
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_dashboards.return_value = SAMPLE_DASHBOARDS

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
        client.get_dashboards.return_value = SAMPLE_DASHBOARDS

        result = runner.invoke(app, ["list", "--json"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_yaml_output(self, mock_ctx_cls, mock_client_cls, mock_spinner):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        mock_ctx_cls.return_value = MagicMock()
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_dashboards.return_value = SAMPLE_DASHBOARDS

        result = runner.invoke(app, ["list", "--yaml"])
        assert result.exit_code == 0

    @patch("sup.commands.dashboard.display_dashboards_table")
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
        client.get_dashboards.return_value = SAMPLE_DASHBOARDS

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
        client.get_dashboards.return_value = []

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
# dashboard_info
# ---------------------------------------------------------------------------

class TestDashboardInfo:

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_porcelain(self, mock_ctx_cls, mock_client_cls, mock_spinner):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        mock_ctx_cls.return_value = MagicMock()
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_dashboard.return_value = {
            "id": 1,
            "dashboard_title": "Sales",
            "published": True,
        }

        result = runner.invoke(app, ["info", "1", "--porcelain"])
        assert result.exit_code == 0
        assert "1\tSales\tTrue" in result.output

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_json_output(self, mock_ctx_cls, mock_client_cls, mock_spinner):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        mock_ctx_cls.return_value = MagicMock()
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_dashboard.return_value = {"id": 1, "dashboard_title": "Sales"}

        result = runner.invoke(app, ["info", "1", "--json"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_yaml_output(self, mock_ctx_cls, mock_client_cls, mock_spinner):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        mock_ctx_cls.return_value = MagicMock()
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_dashboard.return_value = {"id": 1, "dashboard_title": "Sales"}

        result = runner.invoke(app, ["info", "1", "--yaml"])
        assert result.exit_code == 0

    @patch("sup.commands.dashboard.display_dashboard_details")
    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_table_output(self, mock_ctx_cls, mock_client_cls, mock_spinner, mock_details):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        mock_ctx_cls.return_value = MagicMock()
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        dashboard = {"id": 1, "dashboard_title": "Sales"}
        client.get_dashboard.return_value = dashboard

        result = runner.invoke(app, ["info", "1"])
        assert result.exit_code == 0
        mock_details.assert_called_once_with(dashboard)

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
# display_dashboard_details
# ---------------------------------------------------------------------------

class TestDisplayDashboardDetails:

    @patch("sup.commands.dashboard.console")
    def test_basic_no_optional_fields(self, mock_console):
        dashboard = {"id": 1, "dashboard_title": "Test", "published": False, "slug": "test"}
        display_dashboard_details(dashboard)
        assert mock_console.print.called

    @patch("sup.commands.dashboard.console")
    def test_with_description_and_dates(self, mock_console):
        dashboard = {
            "id": 1,
            "dashboard_title": "Test",
            "published": True,
            "slug": "test",
            "description": "A dashboard",
            "created_on": "2024-01-15T12:00:00",
            "changed_on": "2024-02-20T14:00:00",
        }
        display_dashboard_details(dashboard)
        assert mock_console.print.called

    @patch("sup.commands.dashboard.console")
    def test_owners_with_name_and_email(self, mock_console):
        dashboard = {
            "id": 1,
            "dashboard_title": "Test",
            "published": False,
            "owners": [
                {"first_name": "Alice", "last_name": "Smith", "email": "alice@example.com"},
            ],
        }
        display_dashboard_details(dashboard)
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("Alice Smith" in c for c in calls)

    @patch("sup.commands.dashboard.console")
    def test_owners_email_only(self, mock_console):
        dashboard = {
            "id": 1,
            "dashboard_title": "Test",
            "published": False,
            "owners": [{"email": "bob@example.com"}],
        }
        display_dashboard_details(dashboard)
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("bob@example.com" in c for c in calls)

    @patch("sup.commands.dashboard.console")
    def test_owners_no_email_no_name(self, mock_console):
        dashboard = {
            "id": 1,
            "dashboard_title": "Test",
            "published": False,
            "owners": [{}],
        }
        display_dashboard_details(dashboard)

    @patch("sup.commands.dashboard.console")
    def test_owners_more_than_five(self, mock_console):
        dashboard = {
            "id": 1,
            "dashboard_title": "Test",
            "published": False,
            "owners": [
                {"first_name": f"User{i}", "last_name": "", "email": f"u{i}@example.com"}
                for i in range(8)
            ],
        }
        display_dashboard_details(dashboard)
        calls = [str(c) for c in mock_console.print.call_args_list]
        assert any("3 more" in c for c in calls)

    @patch("sup.commands.dashboard.console")
    def test_position_json_with_charts(self, mock_console):
        position = {
            "CHART-abc": {
                "meta": {
                    "chartId": 10,
                    "sliceName": "Revenue",
                    "uuid": "uuid-1",
                    "sliceNameOverride": "Revenue Override",
                },
            },
            "CHART-def": {
                "meta": {
                    "chartId": 5,
                    "sliceName": "Costs",
                    "uuid": "uuid-2",
                },
            },
            "OTHER-xyz": {"meta": {}},
        }
        dashboard = {
            "id": 1,
            "dashboard_title": "Test",
            "published": False,
            "position_json": json.dumps(position),
        }
        display_dashboard_details(dashboard)
        assert mock_console.print.called

    @patch("sup.commands.dashboard.console")
    def test_position_json_parse_failure_fallback(self, mock_console):
        dashboard = {
            "id": 1,
            "dashboard_title": "Test",
            "published": False,
            "position_json": "NOT VALID JSON",
            "charts": ["ChartA", "ChartB"],
        }
        display_dashboard_details(dashboard)
        assert mock_console.print.called

    @patch("sup.commands.dashboard.console")
    def test_no_chart_data(self, mock_console):
        dashboard = {
            "id": 1,
            "dashboard_title": "Test",
            "published": False,
            "position_json": "{}",
        }
        display_dashboard_details(dashboard)

    @patch("sup.commands.dashboard.console")
    def test_chart_without_override_name(self, mock_console):
        position = {
            "CHART-a": {
                "meta": {
                    "chartId": 7,
                    "sliceName": "Original",
                    "uuid": "u1",
                    "sliceNameOverride": None,
                },
            },
        }
        dashboard = {
            "id": 1,
            "dashboard_title": "Test",
            "published": False,
            "position_json": json.dumps(position),
        }
        display_dashboard_details(dashboard)

    @patch("sup.commands.dashboard.console")
    def test_chart_data_no_id(self, mock_console):
        position = {
            "CHART-a": {
                "meta": {
                    "chartId": "",
                    "sliceName": "NoID",
                    "uuid": "u1",
                },
            },
        }
        dashboard = {
            "id": 1,
            "dashboard_title": "Test",
            "published": False,
            "position_json": json.dumps(position),
        }
        display_dashboard_details(dashboard)


# ---------------------------------------------------------------------------
# pull_dashboards
# ---------------------------------------------------------------------------

class TestPullDashboards:

    def _setup_pull_mocks(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path,
                          dashboards=None, zip_files=None):
        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm

        ctx = MagicMock()
        ctx.get_assets_folder.return_value = str(tmp_path / "assets")
        mock_ctx_cls.return_value = ctx

        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_dashboards.return_value = dashboards if dashboards is not None else SAMPLE_DASHBOARDS

        if zip_files is None:
            zip_files = {
                "root/dashboards/Sales.yaml": "title: Sales",
                "root/charts/Chart1.yaml": "name: Chart1",
            }
        client.client.export_zip.return_value = _make_zip(zip_files)

        return ctx, client, sp

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_creates_output_dir(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path,
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
            mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path,
        )

        result = runner.invoke(app, ["pull", "--id=1"])
        assert result.exit_code == 0
        client.client.export_zip.assert_called_once_with("dashboard", [1])

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_ids_filter(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path,
        )

        result = runner.invoke(app, ["pull", "--ids=1,2"])
        assert result.exit_code == 0
        client.client.export_zip.assert_called_once_with("dashboard", [1, 2])

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_mine_filter_success(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path,
        )
        client.client.get_me.return_value = {"id": 10}

        result = runner.invoke(app, ["pull", "--mine"])
        assert result.exit_code == 0
        client.client.export_zip.assert_called_once_with("dashboard", [1])

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_mine_filter_get_me_failure(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path,
        )
        client.client.get_me.side_effect = RuntimeError("unauthorized")

        result = runner.invoke(app, ["pull", "--mine"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_limit(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path,
        )

        result = runner.invoke(app, ["pull", "--limit=1"])
        assert result.exit_code == 0
        client.client.export_zip.assert_called_once_with("dashboard", [1])

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_no_dashboards_warning(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path,
            dashboards=[],
        )

        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_skip_dependencies(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path,
            zip_files={
                "root/dashboards/Sales.yaml": "title: Sales",
                "root/charts/Chart1.yaml": "name: Chart1",
            },
        )

        result = runner.invoke(app, ["pull", "--skip-dependencies"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_file_exists_no_overwrite(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        dashboards_dir = assets / "dashboards"
        dashboards_dir.mkdir()
        (dashboards_dir / "Sales.yaml").write_text("old content")

        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path,
        )
        ctx.get_assets_folder.return_value = str(assets)

        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 0
        assert (dashboards_dir / "Sales.yaml").read_text() == "old content"

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_file_exists_overwrite(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        dashboards_dir = assets / "dashboards"
        dashboards_dir.mkdir()
        (dashboards_dir / "Sales.yaml").write_text("old content")

        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path,
        )
        ctx.get_assets_folder.return_value = str(assets)

        result = runner.invoke(app, ["pull", "--overwrite"])
        assert result.exit_code == 0
        assert (dashboards_dir / "Sales.yaml").read_text() == "title: Sales"

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_creates_parent_dirs(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        assets = tmp_path / "assets"
        assets.mkdir(parents=True)

        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path,
            zip_files={"root/dashboards/deep/nested/file.yaml": "content"},
        )
        ctx.get_assets_folder.return_value = str(assets)

        result = runner.invoke(app, ["pull", "--overwrite"])
        assert result.exit_code == 0
        assert (assets / "dashboards" / "deep" / "nested" / "file.yaml").exists()

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_porcelain_output(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path,
        )

        result = runner.invoke(app, ["pull", "--porcelain"])
        assert result.exit_code == 0
        assert "\t" in result.output

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_normal_output_with_deps(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        ctx, client, sp = self._setup_pull_mocks(
            mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path,
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
        client.get_dashboards.return_value = SAMPLE_DASHBOARDS
        client.client.export_zip.return_value = _make_zip(
            {"root/dashboards/Sales.yaml": "title: Sales"},
        )

        result = runner.invoke(app, ["pull"])
        assert result.exit_code == 0

    @patch(PATCH_SPINNER)
    @patch(PATCH_CLIENT)
    @patch(PATCH_CTX)
    def test_pull_file_exists_no_overwrite_porcelain(self, mock_ctx_cls, mock_client_cls, mock_spinner, tmp_path):
        assets = tmp_path / "assets"
        assets.mkdir(parents=True)
        dashboards_dir = assets / "dashboards"
        dashboards_dir.mkdir()
        (dashboards_dir / "Sales.yaml").write_text("old")

        cm, sp = _make_spinner_mock()
        mock_spinner.return_value = cm
        ctx = MagicMock()
        ctx.get_assets_folder.return_value = str(assets)
        mock_ctx_cls.return_value = ctx
        client = MagicMock()
        mock_client_cls.from_context.return_value = client
        client.get_dashboards.return_value = SAMPLE_DASHBOARDS
        client.client.export_zip.return_value = _make_zip(
            {"root/dashboards/Sales.yaml": "new"},
        )

        result = runner.invoke(app, ["pull", "--porcelain"])
        assert result.exit_code == 0
        assert (dashboards_dir / "Sales.yaml").read_text() == "old"
