"""Tool result types + client protocols.

All tool output is UNTRUSTED data (CLAUDE.md §9). These types just carry the
fetched content; the injection guard (Unit 4) screens it before any agent reasons
over it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


class ToolError(Exception):
    """Raised when a search/fetch tool fails (bad key, quota, network, parse)."""

    def __init__(self, provider: str, message: str, *, status_code: int | None = None) -> None:
        super().__init__(f"[{provider}] {message}")
        self.provider = provider
        self.status_code = status_code


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""
    score: float = 0.0


@dataclass(frozen=True)
class FetchedPage:
    url: str
    title: str
    content: str
    status_code: int = 200


@runtime_checkable
class SearchClient(Protocol):
    name: str

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]: ...


@runtime_checkable
class WebFetcher(Protocol):
    name: str

    def fetch(self, url: str) -> FetchedPage: ...
