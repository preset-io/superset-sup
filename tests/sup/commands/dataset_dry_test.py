"""Tests for sup.commands.dataset_dry - DRY refactored dataset commands.

Uses __wrapped__ to bypass decorator wrappers and test original functions directly.
"""

from unittest.mock import MagicMock, patch

import click.exceptions
import pytest

from sup.config.settings import OutputOptions
from sup.filters.base import UniversalFilters

CTX = "sup.config.settings.SupContext"
CLIENT = "sup.clients.superset.SupSupersetClient"
SPINNER = "sup.output.spinners.data_spinner"

SAMPLE_DATASETS = [
    {
        "id": 1,
        "table_name": "sales",
        "database_name": "main_db",
        "schema": "analytics",
        "kind": "physical",
        "database": {"id": 10},
        "sql": "",
    },
    {
        "id": 2,
        "table_name": "users",
        "database_name": "stats_db",
        "schema": "public",
        "kind": "virtual",
        "database": {"id": 20},
        "sql": "SELECT * FROM raw_users",
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
        id=None,
        ids=None,
        name=None,
        search=None,
        mine=False,
        team_id=None,
        created_after=None,
        modified_after=None,
        limit=None,
        offset=None,
        page=None,
        page_size=None,
        order=None,
        desc=False,
    )
    defaults.update(overrides)
    return UniversalFilters(**defaults)


def _output(**overrides):
    defaults = dict(json_output=False, yaml_output=False, porcelain=False, workspace_id=None)
    defaults.update(overrides)
    return OutputOptions(**defaults)


def _get_list_datasets():
    from sup.commands.dataset_dry import list_datasets

    return list_datasets.__wrapped__.__wrapped__


def _get_dataset_info():
    from sup.commands.dataset_dry import dataset_info

    return dataset_info.__wrapped__


def _get_export_dataset():
    from sup.commands.dataset_dry import export_dataset

    return export_dataset.__wrapped__.__wrapped__


# ---- list_datasets ----


@patch("sup.commands.dataset_dry.display_entity_results")
@patch("sup.commands.dataset_dry.apply_dataset_filters")
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
    client.get_datasets.return_value = SAMPLE_DATASETS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = SAMPLE_DATASETS

    _get_list_datasets()(filters=_filters(), output=_output())
    mock_display.assert_called_once()
    assert sp.text == f"Found {len(SAMPLE_DATASETS)} datasets"


@patch("sup.commands.dataset_dry.display_entity_results")
@patch("sup.commands.dataset_dry.apply_dataset_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_filtered_spinner(
    mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display
):
    cm, sp = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_datasets.return_value = SAMPLE_DATASETS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = [SAMPLE_DATASETS[0]]

    _get_list_datasets()(filters=_filters(), output=_output())
    assert "showing 1 after filtering" in sp.text


@patch("sup.commands.dataset_dry.display_entity_results")
@patch("sup.commands.dataset_dry.apply_dataset_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_porcelain(mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_datasets.return_value = SAMPLE_DATASETS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = SAMPLE_DATASETS

    _get_list_datasets()(filters=_filters(), output=_output(porcelain=True))
    mock_data_spinner.assert_called_once_with("datasets", silent=True)
    assert mock_display.call_args[1]["porcelain"] is True


@patch("sup.commands.dataset_dry.display_entity_results")
@patch("sup.commands.dataset_dry.apply_dataset_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_json(mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_datasets.return_value = []
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = []

    _get_list_datasets()(filters=_filters(), output=_output(json_output=True))
    assert mock_display.call_args[1]["output_format"] == "json"


@patch("sup.commands.dataset_dry.display_entity_results")
@patch("sup.commands.dataset_dry.apply_dataset_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_yaml(mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_datasets.return_value = []
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = []

    _get_list_datasets()(filters=_filters(), output=_output(yaml_output=True))
    assert mock_display.call_args[1]["output_format"] == "yaml"


@patch("sup.commands.dataset_dry.display_entity_results")
@patch("sup.commands.dataset_dry.apply_dataset_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_workspace_id(
    mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display
):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    ctx = MagicMock()
    mock_ctx_cls.return_value = ctx
    client = MagicMock()
    client.get_datasets.return_value = []
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = []

    _get_list_datasets()(filters=_filters(), output=_output(workspace_id=55))
    mock_client_cls.from_context.assert_called_once_with(ctx, 55)


@patch("sup.commands.dataset_dry.display_entity_results")
@patch("sup.commands.dataset_dry.apply_dataset_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_dataset_specific_filters(
    mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display
):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_datasets.return_value = SAMPLE_DATASETS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = [SAMPLE_DATASETS[0]]

    _get_list_datasets()(
        filters=_filters(),
        output=_output(),
        database_id=10,
        schema="analytics",
        table_type="view",
    )
    df = mock_apply.call_args[0][1]
    assert df.database_id == 10
    assert df.schema == "analytics"
    assert df.table_type == "view"


@patch("sup.commands.dataset_dry.display_entity_results")
@patch("sup.commands.dataset_dry.apply_dataset_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_universal_filters(
    mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display
):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_datasets.return_value = SAMPLE_DATASETS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = SAMPLE_DATASETS

    _get_list_datasets()(
        filters=_filters(mine=True, limit=25, name="sales*", id=1),
        output=_output(),
    )
    df = mock_apply.call_args[0][1]
    assert df.mine is True
    assert df.limit == 25
    assert df.name == "sales*"
    assert df.id == 1


@patch("sup.commands.dataset_dry.display_entity_results")
@patch("sup.commands.dataset_dry.apply_dataset_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_page_filter(
    mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display
):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_datasets.return_value = []
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = []

    _get_list_datasets()(filters=_filters(page=5), output=_output())
    client.get_datasets.assert_called_once_with(silent=True, limit=None, page=4)


@patch("sup.commands.dataset_dry.display_entity_results")
@patch("sup.commands.dataset_dry.apply_dataset_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_no_page_defaults_zero(
    mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display
):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_datasets.return_value = []
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = []

    _get_list_datasets()(filters=_filters(), output=_output())
    client.get_datasets.assert_called_once_with(silent=True, limit=None, page=0)


@patch("sup.commands.dataset_dry.display_entity_results")
@patch("sup.commands.dataset_dry.apply_dataset_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_table_display_func(
    mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display
):
    cm, _ = _make_spinner_cm()
    mock_data_spinner.return_value = cm
    ctx = MagicMock()
    ctx.get_workspace_hostname.return_value = "host.io"
    mock_ctx_cls.return_value = ctx
    client = MagicMock()
    client.get_datasets.return_value = SAMPLE_DATASETS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = SAMPLE_DATASETS

    with patch("sup.commands.dataset_dry.display_datasets_table") as mock_ds_table:
        _get_list_datasets()(filters=_filters(), output=_output())
        table_func = mock_display.call_args[1]["table_display_func"]
        table_func(SAMPLE_DATASETS)
        mock_ds_table.assert_called_once_with(SAMPLE_DATASETS, "host.io")


@patch("sup.commands.dataset_dry.display_entity_results")
@patch("sup.commands.dataset_dry.apply_dataset_filters")
@patch(SPINNER)
@patch(CLIENT)
@patch(CTX)
def test_list_spinner_silent_none(
    mock_ctx_cls, mock_client_cls, mock_data_spinner, mock_apply, mock_display
):
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=None)
    cm.__exit__ = MagicMock(return_value=False)
    mock_data_spinner.return_value = cm
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_datasets.return_value = SAMPLE_DATASETS
    mock_client_cls.from_context.return_value = client
    mock_apply.return_value = SAMPLE_DATASETS

    _get_list_datasets()(filters=_filters(), output=_output(porcelain=True))


@patch(CTX)
def test_list_error_no_porcelain(mock_ctx_cls):
    mock_ctx_cls.side_effect = RuntimeError("boom")
    with patch("sup.commands.dataset_dry.console") as mock_console:
        with pytest.raises(click.exceptions.Exit):
            _get_list_datasets()(filters=_filters(), output=_output())
        assert any("Failed to list datasets" in str(c) for c in mock_console.print.call_args_list)


@patch(CTX)
def test_list_error_with_porcelain(mock_ctx_cls):
    mock_ctx_cls.side_effect = RuntimeError("boom")
    with patch("sup.commands.dataset_dry.console") as mock_console:
        with pytest.raises(click.exceptions.Exit):
            _get_list_datasets()(filters=_filters(), output=_output(porcelain=True))
        mock_console.print.assert_not_called()


# ---- dataset_info ----


@patch("sup.commands.dataset.display_dataset_details")
@patch(CLIENT)
@patch(CTX)
def test_info_default(mock_ctx_cls, mock_client_cls, mock_display):
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    ds = {"id": 1, "table_name": "sales", "database_name": "db"}
    client.get_dataset.return_value = ds
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.dataset_dry.console"):
        _get_dataset_info()(dataset_id=1, output=_output())
    mock_display.assert_called_once_with(ds)


@patch(CLIENT)
@patch(CTX)
def test_info_porcelain(mock_ctx_cls, mock_client_cls):
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_dataset.return_value = {"id": 7, "table_name": "orders", "database_name": "prod"}
    mock_client_cls.from_context.return_value = client

    with patch("builtins.print") as mock_print:
        _get_dataset_info()(dataset_id=7, output=_output(porcelain=True))
    mock_print.assert_called_once_with("7\torders\tprod")


@patch(CLIENT)
@patch(CTX)
def test_info_json(mock_ctx_cls, mock_client_cls):
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_dataset.return_value = {"id": 1, "table_name": "t1"}
    mock_client_cls.from_context.return_value = client

    with patch("builtins.print") as mock_print, patch("sup.commands.dataset_dry.console"):
        _get_dataset_info()(dataset_id=1, output=_output(json_output=True))
    assert '"table_name"' in mock_print.call_args[0][0]


@patch(CLIENT)
@patch(CTX)
def test_info_workspace_id(mock_ctx_cls, mock_client_cls):
    ctx = MagicMock()
    mock_ctx_cls.return_value = ctx
    client = MagicMock()
    client.get_dataset.return_value = {"id": 1, "table_name": "t", "database_name": "d"}
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.dataset.display_dataset_details"), patch(
        "sup.commands.dataset_dry.console"
    ):
        _get_dataset_info()(dataset_id=1, output=_output(workspace_id=88))
    mock_client_cls.from_context.assert_called_once_with(ctx, 88)


@patch(CTX)
def test_info_error_no_porcelain(mock_ctx_cls):
    mock_ctx_cls.side_effect = RuntimeError("not found")
    with patch("sup.commands.dataset_dry.console") as mock_console:
        with pytest.raises(click.exceptions.Exit):
            _get_dataset_info()(dataset_id=999, output=_output())
        assert any(
            "Failed to get dataset info" in str(c) for c in mock_console.print.call_args_list
        )


@patch(CTX)
def test_info_error_with_porcelain(mock_ctx_cls):
    mock_ctx_cls.side_effect = RuntimeError("not found")
    with patch("sup.commands.dataset_dry.console") as mock_console:
        with pytest.raises(click.exceptions.Exit):
            _get_dataset_info()(dataset_id=999, output=_output(porcelain=True))
        mock_console.print.assert_not_called()


@patch(CLIENT)
@patch(CTX)
def test_info_loading_message(mock_ctx_cls, mock_client_cls):
    mock_ctx_cls.return_value = MagicMock()
    client = MagicMock()
    client.get_dataset.return_value = {"id": 1, "table_name": "t", "database_name": "d"}
    mock_client_cls.from_context.return_value = client

    with patch("sup.commands.dataset.display_dataset_details"), patch(
        "sup.commands.dataset_dry.console"
    ) as mock_console:
        _get_dataset_info()(dataset_id=1, output=_output())
    assert any("Loading dataset 1" in str(c) for c in mock_console.print.call_args_list)


# ---- export_dataset ----


def test_export_not_yet_implemented():
    with patch("sup.commands.dataset_dry.console") as mock_console:
        _get_export_dataset()(filters=_filters(), output=_output())
    assert any("not yet implemented" in str(c) for c in mock_console.print.call_args_list)


def test_export_with_options():
    with patch("sup.commands.dataset_dry.console") as mock_console:
        _get_export_dataset()(
            filters=_filters(),
            output=_output(),
            folder="/tmp/out",
            overwrite=True,
            dry_run=True,
        )
    assert any("not yet implemented" in str(c) for c in mock_console.print.call_args_list)
