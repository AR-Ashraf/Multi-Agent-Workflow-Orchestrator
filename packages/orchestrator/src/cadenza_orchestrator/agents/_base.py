"""Shared helper for agent nodes."""

from __future__ import annotations

from typing import TYPE_CHECKING

from langchain_core.runnables import RunnableConfig

if TYPE_CHECKING:
    from ..context import RunContext


def ctx_from(config: RunnableConfig) -> RunContext:
    """Pull the per-run RunContext threaded through the LangGraph config."""
    return config["configurable"]["ctx"]  # type: ignore[index,typeddict-item]
