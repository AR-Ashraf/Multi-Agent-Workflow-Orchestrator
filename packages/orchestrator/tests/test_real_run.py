"""Real-path graph test (Unit 13, Stage C) — drives the whole graph with a real
(provider != mock) LLM whose structured outputs are scripted, plus scripted
web search/fetch. Proves the agents actually USE the model's output: the brief's
sections come from the Writer, sources are the fetched pages, and the Critic
grounds each claim against the real source text. No network."""

from __future__ import annotations

import json

from cadenza_orchestrator import RunSession
from cadenza_orchestrator.llm import LLMResult
from cadenza_orchestrator.tools import FetchedPage, SearchResult

QUERY = "Market for AI invoice automation for SMB accounting firms"


class ScriptedLLM:
    """A 'real' client (provider != mock) returning canned structured output by
    agent (routed on the system prompt). Source-grounded values are exact quotes."""

    provider = "anthropic"

    def complete(
        self, *, system: str, prompt: str, model: str, max_tokens: int = 1024
    ) -> LLMResult:
        return LLMResult(text=self._route(system), input_tokens=12, output_tokens=24)

    def _route(self, system: str) -> str:
        if system.startswith("You are the Planner"):
            return '["market size", "competitors", "pricing"]'
        if system.startswith("You are the Analyst"):
            return json.dumps(
                {
                    "insights": "Mid-market accounting firms are underserved.",
                    "direction": ["Size the US market", "Profile 3 rivals", "Name the gap"],
                }
            )
        if "revising a draft" in system or system.startswith("You are the Writer"):
            return json.dumps(
                {
                    "sections": [
                        {"heading": "Market opportunity", "body": "Large TAM [Source 1]."},
                        {"heading": "Competitive landscape", "body": "Priced plans [Source 2]."},
                        {
                            "heading": "Where Devs Core could win",
                            "body": "Exception gap [Source 3].",
                        },
                    ],
                    "claims": [
                        {
                            "id": "c1",
                            "text": "firm count",
                            "source_id": "Source 1",
                            "value": "1.4 million firms",
                        },
                        {
                            "id": "c2",
                            "text": "pricing",
                            "source_id": "Source 2",
                            "value": "$200 per month",
                        },
                        {
                            "id": "c3",
                            "text": "manual time",
                            "source_id": "Source 3",
                            "value": "30% of staff time",
                        },
                    ],
                }
            )
        return "ok"  # researcher / critic metering calls


_CONTENT = {
    "market size": "There are about 1.4 million firms doing bookkeeping in the US.",
    "competitors": "Incumbent AP tools charge roughly $200 per month per firm.",
    "pricing": "Manual data entry eats around 30% of staff time at small firms.",
}


class ScriptedSearch:
    name = "scripted"

    def search(self, query: str, *, max_results: int = 5) -> list[SearchResult]:
        return [
            SearchResult(title=f"{query} — page", url=f"https://ex.test/?q={query}", snippet="")
        ]


class ScriptedFetch:
    name = "scripted"

    def fetch(self, url: str) -> FetchedPage:
        content = next((v for k, v in _CONTENT.items() if k in url), "Generic context.")
        return FetchedPage(url=url, title="Source page", content=content)


def _run() -> list[dict]:
    session = RunSession(
        run_id="real1",
        query=QUERY,
        provider="anthropic",
        model_id="claude-sonnet",
        routing=True,
        mode="live",
        llm=ScriptedLLM(),
        search=ScriptedSearch(),
        fetch=ScriptedFetch(),
    )
    assert session.start() is True  # pauses at HITL
    session.resume("approve")
    assert session.completed and not session.errored
    return session.events


def _last(events, type_):
    return next(e for e in reversed(events) if e["type"] == type_)


def test_real_run_uses_model_drafted_brief_and_grounds_claims():
    events = _run()
    brief = _last(events, "brief.released")["brief"]

    # The brief is the model's draft — not the dental fixture.
    assert brief["title"].startswith(QUERY)
    assert [s["heading"] for s in brief["sections"]] == [
        "Market opportunity",
        "Competitive landscape",
        "Where Devs Core could win",
    ]
    assert "Large TAM [Source 1]." == brief["sections"][0]["body"]
    assert len(brief["sources"]) == 3
    assert brief["sources"][0]["url"].startswith("https://ex.test/")
    assert brief["claimsVerified"] == {"verified": 3, "total": 3}
    assert brief["permalink"] == "cadenza.devs-core.com/run/real1"


def test_real_run_verifies_every_claim_against_its_fetched_source():
    events = _run()
    claims = [e for e in events if e["type"] == "claim.verified"]
    assert len(claims) == 3
    assert all(c["verdict"] == "grounded" for c in claims)
    assert _last(events, "run.completed")["claimsVerified"] == {"verified": 3, "total": 3}


def test_real_run_planner_subtasks_came_from_the_model():
    events = _run()
    rationale = next(
        e for e in events if e["type"] == "agent.rationale" and e["agentId"] == "planner"
    )
    assert rationale["items"] == ["market size", "competitors", "pricing"]
