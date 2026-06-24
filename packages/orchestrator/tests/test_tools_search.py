"""Web-search adapter tests — real request-building + parsing, offline via
httpx.MockTransport (no network in CI). CLAUDE.md §7."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from cadenza_orchestrator.tools import (
    BraveSearchClient,
    TavilySearchClient,
    ToolError,
    make_search_client,
)


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_tavily_builds_request_and_parses_results():
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "POST"
        assert req.url.path == "/search"
        assert req.headers["authorization"] == "Bearer tvly-test"
        body = json.loads(req.content)
        assert body == {"query": "dental market", "search_depth": "basic", "max_results": 2}
        return httpx.Response(
            200,
            json={
                "results": [
                    {"title": "A", "url": "https://a.test", "content": "snippet a", "score": 0.9},
                    {"title": "B", "url": "https://b.test", "content": "snippet b", "score": 0.5},
                ]
            },
        )

    results = TavilySearchClient("tvly-test", http=_client(handler)).search(
        "dental market", max_results=2
    )
    assert [r.url for r in results] == ["https://a.test", "https://b.test"]
    assert results[0].snippet == "snippet a"
    assert results[0].score == 0.9


def test_tavily_raises_tool_error_on_401():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "bad key"})

    with pytest.raises(ToolError) as ei:
        TavilySearchClient("bad", http=_client(handler)).search("q")
    assert ei.value.status_code == 401
    assert ei.value.provider == "tavily"


def test_brave_builds_request_and_parses_results():
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "GET"
        assert req.url.path == "/res/v1/web/search"
        assert req.headers["x-subscription-token"] == "brave-key"
        assert req.url.params["q"] == "ai agents"
        return httpx.Response(
            200,
            json={
                "web": {"results": [{"title": "T", "url": "https://t.test", "description": "desc"}]}
            },
        )

    results = BraveSearchClient("brave-key", http=_client(handler)).search(
        "ai agents", max_results=5
    )
    assert results[0].url == "https://t.test"
    assert results[0].snippet == "desc"


def test_make_search_client_rejects_unknown_provider():
    with pytest.raises(ToolError):
        make_search_client("duckduckgo", "k")
