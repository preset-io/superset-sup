"""Tests for sup.commands.chart module — targeting 100% line coverage."""

import io
import json
import zipfile
from unittest.mock import MagicMock, patch

from rich.console import Console
from typer.testing import CliRunner

from sup.commands.chart import (
    app,
    display_chart_data_results,
    display_chart_details,
    display_chart_sql_compiled,
    display_chart_sql_rich,
    display_charts_table,
)

runner = CliRunner()


def _render(rich_obj) -> str:
    """Render a Rich object to plain text for assertion checks."""
    buf = io.StringIO()
    Console(file=buf, width=300, no_color=True).print(rich_obj)
    return buf.getvalue()


# Patch targets
_CTX = "sup.config.settings.SupContext"
_CLI = "sup.clients.superset.SupSupersetClient"
_DSP = "sup.output.spinners.data_spinner"
_QSP = "sup.output.spinners.query_spinner"
_PARSE = "sup.commands.chart.parse_chart_filters"
# console is imported at module-level in chart.py, so patch the reference there
_CON = "sup.commands.chart.console"
_PORCELAIN = "sup.output.formatters.display_porcelain_list"
_CTBL = "sup.output.tables.display_charts_table"
_QR = "sup.output.formatters.QueryResult"
_DQR = "sup.output.formatters.display_query_results"
_PAUTH = "sup.auth.preset.SupPresetAuth"
_PCLI = "sup.clients.preset.SupPresetClient"
_NATIVE = "preset_cli.cli.superset.sync.native.command.native"


def _ctx(workspace_id=1, hostname="ws.preset.io", assets_folder="./assets", target_workspace_id=2):
    m = MagicMock()
    m.get_workspace_id.return_value = workspace_id
    m.get_workspace_hostname.return_value = hostname
    m.get_assets_folder.return_value = assets_folder
    m.get_target_workspace_id.return_value = target_workspace_id
    return m


def _client(charts=None, chart=None, chart_data=None):
    c = MagicMock()
    c.get_charts.return_value = charts if charts is not None else []
    c.get_chart.return_value = chart or {"id": 1, "slice_name": "Test"}
    c.get_chart_data.return_value = chart_data or {}
    c.client.get_me.return_value = {"id": 99}
    c.client.export_zip.return_value = io.BytesIO()
    c.client.baseurl = "https://ws.preset.io"
    return c


def _sp():
    sp = MagicMock()
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=sp)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, sp


def _zipbuf(files: dict) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    buf.seek(0)
    return buf


CHART = {
    "id": 1,
    "slice_name": "Sales Chart",
    "viz_type": "bar",
    "datasource_name_text": "sales_table",
    "datasource_name": "sales",
    "datasource_id": 10,
    "dashboards": [{"id": 1, "dashboard_title": "Main Dashboard"}],
    "description": "A chart",
    "params": "{}",
    "query_context": "{}",
}


# ===================================================================
# list_charts
# ===================================================================


class TestListCharts:
    def _invoke(self, args, charts=None, mine=False, mine_fails=False, limit=None):
        filters = MagicMock()
        filters.page = None
        filters.search = None
        filters.mine = mine
        filters.limit = limit

        cm, sp = _sp()
        cl = _client(charts=charts if charts is not None else [CHART])
        if mine_fails:
            cl.client.get_me.side_effect = Exception("fail")

        with patch(_PARSE, return_value=filters), patch(_DSP, return_value=cm), patch(
            _CLI, **{"from_context.return_value": cl}
        ), patch(_CTX, return_value=_ctx()), patch(
            "sup.filters.chart.apply_chart_filters", return_value=cl.get_charts()
        ), patch(_CON):
            return runner.invoke(app, ["list"] + args)

    def test_porcelain(self):
        with patch(_PORCELAIN):
            assert self._invoke(["--porcelain"]).exit_code == 0

    def test_json(self):
        assert self._invoke(["--json"]).exit_code == 0

    def test_yaml(self):
        assert self._invoke(["--yaml"]).exit_code == 0

    def test_table(self):
        with patch(_CTBL):
            assert self._invoke([]).exit_code == 0

    def test_mine_success(self):
        assert self._invoke(["--mine"], mine=True).exit_code == 0

    def test_mine_fails(self):
        assert self._invoke(["--mine"], mine=True, mine_fails=True).exit_code == 0

    def test_limit(self):
        assert self._invoke(["--limit", "1"], charts=[CHART, CHART], limit=1).exit_code == 0

    def test_error(self):
        with patch(_CTX, side_effect=RuntimeError("x")), patch(_PARSE), patch(_DSP), patch(_CON):
            assert runner.invoke(app, ["list"]).exit_code == 1

    def test_error_porcelain(self):
        with patch(_CTX, side_effect=RuntimeError("x")), patch(_PARSE), patch(_DSP), patch(_CON):
            assert runner.invoke(app, ["list", "--porcelain"]).exit_code == 1

    def test_no_limit_applied(self):
        """Branch 180->184, 184->152: limit=None and sp=None via real data_spinner."""
        from sup.filters.chart import ChartFilters

        filters = ChartFilters(limit=None)
        cl = _client(charts=[CHART])

        # Use real data_spinner (silent=True via --porcelain) so coverage tracks branches.
        with patch(_PARSE, return_value=filters), patch(
            _CLI, **{"from_context.return_value": cl}
        ), patch(_CTX, return_value=_ctx()), patch(
            "sup.filters.chart.apply_chart_filters", return_value=[CHART]
        ), patch(_CON), patch(_PORCELAIN):
            assert runner.invoke(app, ["list", "--porcelain"]).exit_code == 0


