# Multi-Agent Workflow Orchestrator

A public, interactive demo where a visitor can trigger a **real multi-agent workflow**
and watch AI agents collaborate live — Devs Core's flagship showcase that we build
production-grade *agentic* systems (orchestration, human-in-the-loop, error recovery),
not no-code automations.

> **Status:** Project scaffold only. No application logic yet. See [`CLAUDE.md`](./CLAUDE.md)
> for the full architecture, conventions, build order, and cost/safety rules.

## Flagship workflow — "AI Market Research Brief"

```
Planner ─▶ parallel Researchers (web search + Firecrawl) ─▶ Analyst
   └─▶ [ human approval checkpoint ] ─▶ Writer ─▶ Critic (QA / retry)
        └─▶ downloadable, cited brief + shareable run permalink
```

The same engine later powers secondary workflows (outreach draft, content outline).

## Tech stack

| Layer | Choice |
|-------|--------|
| Frontend | Next.js + TypeScript + Tailwind + shadcn/ui, **React Flow** (live agent graph), **SSE** (streaming agent activity) |
| Backend | **FastAPI** (Python) gateway + SSE |
| Orchestration | **LangGraph** — stateful multi-agent graph with native human-in-the-loop interrupts + retries |
| LLM | **Claude API** with model routing (Haiku for cheap sub-steps, Sonnet for reasoning) |
| Tools | Web search (Tavily / Brave) + **Firecrawl** for page fetch |
| State / queue / cache | **Redis** (run state, event pub/sub, rate limiting, caching) |
| Database | **PostgreSQL** (saved runs, logs, artifacts, shareable links) |
| Observability | **Langfuse** (self-hosted) |
| Packaging | Docker + docker-compose, **Caddy** proxy/SSL |
| CI/CD | GitHub Actions |
| Deploy | DigitalOcean droplet → `cadenza.devs-core.com` |

## Monorepo layout

```
apps/
  web/                  Next.js frontend (live agent graph UI)
  api/                  FastAPI gateway + SSE stream
packages/
  orchestrator/         LangGraph orchestration — the engine
    graphs/             stateful multi-agent graph definitions
    agents/             Planner / Researcher / Analyst / Writer / Critic
    tools/              web search + Firecrawl wrappers
  shared/               types shared across FE/BE (event schema lives here)
infra/                  docker-compose.yml, Caddyfile (placeholders)
.github/workflows/      CI/CD (placeholder)
```

## Getting started

> Not runnable yet — this is the initial scaffold. Setup instructions land as the
> build proceeds (see the **Planned build order** in [`CLAUDE.md`](./CLAUDE.md)).

```bash
cp .env.example .env   # fill in keys (server-side only)
```

## License

[MIT](./LICENSE) © 2026 Mohammad Ashraful Islam / [Devs Core](https://devs-core.com)
