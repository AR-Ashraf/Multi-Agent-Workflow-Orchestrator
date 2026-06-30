"""The eval set — sample research questions scored by the harness (CLAUDE.md §7).

Kept small and deterministic. Until real LLM synthesis lands, queries without a
dedicated fixture fall back to the default brief; they still exercise the full
graph (plan → research → HITL → write → verify → output) and its structural
guarantees.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class EvalCase:
    id: str
    query: str


EVAL_CASES: list[EvalCase] = [
    EvalCase("dental", "Market for AI scheduling assistants for US dental clinics"),
    EvalCase("ecommerce", "Competitive landscape for AI customer-support agents in e-commerce"),
    EvalCase("accounting", "Demand for AI invoice-processing automation for SMB accounting firms"),
]
