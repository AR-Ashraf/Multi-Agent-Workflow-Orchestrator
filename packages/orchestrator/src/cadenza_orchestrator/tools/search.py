"""Web search adapters — Tavily + Brave behind one `SearchClient` interface.

The HTTP client is injectable so tests drive real request-building + response
parsing offline via `httpx.MockTransport` (no network in CI). API keys here are
OUR server-side keys (the visitor's BYOK key is only for the LLM, never tools).
"""

from __future__ import annotations

import httpx

from .types import SearchResult, ToolError


class TavilySearchClient:
    name = "tavily"

    def __init__(
        self,
        api_key: str,
        *,
        http: httpx.Client | None = None,
        base_url: str = "https://api.tavily.com",
        timeout: float = 20.0,
    ) -> None:
        self._key = api_key
        self._http = http or httpx.Client(timeout=timeout)
        self._base = base_url.rstrip("/")

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        try:
            resp = self._http.post(
                f"{self._base}/search",
                headers={"Authorization": f"Bearer {self._key}"},
                json={"query": query, "search_depth": "basic", "max_results": max_results},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as ex:
            raise ToolError(
                "tavily",
                f"search failed ({ex.response.status_code})",
                status_code=ex.response.status_code,
            ) from ex
        except httpx.HTTPError as ex:
            raise ToolError("tavily", f"request error: {ex}") from ex

        data = resp.json()
        return [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("content", ""),
                score=float(item.get("score") or 0.0),
            )
            for item in data.get("results", [])
        ]


class BraveSearchClient:
    name = "brave"

    def __init__(
        self,
        api_key: str,
        *,
        http: httpx.Client | None = None,
        base_url: str = "https://api.search.brave.com",
        timeout: float = 20.0,
    ) -> None:
        self._key = api_key
        self._http = http or httpx.Client(timeout=timeout)
        self._base = base_url.rstrip("/")

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        try:
            resp = self._http.get(
                f"{self._base}/res/v1/web/search",
                headers={"X-Subscription-Token": self._key, "Accept": "application/json"},
                params={"q": query, "count": max_results},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as ex:
            raise ToolError(
                "brave",
                f"search failed ({ex.response.status_code})",
                status_code=ex.response.status_code,
            ) from ex
        except httpx.HTTPError as ex:
            raise ToolError("brave", f"request error: {ex}") from ex

        data = resp.json()
        results = (data.get("web") or {}).get("results", [])
        return [
            SearchResult(
                title=item.get("title", ""),
                url=item.get("url", ""),
                snippet=item.get("description", ""),
            )
            for item in results
        ]


def make_search_client(provider: str, api_key: str, *, http: httpx.Client | None = None):
    """Factory: 'tavily' | 'brave'."""
    p = provider.lower()
    if p == "tavily":
        return TavilySearchClient(api_key, http=http)
    if p == "brave":
        return BraveSearchClient(api_key, http=http)
    raise ToolError("search", f"unknown search provider: {provider}")
