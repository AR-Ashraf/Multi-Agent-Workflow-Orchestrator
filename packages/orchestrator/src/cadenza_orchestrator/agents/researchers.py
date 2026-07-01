"""Researchers A/B/C — parallel web search + page read, screened (CLAUDE.md §4, §9).

Each Researcher runs a real search (`ctx.search`) and fetches candidate pages
(`ctx.fetch`). EVERY fetched page passes through the injection guard before its
content is used: a blocked page is quarantined and the Researcher falls back to
the next clean result; a sanitized page is cleaned and kept.

On the real path the query comes from the Planner's sub-question and the screened
page content + title are carried forward (so the Analyst/Writer can synthesize +
cite real sources). On the mock path the offline fixtures drive the same flow —
Researcher B's top result is a poisoned page, so the guard really fires on it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from langchain_core.runnables import RunnableConfig

from ..guard import screen_content
from ..state import ResearchState
from ._base import ctx_from, is_real, truncate

# node_id -> (subtask label, human-readable search query)  [mock-path defaults]
_RESEARCH: dict[str, tuple[str, str]] = {
    "researcher-a": ("market size", "US dental practices count + no-show cost"),
    "researcher-b": ("top competitors", "AI scheduling competitors dental"),
    "researcher-c": ("pricing signals", "AI scheduling pricing dental"),
}
_INDEX: dict[str, int] = {"researcher-a": 0, "researcher-b": 1, "researcher-c": 2}


def make_researcher(node_id: str) -> Callable[[ResearchState, RunnableConfig], dict[str, Any]]:
    label_default, query_text = _RESEARCH[node_id]
    idx = _INDEX[node_id]
    who = "Researcher " + node_id.rsplit("-", 1)[1].upper()

    def researcher(state: ResearchState, config: RunnableConfig) -> dict[str, Any]:
        ctx = ctx_from(config)
        ctx.step()
        e = ctx.emitter
        real = is_real(ctx)

        subtasks = state.get("subtasks", [])
        subtask = subtasks[idx] if real and idx < len(subtasks) else label_default
        search_q = f"{subtask} {ctx.query}".strip() if real else label_default
        display_q = subtask if real else query_text

        e.edge_status(f"planner->{node_id}", "done")
        e.node_status(node_id, "active")

        results = ctx.search.search(search_q, max_results=6)
        e.log("info", who, f'web search "{display_q}" → reading {len(results)} pages.', node_id)
        ctx.charge(
            ctx.llm.complete(system="Researcher", prompt=subtask, model=ctx.api_model_for(node_id))
        )

        chosen_url: str | None = None
        chosen_title = ""
        safe_content = ""
        blocked_any = False

        for result in results:
            page = ctx.fetch.fetch(result.url)  # UNTRUSTED until screened
            verdict = screen_content(page.content, source_url=page.url)

            if verdict.status == "blocked":
                blocked_any = True
                e.node_status(node_id, "blocked")
                e.injection_screened(node_id, "blocked", verdict.reason, source_url=page.url)
                snippet = verdict.matched[0] if verdict.matched else "hidden instructions"
                e.log(
                    "security",
                    "Injection guard",
                    f'{who} fetched a page with embedded instructions: "{snippet}".',
                    node_id,
                )
                e.log(
                    "security",
                    "Injection guard",
                    "classified as prompt-injection → page quarantined, never fed to the model. Run continues safely.",
                    node_id,
                )
                ctx.charge(
                    ctx.llm.complete(
                        system="Researcher",
                        prompt="re-read clean pages",
                        model=ctx.api_model_for(node_id),
                    )
                )
                e.node_status(node_id, "active")
                continue  # fall back to the next (clean) result

            if verdict.status == "sanitized":
                e.injection_screened(node_id, "sanitized", verdict.reason, source_url=page.url)
                e.log(
                    "security",
                    "Injection guard",
                    f"{who}: stripped suspicious lines from a page; kept the rest.",
                    node_id,
                )

            chosen_url = page.url
            chosen_title = page.title or result.title
            safe_content = verdict.safe_content
            break

        if blocked_any:
            e.log(
                "info", who, "re-read clean pages from other sources → findings recovered.", node_id
            )

        e.node_status(node_id, "done")
        e.edge_status(f"{node_id}->analyst", "flow")

        finding: dict[str, Any] = {
            "node": node_id,
            "subtask": subtask if real else label_default,
            "source": chosen_url or "about:blank",
            "safe_chars": len(safe_content),
        }
        if real:  # carry real content/title forward only on the live path
            finding["title"] = chosen_title
            finding["content"] = truncate(safe_content)
            finding["blocked"] = blocked_any
        return {"findings": [finding]}

    researcher.__name__ = f"researcher_{node_id.rsplit('-', 1)[1]}"
    return researcher
