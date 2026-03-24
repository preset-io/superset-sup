"""Tests for sup.commands.chart_dry - DRY refactored chart commands.

The decorated commands use functools.wraps which copies the original signature
containing custom types. We call __wrapped__.__wrapped__ to access the original
function directly, bypassing the decorator wrappers.
"""

from unittest.mock import MagicMock, patch

import click.exceptions
import pytest

from sup.config.settings import OutputOptions
from sup.filters.base import UniversalFilters

# Patch targets at source modules (lazy imports)
CTX = "sup.config.settings.SupContext"
CLIENT = "sup.clients.superset.SupSupersetClient"
SPINNER = "sup.output.spinners.data_spinner"

SAMPLE_CHARTS = [
    {
        "id": 1,
        "slice_name": "Revenue Chart",
        "viz_type": "bar",
        "datasource_name": "sales",
        "datasource_id": 100,
        "dashboards": [{"id": 10}],
    },
    {
        "id": 2,
        "slice_name": "User Growth",
        "viz_type": "line",
        "datasource_name": "users",
        "datasource_id": 200,
        "dashboards": [{"id": 20}],
    },
]


def _make_spinner_cm(sp_obj=None):
    cm = MagicMock()
    obj = sp_obj or MagicMock()
    cm.__enter__ = MagicMock(return_value=obj)
    cm.__exit__ = MagicMock(return_value=False)
    return cm, obj


def _filters(**overrides):
    defaults = dict(
        id=None, ids=None, name=None, search=None, mine=False,
        team_id=None, created_after=None, modified_after=None,
        limit=None, offset=None, page=None, page_size=None,
        order=None, desc=False,
    )
    defaults.update(overrides)
    return UniversalFilters(**defaults)


def _output(**overrides):
    defaults = dict(json_output=False, yaml_output=False, porcelain=False, workspace_id=None)
    defaults.update(overrides)
    return OutputOptions(**defaults)


def _get_list_charts():
    from sup.commands.chart_dry import list_charts
    return list_charts.__wrapped__.__wrapped__


def _get_chart_info():
    from sup.commands.chart_dry import chart_info
    return chart_info.__wrapped__


# ---- list_charts ----


