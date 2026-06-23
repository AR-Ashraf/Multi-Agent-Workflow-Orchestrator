"""Cadenza agents — Planner / Researcher / Analyst / Writer / Critic.

Each agent is a LangGraph node function. In this (mocked-LLM) unit the agents
construct deterministic structured outputs; the LLM client is exercised for token
accounting and is the seam where real provider parsing will plug in.
"""

from ._base import ctx_from

__all__ = ["ctx_from"]