# ===================================================================
# chart_info
# ===================================================================


class TestChartInfo:
    def _invoke(self, args, chart=None):
        cm, sp = _sp()
        cl = _client(chart=chart or CHART)
        with patch(_CLI, **{"from_context.return_value": cl}), patch(
            _CTX, return_value=_ctx()
        ), patch(_DSP, return_value=cm), patch(_CON):
            return runner.invoke(app, ["info"] + args)

    def test_porcelain(self):
        r = self._invoke(["1", "--porcelain"])
        assert r.exit_code == 0
        assert "1\tSales Chart\tbar" in r.output

    def test_json(self):
        assert self._invoke(["1", "--json"]).exit_code == 0

    def test_yaml(self):
        assert self._invoke(["1", "--yaml"]).exit_code == 0

    def test_table(self):
        with patch("sup.commands.chart.display_chart_details"):
            assert self._invoke(["1"]).exit_code == 0

    def test_error(self):
        with patch(_CTX, side_effect=RuntimeError("x")), patch(_DSP), patch(_CON):
            assert runner.invoke(app, ["info", "1"]).exit_code == 1

    def test_error_porcelain(self):
        with patch(_CTX, side_effect=RuntimeError("x")), patch(_DSP), patch(_CON):
            assert runner.invoke(app, ["info", "1", "--porcelain"]).exit_code == 1


# ===================================================================
# chart_sql
# ===================================================================


class TestChartSql:
    def _invoke(self, args, query_result=None):
        cm, sp = _sp()
        data = query_result or {"result": [{"query": "SELECT 1"}]}
        cl = _client(chart=CHART, chart_data=data)
        with patch(_CLI, **{"from_context.return_value": cl}), patch(
            _CTX, return_value=_ctx()
        ), patch(_QSP, return_value=cm), patch(_CON):
            return runner.invoke(app, ["sql"] + args)

    def test_porcelain(self):
        r = self._invoke(["1", "--porcelain"])
        assert r.exit_code == 0
        assert "SELECT 1" in r.output

    def test_json(self):
        cm, sp = _sp()
        data = {"result": [{"query": "SELECT 1"}]}
        cl = _client(chart=CHART, chart_data=data)
        with patch(_CLI, **{"from_context.return_value": cl}), patch(
            _CTX, return_value=_ctx()
        ), patch(_QSP, return_value=cm), patch(_CON) as mc:
            r = runner.invoke(app, ["sql", "1", "--json"])
        assert r.exit_code == 0
        printed = str(mc.print.call_args_list)
        assert "sql_queries" in printed
        assert "SELECT 1" in printed

    def test_yaml(self):
        assert self._invoke(["1", "--yaml"]).exit_code == 0

    def test_rich(self):
        with patch("sup.commands.chart.display_chart_sql_rich"):
            assert self._invoke(["1"]).exit_code == 0

    def test_no_queries(self):
        with patch("sup.commands.chart.display_chart_sql_rich") as m:
            self._invoke(["1"], query_result={"result": [{"other": "x"}]})
        m.assert_called_once_with(1, "Sales Chart", [])

    def test_no_result_key(self):
        """Empty dict -> no result key -> empty sql_queries."""
        cm, sp = _sp()
        # Must override chart_data so get_chart_data returns {}
        cl = _client(chart=CHART)
        cl.get_chart_data.return_value = {}
        with patch(_CLI, **{"from_context.return_value": cl}), patch(
            _CTX, return_value=_ctx()
        ), patch(_QSP, return_value=cm), patch(_CON), patch(
            "sup.commands.chart.display_chart_sql_rich"
        ) as m:
            runner.invoke(app, ["sql", "1"])
        m.assert_called_once_with(1, "Sales Chart", [])

    def test_error(self):
        with patch(_CTX, side_effect=RuntimeError("x")), patch(_CON):
            assert runner.invoke(app, ["sql", "1"]).exit_code == 1

    def test_error_porcelain(self):
        with patch(_CTX, side_effect=RuntimeError("x")), patch(_CON):
            assert runner.invoke(app, ["sql", "1", "--porcelain"]).exit_code == 1


