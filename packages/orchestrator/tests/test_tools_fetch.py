"""Firecrawl fetch adapter tests — offline via httpx.MockTransport."""

from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from cadenza_orchestrator.tools import FirecrawlFetcher, ToolError


def _client(handler: Callable[[httpx.Request], httpx.Response]) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_firecrawl_builds_request_and_parses_markdown():
    def handler(req: httpx.Request) -> httpx.Response:
        assert req.method == "POST"
        assert req.url.path == "/v2/scrape"
        assert req.headers["authorization"] == "Bearer fc-test"
        body = json.loads(req.content)
        assert body["url"] == "https://site.test"
        assert "markdown" in body["formats"]
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "markdown": "# Hello",
                    "metadata": {
                        "title": "Hello",
                        "sourceURL": "https://site.test",
                        "statusCode": 200,
                    },
                },
            },
        )

    page = FirecrawlFetcher("fc-test", http=_client(handler)).fetch("https://site.test")
    assert page.title == "Hello"
    assert page.content == "# Hello"
    assert page.url == "https://site.test"
    assert page.status_code == 200


def test_firecrawl_raises_on_http_500():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": "boom"})

    with pytest.raises(ToolError) as ei:
        FirecrawlFetcher("fc", http=_client(handler)).fetch("https://x.test")
    assert ei.value.status_code == 500
    assert ei.value.provider == "firecrawl"


def test_firecrawl_raises_when_success_false():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"success": False})

    with pytest.raises(ToolError):
        FirecrawlFetcher("fc", http=_client(handler)).fetch("https://x.test")
