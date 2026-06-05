"""Tests for SupSupersetClient.get_datasets server-side filtering & pagination."""

from contextlib import contextmanager
from unittest.mock import MagicMock, patch

import prison
from yarl import URL

from sup.clients.superset import SupSupersetClient


def _make_client(pages):
    """Build a SupSupersetClient whose session.get returns the given pages in order.

    ``pages`` is a list of result-lists; each call to session.get pops the next one.
    """
    client = SupSupersetClient.__new__(SupSupersetClient)  # bypass __init__/auth
    inner = MagicMock()
    inner.baseurl = URL("http://superset.test/")

    responses = []
    for page in pages:
        resp = MagicMock()
        resp.json.return_value = {"result": page}
        resp.status_code = 200
        responses.append(resp)
    inner.session.get.side_effect = responses
    client.client = inner
    return client, inner


def _query_of(call):
    """Extract and decode the prison-encoded ``q`` from a session.get call's URL."""
    url = call.args[0]
    return prison.loads(str(url).split("q=", 1)[1])


def test_single_page_by_default():
    """Without fetch_all, only one request is made and limit drives page_size."""
    client, inner = _make_client([[{"id": 1}, {"id": 2}]])

    result = client.get_datasets(silent=True, limit=25)

    assert [d["id"] for d in result] == [1, 2]
    assert inner.session.get.call_count == 1
    q = _query_of(inner.session.get.call_args)
    assert q["page_size"] == 25
    assert q["filters"] == []


def test_fetch_all_paginates_until_empty():
    """With fetch_all, it keeps requesting pages until the API returns none."""
    client, inner = _make_client([[{"id": 1}], [{"id": 2}], []])

    result = client.get_datasets(silent=True, fetch_all=True)

    assert [d["id"] for d in result] == [1, 2]
    # 2 full pages + 1 empty page that stops the loop
    assert inner.session.get.call_count == 3
    first_q = _query_of(inner.session.get.call_args_list[0])
    assert first_q["page_size"] == 100  # MAX_PAGE_SIZE
    assert first_q["page"] == 0
    assert _query_of(inner.session.get.call_args_list[1])["page"] == 1


def test_filters_and_text_search_combined():
    """Caller filters and text_search are both sent server-side."""
    client, inner = _make_client([[{"id": 3}], []])

    client.get_datasets(
        silent=True,
        filters=[{"col": "id", "opr": "eq", "value": 3}],
        text_search="sales",
        fetch_all=True,
    )

    q = _query_of(inner.session.get.call_args_list[0])
    assert {"col": "id", "opr": "eq", "value": 3} in q["filters"]
    assert {"col": "table_name", "opr": "ct", "value": "sales"} in q["filters"]


def test_error_returns_empty_list():
    """A failing request yields an empty list rather than raising."""
    client = SupSupersetClient.__new__(SupSupersetClient)
    inner = MagicMock()
    inner.baseurl = URL("http://superset.test/")
    inner.session.get.side_effect = RuntimeError("boom")
    client.client = inner

    assert client.get_datasets(silent=True) == []


def _ctx_for_from_context(current_workspace_id):
    """A SupContext mock for from_context with no cached hostname.

    The active workspace is ``current_workspace_id`` and the hostname cache is
    empty, forcing from_context to resolve the hostname via the Preset API.
    """
    ctx = MagicMock()
    ctx.get_workspace_id.return_value = current_workspace_id
    ctx.get_workspace_hostname.return_value = None
    return ctx


@contextmanager
def _patched_from_context(workspaces):
    """Patch the Preset/auth/client collaborators from_context resolves through.

    ``workspaces`` is the list returned by get_all_workspaces (the hostname
    resolution source).
    """
    preset_client = MagicMock()
    preset_client.get_all_workspaces.return_value = workspaces

    with patch(
        "sup.clients.preset.SupPresetClient.from_context",
        return_value=preset_client,
    ), patch(
        "sup.clients.superset.SupPresetAuth.from_sup_config",
        return_value=MagicMock(),
    ), patch(
        "sup.clients.superset.SupersetClient",
        return_value=MagicMock(),
    ):
        yield


def test_from_context_scoped_workspace_id_does_not_persist():
    """A --workspace-id filter pointing elsewhere must not touch state.yml.

    Regression: passing a workspace id as a filter used to overwrite the
    persistent current workspace via set_workspace_context.
    """
    ctx = _ctx_for_from_context(current_workspace_id=100)

    with _patched_from_context([{"id": 200, "hostname": "ws200.example.com"}]):
        client = SupSupersetClient.from_context(ctx, workspace_id=200)

    assert client.workspace_url == "https://ws200.example.com/"
    ctx.set_workspace_context.assert_not_called()


def test_from_context_default_workspace_caches_hostname():
    """Without an explicit id, the active workspace's hostname is cached."""
    ctx = _ctx_for_from_context(current_workspace_id=100)

    with _patched_from_context([{"id": 100, "hostname": "ws100.example.com"}]):
        client = SupSupersetClient.from_context(ctx)

    assert client.workspace_url == "https://ws100.example.com/"
    ctx.set_workspace_context.assert_called_once_with(
        100,
        hostname="ws100.example.com",
    )


def test_from_context_explicit_active_workspace_id_caches_hostname():
    """An explicit id equal to the active workspace still warms the cache.

    Callers such as `sup sql` pre-resolve the workspace id and pass it
    positionally even with no --workspace-id flag; that path must keep caching
    the active workspace's hostname rather than re-hitting the Preset API.
    """
    ctx = _ctx_for_from_context(current_workspace_id=100)

    with _patched_from_context([{"id": 100, "hostname": "ws100.example.com"}]):
        client = SupSupersetClient.from_context(ctx, workspace_id=100)

    assert client.workspace_url == "https://ws100.example.com/"
    ctx.set_workspace_context.assert_called_once_with(
        100,
        hostname="ws100.example.com",
    )