# ===================================================================
# chart_data
# ===================================================================


class TestChartData:
    def _invoke(self, args, data_result=None):
        cm, sp = _sp()
        default = {"result": [{"data": [{"col1": "a", "col2": 1}], "duration": 0.5}]}
        data = data_result if data_result is not None else default
        cl = _client(chart=CHART, chart_data=data)
        with patch(_CLI, **{"from_context.return_value": cl}), patch(
            _CTX, return_value=_ctx()
        ), patch(_DSP, return_value=cm), patch(_CON):
            return runner.invoke(app, ["data"] + args)

    def test_porcelain(self):
        r = self._invoke(["1", "--porcelain"])
        assert r.exit_code == 0
        assert "a\t1" in r.output

    def test_json(self):
        assert self._invoke(["1", "--json"]).exit_code == 0

    def test_yaml(self):
        assert self._invoke(["1", "--yaml"]).exit_code == 0

    def test_csv(self):
        cm, sp = _sp()
        default = {"result": [{"data": [{"col1": "a", "col2": 1}], "duration": 0.5}]}
        cl = _client(chart=CHART, chart_data=default)
        with patch(_CLI, **{"from_context.return_value": cl}), patch(
            _CTX, return_value=_ctx()
        ), patch(_DSP, return_value=cm), patch(_CON) as mc:
            r = runner.invoke(app, ["data", "1", "--csv"])
        assert r.exit_code == 0
        printed = str(mc.print.call_args_list)
        assert "col1" in printed
        assert "col2" in printed

    def test_table(self):
        with patch(_DQR), patch(_QR):
            assert self._invoke(["1"]).exit_code == 0

    def test_limit(self):
        assert self._invoke(["1", "--limit", "1", "--json"]).exit_code == 0

    def test_porcelain_nan(self):
        data = {"result": [{"data": [{"c": None}], "duration": 0.1}]}
        assert self._invoke(["1", "--porcelain"], data_result=data).exit_code == 0

    def test_no_data_in_result(self):
        assert self._invoke(["1"], data_result={"result": [{"x": 1}]}).exit_code == 1

    def test_no_data_porcelain(self):
        assert self._invoke(["1", "--porcelain"], data_result={"result": [{"x": 1}]}).exit_code == 1

    def test_no_result(self):
        assert self._invoke(["1"], data_result={}).exit_code == 1

    def test_no_result_porcelain(self):
        assert self._invoke(["1", "--porcelain"], data_result={}).exit_code == 1

    def test_empty_result(self):
        assert self._invoke(["1"], data_result={"result": []}).exit_code == 1

    def test_error(self):
        with patch(_CTX, side_effect=RuntimeError("x")), patch(_CON):
            assert runner.invoke(app, ["data", "1"]).exit_code == 1

    def test_error_porcelain(self):
        with patch(_CTX, side_effect=RuntimeError("x")), patch(_CON):
            assert runner.invoke(app, ["data", "1", "--porcelain"]).exit_code == 1


# ===================================================================
# display_chart_sql_rich
# ===================================================================


class TestDisplayChartSqlRich:
    @patch(_CON)
    def test_empty(self, mc):
        display_chart_sql_rich(1, "T", [])
        assert any("No SQL" in str(c) for c in mc.print.call_args_list)

    @patch(_CON)
    def test_single(self, mc):
        display_chart_sql_rich(1, "T", ["SELECT 1"])
        assert mc.print.call_count >= 2

    @patch(_CON)
    def test_multiple(self, mc):
        display_chart_sql_rich(1, "T", ["SELECT 1", "SELECT 2"])
        assert mc.print.call_count >= 3


# ===================================================================
# display_charts_table
# ===================================================================


class TestDisplayChartsTable:
    @patch(_CON)
    def test_empty(self, mc):
        display_charts_table([])
        assert any("No charts" in str(c) for c in mc.print.call_args_list)

    @patch(_CON)
    def test_with_hostname(self, mc):
        display_charts_table([CHART], workspace_hostname="ws.preset.io")
        assert mc.print.call_count >= 3

    @patch(_CON)
    def test_without_hostname(self, mc):
        display_charts_table([CHART], workspace_hostname=None)
        assert mc.print.call_count >= 2

    @patch(_CON)
    def test_dashboards_gt_two(self, mc):
        c = {**CHART, "dashboards": [{"id": i, "dashboard_title": f"D{i}"} for i in range(4)]}
        display_charts_table([c])
        assert mc.print.called
        rendered = _render(mc.print.call_args_list[0][0][0])
        assert "+2 more" in rendered

    @patch(_CON)
    def test_no_dashboards(self, mc):
        display_charts_table([{**CHART, "dashboards": []}])
        assert mc.print.called
        rendered = _render(mc.print.call_args_list[0][0][0])
        assert "None" in rendered

    @patch(_CON)
    def test_datasource_fallbacks(self, mc):
        display_charts_table([{**CHART, "datasource_name_text": None, "datasource_name": "fb"}])
        rendered = _render(mc.print.call_args_list[0][0][0])
        assert "fb" in rendered

        mc.reset_mock()
        display_charts_table(
            [{**CHART, "datasource_name_text": None, "datasource_name": None, "datasource_id": 42}]
        )
        rendered = _render(mc.print.call_args_list[0][0][0])
        assert "ID:42" in rendered

        mc.reset_mock()
        display_charts_table(
            [
                {
                    **CHART,
                    "datasource_name_text": None,
                    "datasource_name": None,
                    "datasource_id": None,
                }
            ]
        )
        rendered = _render(mc.print.call_args_list[0][0][0])
        assert "Unknown" in rendered


