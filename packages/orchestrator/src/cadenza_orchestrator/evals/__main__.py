"""`uv run python -m cadenza_orchestrator.evals` — run the eval set, print the
JSON report, and exit non-zero if any case regresses below threshold (§7)."""

from __future__ import annotations

from .harness import run_evals

report = run_evals()
raise SystemExit(0 if report["summary"]["all_passed"] else 1)
