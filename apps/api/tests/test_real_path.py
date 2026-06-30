"""Real-adapter plumbing (Unit 13) — with real_llm_enabled the gateway builds the
real provider + tool clients and guards unsupported providers. No network: we
only assert admission decisions and client construction (httpx is lazy)."""

from __future__ import annotations

from _helpers import make_client
from cadenza_orchestrator.llm import AnthropicClient, OpenAIClient
from cadenza_orchestrator.tools import FirecrawlFetcher, TavilySearchClient

from cadenza_api.runs import Admission
from cadenza_api.schemas import StartRunRequest

DENTAL = "Market for AI scheduling assistants for US dental clinics"


async def test_keyed_anthropic_run_is_admitted_live():
    async with make_client(real_llm_enabled=True) as (client, _):
        r = await client.post(
            "/api/runs",
            json={"query": DENTAL, "provider": "anthropic", "api_key": "sk-ant-abc123456"},
        )
        body = r.json()
        assert body["mode"] == "live" and body["run_id"]


async def test_unsupported_provider_with_key_falls_back_to_demo():
    async with make_client(real_llm_enabled=True) as (client, _):
        r = await client.post(
            "/api/runs",
            json={"query": DENTAL, "provider": "google", "api_key": "AIzaSyABC1234567890"},
        )
        body = r.json()
        assert body["mode"] == "demo"
        assert body["reason"] == "provider_unsupported"
        assert body["run_id"] is None


async def test_build_llm_picks_the_real_client_per_provider():
    async with make_client(real_llm_enabled=True) as (_, manager):
        live = Admission("live", "visitor")
        a = manager._build_llm(
            StartRunRequest(query=DENTAL, provider="anthropic", api_key="sk-ant-x12345678"), live
        )
        o = manager._build_llm(
            StartRunRequest(query=DENTAL, provider="openai", api_key="sk-x12345678"), live
        )
        assert isinstance(a, AnthropicClient)
        assert isinstance(o, OpenAIClient)


async def test_build_tools_uses_real_clients_when_keys_present():
    async with make_client(
        real_llm_enabled=True, tavily_api_key="tvly-x", firecrawl_api_key="fc-x"
    ) as (_, manager):
        search, fetch = manager._build_tools()
        assert isinstance(search, TavilySearchClient)
        assert isinstance(fetch, FirecrawlFetcher)


async def test_tools_fall_back_to_fixtures_without_keys():
    async with make_client(real_llm_enabled=True) as (_, manager):
        assert manager._build_tools() == (None, None)


async def test_mock_graph_when_real_llm_disabled():
    async with make_client(real_llm_enabled=False, tavily_api_key="tvly-x") as (_, manager):
        assert manager._build_tools() == (None, None)
        llm = manager._build_llm(
            StartRunRequest(query=DENTAL, provider="anthropic", api_key="sk-ant-x12345678"),
            Admission("live", "visitor"),
        )
        assert llm is None  # → RunSession uses the mock client