# ===================================================================
# display_chart_details
# ===================================================================


class TestDisplayChartDetails:
    @patch(_CON)
    def test_with_metadata(self, mc):
        display_chart_details(CHART, workspace_hostname="ws.preset.io")
        panel = mc.print.call_args_list[0][0][0]
        content = str(panel.renderable)
        assert "Sales Chart" in content
        assert "ws.preset.io" in content

    @patch(_CON)
    def test_no_hostname(self, mc):
        display_chart_details(CHART, workspace_hostname=None)
        panel = mc.print.call_args_list[0][0][0]
        content = str(panel.renderable)
        assert "Sales Chart" in content
        assert "URL:" not in content

    @patch(_CON)
    def test_no_description(self, mc):
        display_chart_details({**CHART, "description": None})
        panel = mc.print.call_args_list[0][0][0]
        assert "Description:" not in str(panel.renderable)

    @patch(_CON)
    def test_dashboards_gt_five(self, mc):
        c = {**CHART, "dashboards": [{"id": i, "dashboard_title": f"D{i}"} for i in range(7)]}
        display_chart_details(c)
        assert any("2 more" in str(x) for x in mc.print.call_args_list)

    @patch(_CON)
    def test_dashboards_lte_five(self, mc):
        display_chart_details({**CHART, "dashboards": [{"id": i} for i in range(3)]})
        assert any("3 dashboard" in str(c) for c in mc.print.call_args_list)
        # Each dashboard shown as "Dashboard <id>" fallback
        assert any("Dashboard 0" in str(c) for c in mc.print.call_args_list)

    @patch(_CON)
    def test_no_dashboards(self, mc):
        display_chart_details({**CHART, "dashboards": []})
        # No dashboard section printed — only the panel
        assert not any("dashboard(s)" in str(c) for c in mc.print.call_args_list)

    @patch(_CON)
    def test_query_context_lookup(self, mc):
        c = {
            **CHART,
            "datasource_name_text": None,
            "datasource_name": None,
            "query_context": json.dumps({"datasource": {"id": 5, "type": "table"}}),
        }
        cl = MagicMock()
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"result": {"table_name": "orders", "schema": "pub"}}
        cl.client.session.get.return_value = resp
        cl.client.baseurl = "https://x"
        display_chart_details(c, client=cl)
        panel = mc.print.call_args_list[0][0][0]
        assert "pub.orders" in str(panel.renderable)

    @patch(_CON)
    def test_params_lookup(self, mc):
        c = {
            **CHART,
            "datasource_name_text": None,
            "datasource_name": None,
            "query_context": "{}",
            "params": json.dumps({"datasource": "10__table"}),
        }
        cl = MagicMock()
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"result": {"table_name": "tbl", "schema": ""}}
        cl.client.session.get.return_value = resp
        cl.client.baseurl = "https://x"
        display_chart_details(c, client=cl)
        panel = mc.print.call_args_list[0][0][0]
        assert "tbl" in str(panel.renderable)

    @patch(_CON)
    def test_no_table_name(self, mc):
        c = {
            **CHART,
            "datasource_name_text": None,
            "datasource_name": None,
            "query_context": json.dumps({"datasource": {"id": 5, "type": "t"}}),
        }
        cl = MagicMock()
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"result": {"table_name": "", "schema": ""}}
        cl.client.session.get.return_value = resp
        cl.client.baseurl = "https://x"
        display_chart_details(c, client=cl)
        panel = mc.print.call_args_list[0][0][0]
        assert "Dataset ID: 5" in str(panel.renderable)

    @patch(_CON)
    def test_404(self, mc):
        c = {
            **CHART,
            "datasource_name_text": None,
            "datasource_name": None,
            "query_context": json.dumps({"datasource": {"id": 5, "type": "t"}}),
        }
        cl = MagicMock()
        cl.client.session.get.return_value = MagicMock(status_code=404)
        cl.client.baseurl = "https://x"
        display_chart_details(c, client=cl)
        panel = mc.print.call_args_list[0][0][0]
        assert "Dataset ID: 5 (not found)" in str(panel.renderable)

    @patch(_CON)
    def test_fetch_exception(self, mc):
        c = {
            **CHART,
            "datasource_name_text": None,
            "datasource_name": None,
            "query_context": json.dumps({"datasource": {"id": 5, "type": "t"}}),
        }
        cl = MagicMock()
        cl.client.session.get.side_effect = Exception("err")
        cl.client.baseurl = "https://x"
        display_chart_details(c, client=cl)
        panel = mc.print.call_args_list[0][0][0]
        assert "Dataset ID: 5" in str(panel.renderable)

    @patch(_CON)
    def test_no_client(self, mc):
        c = {**CHART, "datasource_name_text": None, "datasource_name": None}
        display_chart_details(c, client=None)
        panel = mc.print.call_args_list[0][0][0]
        assert "Unknown" in str(panel.renderable)

    @patch(_CON)
    def test_bad_json(self, mc):
        c = {
            **CHART,
            "datasource_name_text": None,
            "datasource_name": None,
            "query_context": "bad",
            "params": "bad",
        }
        cl = MagicMock()
        cl.client.baseurl = "https://x"
        display_chart_details(c, client=cl)
        panel = mc.print.call_args_list[0][0][0]
        assert "Unknown" in str(panel.renderable)

    @patch(_CON)
    def test_datasource_info_not_dict(self, mc):
        """Branch 625->632: datasource_info truthy but not a dict."""
        c = {
            **CHART,
            "datasource_name_text": None,
            "datasource_name": None,
            "query_context": json.dumps({"datasource": "string_not_dict"}),
            "params": "{}",
        }
        cl = MagicMock()
        cl.client.baseurl = "https://x"
        cl.client.session.get.return_value = MagicMock(status_code=404)
        display_chart_details(c, client=cl)
        panel = mc.print.call_args_list[0][0][0]
        # No dataset_id extracted, so falls back to "Unknown"
        assert "Unknown" in str(panel.renderable)

    @patch(_CON)
    def test_params_already_dict(self, mc):
        """Branch 634->645: params is already a dict (not a string)."""
        c = {
            **CHART,
            "datasource_name_text": None,
            "datasource_name": None,
            "query_context": "{}",
            "params": {"datasource": "10__table"},
        }
        cl = MagicMock()
        cl.client.baseurl = "https://x"
        display_chart_details(c, client=cl)
        panel = mc.print.call_args_list[0][0][0]
        # params is dict, not str — the isinstance(params, str) branch is skipped, so no dataset_id
        assert "Unknown" in str(panel.renderable)

    @patch(_CON)
    def test_200_no_result_key(self, mc):
        """Branch 652->667: 200 response without 'result' key."""
        c = {
            **CHART,
            "datasource_name_text": None,
            "datasource_name": None,
            "query_context": json.dumps({"datasource": {"id": 5, "type": "t"}}),
        }
        cl = MagicMock()
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"data": "no result key"}
        cl.client.session.get.return_value = resp
        cl.client.baseurl = "https://x"
        display_chart_details(c, client=cl)
        panel = mc.print.call_args_list[0][0][0]
        # 200 response without "result" key -> dataset_name stays unset -> "Unknown"
        assert "Unknown" in str(panel.renderable)

    @patch(_CON)
    def test_query_context_dict(self, mc):
        c = {
            **CHART,
            "datasource_name_text": None,
            "datasource_name": None,
            "query_context": {"datasource": {"id": 5, "type": "t"}},
        }
        cl = MagicMock()
        resp = MagicMock(status_code=200)
        resp.json.return_value = {"result": {"table_name": "t", "schema": "s"}}
        cl.client.session.get.return_value = resp
        cl.client.baseurl = "https://x"
        display_chart_details(c, client=cl)
        panel = mc.print.call_args_list[0][0][0]
        assert "s.t" in str(panel.renderable)

    @patch(_CON)
    def test_params_no_separator(self, mc):
        c = {
            **CHART,
            "datasource_name_text": None,
            "datasource_name": None,
            "query_context": "{}",
            "params": json.dumps({"datasource": "nope"}),
        }
        cl = MagicMock()
        cl.client.baseurl = "https://x"
        display_chart_details(c, client=cl)
        panel = mc.print.call_args_list[0][0][0]
        # No "__" separator means no dataset_id extracted -> "Unknown"
        assert "Unknown" in str(panel.renderable)

    @patch(_CON)
    def test_dashboard_no_title(self, mc):
        display_chart_details({**CHART, "dashboards": [{"id": 99}]})
        # Falls back to "Dashboard 99"
        assert any("Dashboard 99" in str(c) for c in mc.print.call_args_list)


