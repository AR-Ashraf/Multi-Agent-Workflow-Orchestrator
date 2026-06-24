"""Tools — web search + Firecrawl page fetch wrappers (CLAUDE.md §12 step 4).

Real adapters (Tavily/Brave/Firecrawl) plus offline fixture clients for the
mocked graph and tests. All tool output is untrusted and will pass the injection
guard (Unit 4) before any agent reasons over it (CLAUDE.md §9).
"""

from .fetch import FirecrawlFetcher
from .fixtures import (
    INJECTION_MARKER,
    POISONED_URL,
    FixtureFetcher,
    FixtureSearchClient,
)
from .search import BraveSearchClient, TavilySearchClient, make_search_client
from .types import (
    FetchedPage,
    SearchClient,
    SearchResult,
    ToolError,
    WebFetcher,
)

__all__ = [
    "INJECTION_MARKER",
    "POISONED_URL",
    "BraveSearchClient",
    "FetchedPage",
    "FirecrawlFetcher",
    "FixtureFetcher",
    "FixtureSearchClient",
    "SearchClient",
    "SearchResult",
    "TavilySearchClient",
    "ToolError",
    "WebFetcher",
    "make_search_client",
]
