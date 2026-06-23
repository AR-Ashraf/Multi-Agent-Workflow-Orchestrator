"""Provider-agnostic LLM client layer (CLAUDE.md §5: "model routing is intentional").

One interface; adapters per provider arrive in a later unit. For the mocked graph
we ship `MockLLMClient` so the whole orchestration is testable without live LLM
calls or any API key (CLAUDE.md §7).

BYOK note (CLAUDE.md §5/§6): a real adapter receives the visitor's key per-run
only and never persists or logs it. The mock holds no key at all.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable


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