@patch("sup.commands.chart_dry.display_entity_results")
@patch("sup.commands.chart_dry.apply_chart_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_default(mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display):
    cm, sp = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    ctx = MagicMock()
    ctx.get_workspace_hostname.return_value = "ws.preset.io"
    mock_ctx_cls.return_value = ctx
    client = MagicMock()
    client.get_charts.return_value = SAMPLE_CHARTS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = SAMPLE_CHARTS

    _get_list_charts()(filters=_filters(), output=_output())
    mock_display.assert_called_once()
    assert "showing" in sp.text


@patch("sup.commands.chart_dry.display_entity_results")
@patch("sup.commands.chart_dry.apply_chart_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_porcelain(mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_charts.return_value = SAMPLE_CHARTS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = SAMPLE_CHARTS

    _get_list_charts()(filters=_filters(), output=_output(porcelain=True))
    mock_data_spinner.assert_called_once_with("charts", silent=True)
    assert mock_display.call_args[1]["porcelain"] is True


@patch("sup.commands.chart_dry.display_entity_results")
@patch("sup.commands.chart_dry.apply_chart_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_json(mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_charts.return_value = SAMPLE_CHARTS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = SAMPLE_CHARTS

    _get_list_charts()(filters=_filters(), output=_output(json_output=True))
    assert mock_display.call_args[1]["output_format"] == "json"


@patch("sup.commands.chart_dry.display_entity_results")
@patch("sup.commands.chart_dry.apply_chart_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_yaml(mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_charts.return_value = SAMPLE_CHARTS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = SAMPLE_CHARTS

    _get_list_charts()(filters=_filters(), output=_output(yaml_output=True))
    assert mock_display.call_args[1]["output_format"] == "yaml"


@patch("sup.commands.chart_dry.display_entity_results")
@patch("sup.commands.chart_dry.apply_chart_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_workspace_id(mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    ctx = MagicMock()
    mock_ctx_cls.return_value = ctx
    client = MagicMock()
    client.get_charts.return_value = []
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = []

    _get_list_charts()(filters=_filters(), output=_output(workspace_id=42))
    mock_client_cls.from_context.assert_called_once_with(ctx, 42)


@patch("sup.commands.chart_dry.display_entity_results")
@patch("sup.commands.chart_dry.apply_chart_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_chart_specific_filters(mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_charts.return_value = SAMPLE_CHARTS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = [SAMPLE_CHARTS[0]]

    _get_list_charts()(
        filters=_filters(), output=_output(),
        dashboard_id=10, viz_type="bar", dataset_id=100,
    )
    cf = mock_apply.call_args[0][1]
    assert cf.dashboard_id == 10
    assert cf.viz_type == "bar"
    assert cf.dataset_id == 100


@patch("sup.commands.chart_dry.display_entity_results")
@patch("sup.commands.chart_dry.apply_chart_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_universal_filters(mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_charts.return_value = SAMPLE_CHARTS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = SAMPLE_CHARTS

    _get_list_charts()(
        filters=_filters(mine=True, limit=10, name="Revenue*", id=1),
        output=_output(),
    )
    cf = mock_apply.call_args[0][1]
    assert cf.mine is True
    assert cf.limit == 10
    assert cf.name == "Revenue*"
    assert cf.id == 1


@patch("sup.commands.chart_dry.display_entity_results")
@patch("sup.commands.chart_dry.apply_chart_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_page_filter(mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_charts.return_value = []
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = []

    _get_list_charts()(filters=_filters(page=3), output=_output())
    client.get_charts.assert_called_once_with(silent=True, limit=None, page=2)


@patch("sup.commands.chart_dry.display_entity_results")
@patch("sup.commands.chart_dry.apply_chart_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_no_page_defaults_zero(mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_charts.return_value = []
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = []

    _get_list_charts()(filters=_filters(), output=_output())
    client.get_charts.assert_called_once_with(silent=True, limit=None, page=0)


@patch("sup.commands.chart_dry.display_entity_results")
@patch("sup.commands.chart_dry.apply_chart_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_table_display_func(mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    ctx = MagicMock()
    ctx.get_workspace_hostname.return_value = "host.io"
    mock_ctx_cls.return_value = ctx
    client = MagicMock()
    client.get_charts.return_value = SAMPLE_CHARTS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = SAMPLE_CHARTS

    with patch("sup.commands.chart_dry.display_charts_table") as mock_charts_table:
        _get_list_charts()(filters=_filters(), output=_output())
        table_func = mock_display.call_args[1]["table_display_func"]
        table_func(SAMPLE_CHARTS)
        mock_charts_table.assert_called_once_with(SAMPLE_CHARTS, "host.io")



@patch("sup.commands.chart_dry.display_entity_results")
@patch("sup.commands.chart_dry.apply_chart_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_spinner_silent_none(mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display):
    """When sp is None (porcelain/silent), `if sp:` branch is skipped."""
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=None)
    cm.__exit__ = MagicMock(return_value=False)
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_charts.return_value = SAMPLE_CHARTS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = SAMPLE_CHARTS

    _get_list_charts()(filters=_filters(), output=_output(porcelain=True))
    mock_display.assert_called_once()

@patch(CTX)
def test_list_error_no_porcelain(mock_ctx_cls):
    mock_ctx_cls.side_effect = RuntimeError("boom")
    with patch("sup.commands.chart_dry.console") as mock_console:
        with pytest.raises(click.exceptions.Exit):
            _get_list_charts()(filters=_filters(), output=_output())
        assert any("Failed to list charts" in str(c) for c in mock_console.print.call_args_list)


@patch(CTX)
def test_list_error_with_porcelain(mock_ctx_cls):
    mock_ctx_cls.side_effect = RuntimeError("boom")
    with patch("sup.commands.chart_dry.console") as mock_console:
        with pytest.raises(click.exceptions.Exit):
            _get_list_charts()(filters=_filters(), output=_output(porcelain=True))
        mock_console.print.assert_not_called()


# ---- chart_info ----


@patch("sup.commands.chart.display_chart_details")
@patch(CLIENT)
@patch(CTX)
def test_info_default(mock_ctx_cls, mock_client_cls, mock_display):
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    chart_data = {"id": 1, "slice_name": "Rev", "viz_type": "bar"}
    client.get_chart.return_value = chart_data
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.chart_dry.console"):
        _get_chart_info()(chart_id=1, output=_output())
    mock_display.assert_called_once_with(chart_data)


@patch(CLIENT)
@patch(CTX)
def test_info_porcelain(mock_ctx_cls, mock_client_cls):
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_chart.return_value = {"id": 5, "slice_name": "My Chart", "viz_type": "pie"}
    mock_client_cls.from_context.return_value = client

    with patch("builtins.print") as mock_print:
        _get_chart_info()(chart_id=5, output=_output(porcelain=True))
    mock_print.assert_called_once_with("5\tMy Chart\tpie")


@patch(CLIENT)
@patch(CTX)
def test_info_json(mock_ctx_cls, mock_client_cls):
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_chart.return_value = {"id": 1, "slice_name": "C1", "viz_type": "table"}
    mock_client_cls.from_context.return_value = client

    with patch("builtins.print") as mock_print, patch("sup.commands.chart_dry.console"):
        _get_chart_info()(chart_id=1, output=_output(json_output=True))
    assert '"slice_name"' in mock_print.call_args[0][0]


@patch(CLIENT)
@patch(CTX)
def test_info_workspace_id(mock_ctx_cls, mock_client_cls):
    ctx = MagicMock()
    mock_ctx_cls.return_value = ctx
    client = MagicMock()
    client.get_chart.return_value = {"id": 1, "slice_name": "X", "viz_type": "bar"}
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.chart.display_chart_details"), \
         patch("sup.commands.chart_dry.console"):
        _get_chart_info()(chart_id=1, output=_output(workspace_id=77))
    mock_client_cls.from_context.assert_called_once_with(ctx, 77)


@patch(CTX)
def test_info_error_no_porcelain(mock_ctx_cls):
    mock_ctx_cls.side_effect = RuntimeError("not found")
    with patch("sup.commands.chart_dry.console") as mock_console:
        with pytest.raises(click.exceptions.Exit):
            _get_chart_info()(chart_id=999, output=_output())
        assert any("Failed to get chart info" in str(c) for c in mock_console.print.call_args_list)


@patch(CTX)
def test_info_error_with_porcelain(mock_ctx_cls):
    mock_ctx_cls.side_effect = RuntimeError("not found")
    with patch("sup.commands.chart_dry.console") as mock_console:
        with pytest.raises(click.exceptions.Exit):
            _get_chart_info()(chart_id=999, output=_output(porcelain=True))
        mock_console.print.assert_not_called()


@patch(CLIENT)
@patch(CTX)
def test_info_loading_message(mock_ctx_cls, mock_client_cls):
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_chart.return_value = {"id": 1, "slice_name": "X", "viz_type": "bar"}
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.chart.display_chart_details"), \
         patch("sup.commands.chart_dry.console") as mock_console:
        _get_chart_info()(chart_id=1, output=_output())
    assert any("Loading chart 1" in str(c) for c in mock_console.print.call_args_list)
