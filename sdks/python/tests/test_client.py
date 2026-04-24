"""Smoke tests for the CozyMemory Python SDK."""
from __future__ import annotations

import pytest
from pytest_httpx import HTTPXMock

from cozymemory import AuthError, CozyMemoryClient


def test_add_conversation(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="http://test/api/v1/conversations",
        method="POST",
        json={"success": True, "data": [], "total": 0},
    )
    with CozyMemoryClient(api_key="k", base_url="http://test") as c:
        r = c.conversations.add(
            user_id="alice",
            messages=[{"role": "user", "content": "hi"}],
        )
    assert r["success"] is True


def test_auth_error(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="http://test/api/v1/health",
        status_code=401,
        json={"detail": "bad key"},
    )
    with CozyMemoryClient(api_key="bad", base_url="http://test") as c:
        with pytest.raises(AuthError):
            c.health()


def test_sends_api_key_header(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="http://test/api/v1/health",
        method="GET",
        json={"status": "ok"},
    )
    with CozyMemoryClient(api_key="secret-key", base_url="http://test") as c:
        c.health()
    req = httpx_mock.get_request()
    assert req is not None
    assert req.headers["X-Cozy-API-Key"] == "secret-key"


def test_search_posts_body(httpx_mock: HTTPXMock) -> None:
    httpx_mock.add_response(
        url="http://test/api/v1/conversations/search",
        method="POST",
        json={"results": []},
    )
    with CozyMemoryClient(api_key="k", base_url="http://test") as c:
        c.conversations.search(user_id="alice", query="hiking", limit=5)
    req = httpx_mock.get_request()
    assert req is not None
    import json as _json

    body = _json.loads(req.content)
    assert body == {"user_id": "alice", "query": "hiking", "limit": 5}