# ===================================================================
# display_chart_sql_compiled
# ===================================================================


class TestDisplayChartSqlCompiled:
    @patch(_CON)
    def test_single(self, mc):
        cl = MagicMock()
        cl.get_chart_data.return_value = {"result": [{"query": "SELECT 1"}]}
        display_chart_sql_compiled(None, cl, 1, {"slice_name": "C"})

    @patch(_CON)
    def test_multiple(self, mc):
        cl = MagicMock()
        cl.get_chart_data.return_value = {"result": [{"query": "S1"}, {"query": "S2"}]}
        display_chart_sql_compiled(None, cl, 1, {"slice_name": "C"})

    @patch(_CON)
    def test_no_queries(self, mc):
        cl = MagicMock()
        cl.get_chart_data.return_value = {"result": []}
        display_chart_sql_compiled(None, cl, 1, {"slice_name": "C"})
        assert any("Could not retrieve" in str(c) for c in mc.print.call_args_list)

    @patch(_CON)
    def test_no_result_key(self, mc):
        """Branch 728->733: 'result' key missing entirely."""
        cl = MagicMock()
        cl.get_chart_data.return_value = {}
        display_chart_sql_compiled(None, cl, 1, {"slice_name": "C"})

    @patch(_CON)
    def test_result_item_no_query(self, mc):
        """Branch 730->729: result item without 'query' key."""
        cl = MagicMock()
        cl.get_chart_data.return_value = {"result": [{"data": "something"}]}
        display_chart_sql_compiled(None, cl, 1, {"slice_name": "C"})

    @patch(_CON)
    def test_exception(self, mc):
        cl = MagicMock()
        cl.get_chart_data.side_effect = Exception("e")
        display_chart_sql_compiled(None, cl, 1, {"slice_name": "C", "datasource_id": 5})
        assert any("not yet fully implemented" in str(c) for c in mc.print.call_args_list)


