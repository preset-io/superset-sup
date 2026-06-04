"""Tests for SupSupersetClient.get_datasets server-side filtering & pagination."""

from unittest.mock import MagicMock

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
