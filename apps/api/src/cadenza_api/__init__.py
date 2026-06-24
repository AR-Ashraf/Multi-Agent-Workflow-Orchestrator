"""Cadenza FastAPI gateway — a thin caller of the orchestrator (CLAUDE.md §5).

REST endpoints start/resume a run; an SSE endpoint streams the orchestrator's
events to the browser via Redis pub/sub. The visitor's BYOK key is handled
per-run only and never persisted or logged.
"""
