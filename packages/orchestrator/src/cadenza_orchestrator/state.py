"""Graph state — the LangGraph `StateGraph` schema.

`findings` uses an additive reducer so the three Researchers (which run as a
parallel superstep) can each append without a write conflict, and the Analyst
reads the merged list. Everything else is written by a single node.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any, Required, TypedDict


class ResearchState(TypedDict, total=False):
    # inputs (always supplied when the graph is invoked)
    query: Required[str]

    # planner → researchers
    subtasks: list[str]

    # researchers → analyst (parallel fan-in via additive reducer)
    findings: Annotated[list[dict[str, Any]], operator.add]

    # analyst → hitl
    insights: str
    direction: list[str]
    # analyst → writer/critic/output (real path): numbered, citable sources
    sources: list[dict[str, Any]]

    # hitl → writer
    hitl_decision: str
    hitl_note: str

    # writer → critic
    draft: dict[str, Any]

    # critic loop
    critic_attempts: int
    claims: list[dict[str, Any]]
    verdict: str  # "accept" | "retry"
    failed_claims: list[str]  # claim ids the Critic flagged as unsupported
    claims_verified: dict[str, int]  # critic → output: verified/total count

    # terminal
    brief: dict[str, Any]
