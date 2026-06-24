"""Offline fixture tool clients — deterministic + carry a poisoned page for the
injection guard (Unit 4)."""

from __future__ import annotations

from cadenza_orchestrator.tools import (
    INJECTION_MARKER,
    POISONED_URL,
    FixtureFetcher,
    FixtureSearchClient,
)


def test_fixture_search_top_competitors_first_result_is_poisoned():
    results = FixtureSearchClient().search("top competitors", max_results=6)
    assert results[0].url == POISONED_URL
    assert len(results) == 5


def test_fixture_search_respects_max_results():
    assert len(FixtureSearchClient().search("market size", max_results=2)) == 2


def test_fixture_fetch_distinguishes_poisoned_from_clean():
    fetcher = FixtureFetcher()
    poisoned = fetcher.fetch(POISONED_URL)
    assert INJECTION_MARKER in poisoned.content
    clean = fetcher.fetch("https://example.test/market-size/1")
    assert INJECTION_MARKER not in clean.content
