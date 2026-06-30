"""Real LLM adapter tests (Unit 13) — request shape, response/usage parsing, and
error mapping for Anthropic + OpenAI, all offline via httpx.MockTransport (no
network, no keys). The BYOK key only ever lives in the request headers."""

from __future__ import annotations

import json

import httpx
import pytest

from cadenza_orchestrator.constants import api_model_id
from cadenza_orchestrator.llm import (
    AnthropicClient,
    LLMError,
    OpenAIClient,
    make_llm_client,
    parse_json,
)


def _client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def test_anthropic_complete_builds_request_and_parses_usage():
    seen: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"] = str(req.url)
        seen["key"] = req.headers.get("x-api-key")
        seen["version"] = req.headers.get("anthropic-version")
        seen["body"] = json.loads(req.content)
        return httpx.Response(
            200,
            json={
                "content": [{"type": "text", "text": "hello "}, {"type": "text", "text": "world"}],
                "usage": {"input_tokens": 11, "output_tokens": 7},
            },
        )

    client = AnthropicClient("sk-ant-secret", http=_client(handler))
    res = client.complete(
        system="You are X.", prompt="Q?", model="claude-sonnet-4-6", max_tokens=50
    )

    assert res.text == "hello world"
    assert (res.input_tokens, res.output_tokens, res.total_tokens) == (11, 7, 18)
    assert seen["url"].endswith("/v1/messages")
    assert seen["key"] == "sk-ant-secret" and seen["version"] == "2023-06-01"
    assert seen["body"]["system"] == "You are X."
    assert seen["body"]["messages"][0] == {"role": "user", "content": "Q?"}
    assert seen["body"]["max_tokens"] == 50


def test_openai_complete_builds_request_and_parses_usage():
    seen: dict = {}

    def handler(req: httpx.Request) -> httpx.Response:
        seen["url"] = str(req.url)
        seen["auth"] = req.headers.get("authorization")
        seen["body"] = json.loads(req.content)
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": "hi there"}}],
                "usage": {"prompt_tokens": 4, "completion_tokens": 2},
            },
        )

    client = OpenAIClient("sk-openai", http=_client(handler))
    res = client.complete(system="S", prompt="P", model="gpt-5", max_tokens=10)

    assert res.text == "hi there"
    assert (res.input_tokens, res.output_tokens) == (4, 2)
    assert seen["url"].endswith("/v1/chat/completions")
    assert seen["auth"] == "Bearer sk-openai"
    assert seen["body"]["messages"] == [
        {"role": "system", "content": "S"},
        {"role": "user", "content": "P"},
    ]
    assert seen["body"]["max_completion_tokens"] == 10


def test_http_error_becomes_llmerror_with_status():
    def handler(_req: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": "invalid key"})

    client = AnthropicClient("bad-key", http=_client(handler))
    with pytest.raises(LLMError) as ex:
        client.complete(system="", prompt="x", model="m")
    assert ex.value.status_code == 401
    assert ex.value.provider == "anthropic"


def test_factory_selects_provider_and_rejects_unknown():
    assert make_llm_client("anthropic", "k").provider == "anthropic"
    assert make_llm_client("openai", "k").provider == "openai"
    with pytest.raises(LLMError):
        make_llm_client("groq", "k")  # not real yet


def test_parse_json_tolerates_fences_and_prose():
    assert parse_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert parse_json("Sure, here you go:\n[1, 2, 3]") == [1, 2, 3]
    with pytest.raises(LLMError):
        parse_json("definitely not json")


def test_api_model_id_maps_registry_ids_to_real_ones():
    assert api_model_id("anthropic", "claude-sonnet") == "claude-sonnet-4-6"
    assert api_model_id("anthropic", "claude-sonnet", fast=True) == "claude-haiku-4-5-20251001"
    assert api_model_id("openai", "gpt-5") == "gpt-5"
    assert api_model_id("openai", "gpt-5", fast=True) == "gpt-5-mini"
    assert api_model_id("anthropic", "some-future-model") == "some-future-model"  # passthrough
