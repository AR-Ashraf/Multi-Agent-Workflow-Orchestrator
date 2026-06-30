"""Provider-agnostic LLM client layer (CLAUDE.md §5: "model routing is intentional").

One interface; adapters per provider arrive in a later unit. For the mocked graph
we ship `MockLLMClient` so the whole orchestration is testable without live LLM
calls or any API key (CLAUDE.md §7).

BYOK note (CLAUDE.md §5/§6): a real adapter receives the visitor's key per-run
only and never persists or logs it. The mock holds no key at all.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import httpx


class LLMError(Exception):
    """Raised when a provider call fails (bad key, quota, network, parse)."""

    def __init__(self, provider: str, message: str, *, status_code: int | None = None) -> None:
        super().__init__(f"[{provider}] {message}")
        self.provider = provider
        self.status_code = status_code


@dataclass(frozen=True)
class LLMResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@runtime_checkable
class LLMClient(Protocol):
    provider: str

    def complete(
        self, *, system: str, prompt: str, model: str, max_tokens: int = 1024
    ) -> LLMResult: ...


_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def parse_json(text: str) -> Any:
    """Best-effort structured-output parse: tolerate ```json fences and prose
    around the JSON body. Raises LLMError if nothing parseable is found."""
    candidate = text.strip()
    fenced = _FENCE.search(candidate)
    if fenced:
        candidate = fenced.group(1).strip()
    else:
        start = min([i for i in (candidate.find("{"), candidate.find("[")) if i != -1] or [-1])
        if start > 0:
            candidate = candidate[start:]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError as ex:
        raise LLMError("parse", f"model did not return valid JSON: {ex}") from ex


class MockLLMClient:
    """Deterministic, network-free LLM stand-in.

    Token counts are derived from input size so meters move realistically; the
    returned text is a marker (agents in the mocked graph construct their own
    structured outputs — the seam where real parsing will plug in).
    """

    provider = "mock"

    def __init__(self, fixed_output_tokens: int = 96) -> None:
        self._out = fixed_output_tokens

    def complete(
        self, *, system: str, prompt: str, model: str, max_tokens: int = 1024
    ) -> LLMResult:
        input_tokens = max(1, (len(system) + len(prompt)) // 4)
        output_tokens = min(self._out, max_tokens)
        return LLMResult(
            text=f"[mock:{model}] ok",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


class AnthropicClient:
    """Real Claude adapter (BYOK). The visitor's key is used per-request only and
    never stored or logged. HTTP client is injectable for offline tests."""

    provider = "anthropic"

    def __init__(
        self,
        api_key: str,
        *,
        http: httpx.Client | None = None,
        base_url: str = "https://api.anthropic.com",
        timeout: float = 60.0,
    ) -> None:
        self._key = api_key
        self._http = http or httpx.Client(timeout=timeout)
        self._base = base_url.rstrip("/")

    def complete(
        self, *, system: str, prompt: str, model: str, max_tokens: int = 1024
    ) -> LLMResult:
        try:
            resp = self._http.post(
                f"{self._base}/v1/messages",
                headers={
                    "x-api-key": self._key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "max_tokens": max_tokens,
                    "system": system,
                    "messages": [{"role": "user", "content": prompt}],
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as ex:
            raise LLMError(
                "anthropic",
                f"request failed ({ex.response.status_code})",
                status_code=ex.response.status_code,
            ) from ex
        except httpx.HTTPError as ex:
            raise LLMError("anthropic", f"request error: {ex}") from ex

        data = resp.json()
        text = "".join(
            b.get("text", "") for b in data.get("content", []) if b.get("type") == "text"
        )
        usage = data.get("usage") or {}
        return LLMResult(
            text=text,
            input_tokens=int(usage.get("input_tokens", 0)),
            output_tokens=int(usage.get("output_tokens", 0)),
        )


class OpenAIClient:
    """Real OpenAI adapter (BYOK) via Chat Completions. Used per-request only;
    the key is never stored or logged. HTTP client is injectable for tests."""

    provider = "openai"

    def __init__(
        self,
        api_key: str,
        *,
        http: httpx.Client | None = None,
        base_url: str = "https://api.openai.com",
        timeout: float = 60.0,
    ) -> None:
        self._key = api_key
        self._http = http or httpx.Client(timeout=timeout)
        self._base = base_url.rstrip("/")

    def complete(
        self, *, system: str, prompt: str, model: str, max_tokens: int = 1024
    ) -> LLMResult:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        try:
            resp = self._http.post(
                f"{self._base}/v1/chat/completions",
                headers={
                    "authorization": f"Bearer {self._key}",
                    "content-type": "application/json",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_completion_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
        except httpx.HTTPStatusError as ex:
            raise LLMError(
                "openai",
                f"request failed ({ex.response.status_code})",
                status_code=ex.response.status_code,
            ) from ex
        except httpx.HTTPError as ex:
            raise LLMError("openai", f"request error: {ex}") from ex

        data = resp.json()
        choices = data.get("choices") or [{}]
        text = (choices[0].get("message") or {}).get("content") or ""
        usage = data.get("usage") or {}
        return LLMResult(
            text=text,
            input_tokens=int(usage.get("prompt_tokens", 0)),
            output_tokens=int(usage.get("completion_tokens", 0)),
        )


def make_llm_client(provider: str, api_key: str, *, http: httpx.Client | None = None) -> LLMClient:
    """Factory: build the real BYOK client for a provider. 'anthropic' | 'openai'."""
    p = provider.lower()
    if p == "anthropic":
        return AnthropicClient(api_key, http=http)
    if p == "openai":
        return OpenAIClient(api_key, http=http)
    raise LLMError(provider, f"no real adapter for provider '{provider}' yet")
