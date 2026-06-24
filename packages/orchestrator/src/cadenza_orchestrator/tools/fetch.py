"""Page fetch — Firecrawl `/v2/scrape` returning LLM-ready markdown.

Returns the page as a `FetchedPage` of UNTRUSTED content (CLAUDE.md §9). The
injection guard (Unit 4) screens `.content` before any agent uses it.
"""

from __future__ import annotations

import httpx

from .types import FetchedPage, ToolError


class FirecrawlFetcher:
    name = "firecrawl"

    def __init__(
        self,
        api_key: str,
        *,
        http: httpx.Client | None = None,
        base_url: str = "https://api.firecrawl.dev",
        timeout: float = 30.0,
    ) -> None:
        self._key = api_key
        self._http = http or httpx.Client(timeout=timeout)
        self._base = base_url.rstrip("/")

    def fetch(self, url: str) -> FetchedPage:
        try:
            resp = self._http.post(
                f"{self._base}/v2/scrape",
                headers={"Authorization": f"Bearer {self._key}"},
                json={"url": url, "formats": ["markdown"], "only_main_content": True},
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as ex:
            raise ToolError(
                "firecrawl",
                f"scrape failed ({ex.response.status_code})",
                status_code=ex.response.status_code,
            ) from ex
        except httpx.HTTPError as ex:
            raise ToolError("firecrawl", f"request error: {ex}") from ex

        body = resp.json()
        if body.get("success") is False:
            raise ToolError("firecrawl", "scrape unsuccessful")

        data = body.get("data") or {}
        meta = data.get("metadata") or {}
        return FetchedPage(
            url=meta.get("sourceURL", url),
            title=meta.get("title", ""),
            content=data.get("markdown", ""),
            status_code=int(meta.get("statusCode") or 200),
        )