# ===================================================================
# display_chart_data_results
# ===================================================================


class TestDisplayChartDataResults:
    @patch(_DQR)
    @patch(_CON)
    def test_success(self, mc, md):
        cl = MagicMock()
        cl.get_chart_data.return_value = {"result": [{"data": [{"a": 1}], "duration": 0.1}]}
        display_chart_data_results(None, cl, 1, {"slice_name": "C", "datasource_id": 10})
        md.assert_called_once()

    @patch(_CON)
    def test_no_data(self, mc):
        cl = MagicMock()
        cl.get_chart_data.return_value = {"result": [{"x": 1}]}
        display_chart_data_results(None, cl, 1, {"slice_name": "C"})
        assert any("No data" in str(c) for c in mc.print.call_args_list)

    @patch(_CON)
    def test_no_result(self, mc):
        cl = MagicMock()
        cl.get_chart_data.return_value = {}
        display_chart_data_results(None, cl, 1, {"slice_name": "C"})
        assert any("Could not retrieve" in str(c) for c in mc.print.call_args_list)

    @patch(_CON)
    def test_empty_result(self, mc):
        cl = MagicMock()
        cl.get_chart_data.return_value = {"result": []}
        display_chart_data_results(None, cl, 1, {"slice_name": "C"})

    @patch(_CON)
    def test_exception(self, mc):
        cl = MagicMock()
        cl.get_chart_data.side_effect = RuntimeError("boom")
        display_chart_data_results(None, cl, 1, {"slice_name": "C"})
        assert any("Failed" in str(c) for c in mc.print.call_args_list)


# ===================================================================
# pull_charts
# ===================================================================


