"""Cadenza eval harness (CLAUDE.md §7).

A small, deterministic quality gate over the research graph: it runs each eval
case end-to-end (mocked LLM) and scores the output on citation coverage, claim
grounding, and format validity. Runs on demand / nightly — not in the blocking
PR gate — and is the seam where an LLM-as-judge + Langfuse sink land later.

    uv run python -m cadenza_orchestrator.evals
"""

from .dataset import EVAL_CASES, EvalCase
from .harness import CaseScore, run_evals

__all__ = ["EVAL_CASES", "EvalCase", "CaseScore", "run_evals"]