class TestPullCharts:
    DEFAULT_ZIP = {
        "bundle/charts/chart_1.yaml": "slice_name: Test\nviz_type: bar\n",
        "bundle/datasets/ds.yaml": "table_name: t\n",
        "bundle/metadata.yaml": "version: 1\n",
    }

    def _invoke(self, tmp_path, args_extra=None, charts=None, zip_files=None):
        cm, sp = _sp()
        cl = _client(charts=charts if charts is not None else [{"id": 1, "slice_name": "C"}])
        cl.client.export_zip.return_value = _zipbuf(zip_files or self.DEFAULT_ZIP)
        filters = MagicMock()
        filters.search = None
        # Make get_assets_folder return tmp_path by default unless overridden by CLI arg
        ctx = _ctx(assets_folder=str(tmp_path))

        with patch(_CLI, **{"from_context.return_value": cl}), patch(_CTX, return_value=ctx), patch(
            _DSP, return_value=cm
        ), patch(_PARSE, return_value=filters), patch(_CON):
            return runner.invoke(app, ["pull"] + (args_extra or []))

    def test_success(self, tmp_path):
        assert self._invoke(tmp_path).exit_code == 0

    def test_creates_dir(self, tmp_path):
        new = tmp_path / "new"
        # Override assets_folder to point to new dir
        cm, sp = _sp()
        cl = _client(charts=[{"id": 1}])
        cl.client.export_zip.return_value = _zipbuf(self.DEFAULT_ZIP)
        filters = MagicMock()
        filters.search = None
        ctx = _ctx(assets_folder=str(new))
        with patch(_CLI, **{"from_context.return_value": cl}), patch(_CTX, return_value=ctx), patch(
            _DSP, return_value=cm
        ), patch(_PARSE, return_value=filters), patch(_CON):
            r = runner.invoke(app, ["pull"])
        assert r.exit_code == 0
        assert new.exists()

    def test_not_dir(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("x")
        cm, sp = _sp()
        cl = _client()
        filters = MagicMock()
        filters.search = None
        ctx = _ctx(assets_folder=str(f))
        with patch(_CLI, **{"from_context.return_value": cl}), patch(_CTX, return_value=ctx), patch(
            _DSP, return_value=cm
        ), patch(_PARSE, return_value=filters), patch(_CON):
            r = runner.invoke(app, ["pull"])
        assert r.exit_code == 1

    def test_no_charts(self, tmp_path):
        assert self._invoke(tmp_path, charts=[]).exit_code == 0

    def test_skip_deps(self, tmp_path):
        assert self._invoke(tmp_path, ["--skip-dependencies"]).exit_code == 0

    def test_exists_no_overwrite(self, tmp_path):
        d = tmp_path / "charts"
        d.mkdir()
        (d / "chart_1.yaml").write_text("old")
        assert self._invoke(tmp_path).exit_code == 0

    def test_exists_overwrite(self, tmp_path):
        d = tmp_path / "charts"
        d.mkdir()
        (d / "chart_1.yaml").write_text("old")
        assert self._invoke(tmp_path, ["--overwrite"]).exit_code == 0

    def test_disable_jinja(self, tmp_path):
        assert self._invoke(tmp_path, ["--disable-jinja-escaping"]).exit_code == 0

    def test_yaml_error(self, tmp_path):
        z = {"bundle/charts/bad.yaml": "{{{\nnot: valid: yaml: ["}
        assert self._invoke(tmp_path, zip_files=z).exit_code == 0

    def test_unix_eol(self, tmp_path):
        assert self._invoke(tmp_path, ["--force-unix-eol"]).exit_code == 0

    def test_porcelain(self, tmp_path):
        assert self._invoke(tmp_path, ["--porcelain"]).exit_code == 0

    def test_jinja_templates(self, tmp_path):
        z = {"bundle/charts/c.yaml": "sql: '{{ var }}'\nname: test\n"}
        assert self._invoke(tmp_path, zip_files=z).exit_code == 0

    def test_nested_structures(self, tmp_path):
        z = {"bundle/charts/c.yaml": "items:\n  - name: '{{ x }}'\n    count: 5\n"}
        assert self._invoke(tmp_path, zip_files=z).exit_code == 0

    def test_porcelain_file_exists_no_overwrite(self, tmp_path):
        """Branch 1054->1059: porcelain with file exists and no overwrite."""
        d = tmp_path / "charts"
        d.mkdir()
        (d / "chart_1.yaml").write_text("old")
        assert self._invoke(tmp_path, ["--porcelain"]).exit_code == 0

    def test_spinner_none(self, tmp_path):
        """Branch 1015->992: spinner returns None."""
        cm = MagicMock()
        cm.__enter__ = MagicMock(return_value=None)
        cm.__exit__ = MagicMock(return_value=False)
        cl = _client(charts=[{"id": 1}])
        cl.client.export_zip.return_value = _zipbuf(self.DEFAULT_ZIP)
        filters = MagicMock()
        filters.search = None
        ctx = _ctx(assets_folder=str(tmp_path))
        with patch(_CLI, **{"from_context.return_value": cl}), patch(_CTX, return_value=ctx), patch(
            _DSP, return_value=cm
        ), patch(_PARSE, return_value=filters), patch(_CON):
            r = runner.invoke(app, ["pull"])
        assert r.exit_code == 0

    def test_error(self):
        with patch(_CTX, side_effect=RuntimeError("boom")), patch(_CON):
            assert runner.invoke(app, ["pull"]).exit_code == 1

    def test_error_porcelain(self):
        with patch(_CTX, side_effect=RuntimeError("boom")), patch(_CON):
            assert runner.invoke(app, ["pull", "--porcelain"]).exit_code == 1

    def test_export_error_porcelain(self, tmp_path):
        """Branch 1092->1097: porcelain pull error inside try block."""
        cm, sp = _sp()
        cl = _client(charts=[{"id": 1}])
        cl.client.export_zip.side_effect = RuntimeError("export fail")
        filters = MagicMock()
        filters.search = None
        ctx = _ctx(assets_folder=str(tmp_path))
        with patch(_CLI, **{"from_context.return_value": cl}), patch(_CTX, return_value=ctx), patch(
            _DSP, return_value=cm
        ), patch(_PARSE, return_value=filters), patch(_CON):
            r = runner.invoke(app, ["pull", "--porcelain"])
        assert r.exit_code == 1


# ===================================================================
# push_charts
# ===================================================================


class TestPushCharts:
    def _invoke(
        self,
        tmp_path,
        args_extra=None,
        ctx_mock=None,
        workspaces=None,
        confirm=True,
        native_effect=None,
    ):
        ct = ctx_mock or _ctx(assets_folder=str(tmp_path))
        ws = (
            workspaces
            if workspaces is not None
            else [
                {"id": 2, "hostname": "target.preset.io"},
                {"id": 1, "hostname": "source.preset.io"},
            ]
        )
        pcl = MagicMock()
        pcl.get_all_workspaces.return_value = ws

        with patch(_CTX, return_value=ct), patch(_NATIVE) as mn, patch(
            _PAUTH, **{"from_sup_config.return_value": MagicMock()}
        ), patch(_PCLI, **{"from_context.return_value": pcl}), patch(
            "typer.confirm", return_value=confirm
        ), patch(_CON):
            if native_effect:
                mn.side_effect = native_effect
            return runner.invoke(app, ["push"] + (args_extra or []))

    def test_success(self, tmp_path):
        assert self._invoke(tmp_path, ["--force"]).exit_code == 0

    def test_not_exist(self, tmp_path):
        ct = _ctx(assets_folder=str(tmp_path / "nope"))
        assert self._invoke(tmp_path, ["--force"], ctx_mock=ct).exit_code == 1

    def test_not_dir(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_text("x")
        ct = _ctx(assets_folder=str(f))
        assert self._invoke(tmp_path, ["--force"], ctx_mock=ct).exit_code == 1

    def test_no_source(self, tmp_path):
        ct = _ctx(workspace_id=None, assets_folder=str(tmp_path))
        assert self._invoke(tmp_path, ["--force"], ctx_mock=ct).exit_code == 1

    def test_no_target(self, tmp_path):
        ct = _ctx(target_workspace_id=None, assets_folder=str(tmp_path))
        assert self._invoke(tmp_path, ["--force"], ctx_mock=ct).exit_code == 1

    def test_decline(self, tmp_path):
        assert self._invoke(tmp_path, confirm=False).exit_code == 0

    def test_cross_workspace(self, tmp_path):
        ct = _ctx(workspace_id=1, target_workspace_id=2, assets_folder=str(tmp_path))
        assert self._invoke(tmp_path, ctx_mock=ct, confirm=True).exit_code == 0

    def test_same_workspace(self, tmp_path):
        ct = _ctx(workspace_id=1, target_workspace_id=1, assets_folder=str(tmp_path))
        assert (
            self._invoke(
                tmp_path, ctx_mock=ct, confirm=True, workspaces=[{"id": 1, "hostname": "s.io"}]
            ).exit_code
            == 0
        )

    def test_target_not_found(self, tmp_path):
        assert self._invoke(tmp_path, ["--force"], workspaces=[]).exit_code == 1

    def test_no_hostname(self, tmp_path):
        assert (
            self._invoke(tmp_path, ["--force"], workspaces=[{"id": 2, "hostname": None}]).exit_code
            == 1
        )

    def test_exception(self, tmp_path):
        assert self._invoke(tmp_path, ["--force"], native_effect=RuntimeError("k")).exit_code == 1

    def test_typer_exit(self, tmp_path):
        import typer as _t

        assert self._invoke(tmp_path, ["--force"], native_effect=_t.Exit(1)).exit_code == 1

    def test_porcelain_force(self, tmp_path):
        assert self._invoke(tmp_path, ["--porcelain", "--force"]).exit_code == 0

    def test_porcelain_error(self, tmp_path):
        ct = _ctx(workspace_id=None, assets_folder=str(tmp_path))
        assert self._invoke(tmp_path, ["--porcelain", "--force"], ctx_mock=ct).exit_code == 1

    def test_target_found_after_non_matching(self, tmp_path):
        """Branch 1279->1278: loop iterates past non-matching workspace."""
        ws = [{"id": 999, "hostname": "other.io"}, {"id": 2, "hostname": "target.io"}]
        assert self._invoke(tmp_path, ["--force"], workspaces=ws).exit_code == 0

    def test_porcelain_native_error(self, tmp_path):
        """Branch 1348->1353: porcelain with native() exception."""
        assert (
            self._invoke(
                tmp_path,
                ["--porcelain", "--force"],
                native_effect=RuntimeError("import failed"),
            ).exit_code
            == 1
        )
