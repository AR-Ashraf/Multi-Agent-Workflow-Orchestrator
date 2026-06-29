# CLAUDE.md — Multi-Agent Workflow Orchestrator

Project-specific instructions for Claude (and humans). Read this before touching code.

---

## 1. Project goal & what "done" looks like

**Goal:** A public, interactive demo where a visitor triggers a *real* multi-agent
workflow and watches AI agents collaborate live. It is Devs Core's flagship showcase
to prove we build production-grade **agentic** systems — orchestration, human-in-the-loop,
error recovery — **not** no-code automations. The audience is **non-technical founders**,
so the demo must make the *hard parts* legible, not just flash output.

**Flagship workflow — "AI Market Research Brief":**

```
Planner  decomposes the task into research sub-questions  (emits its reasoning)
   │
   ▼
Researchers (parallel)  web search (Tavily/Brave) + Firecrawl page fetch
   │                     ▼ all fetched/tool content passes the INJECTION GUARD first
   ▼
Analyst  synthesizes findings into structured insights
   │
   ▼
[ HUMAN-IN-THE-LOOP APPROVAL CHECKPOINT ]   visitor approves / edits direction
   │
   ▼
Writer  drafts the brief
   │
   ▼
Critic  QAs the draft AND verifies key claims against cited sources;
        flags unsupported claims; retries/loops back on failure
   │
   ▼
Output  downloadable, CITED + claim-verified brief + shareable run permalink
```

The same engine will later run secondary workflows (outreach draft, content outline).

### Core features (v1)

The four **must-haves** below are what make this a credible expertise showcase, not a toy:

1. **Prompt-injection / tool-output defense.** Untrusted web/tool content is screened
   *before* the model acts on it; suspicious instructions are sanitized or blocked, with
   a small UI indicator ("content screened / injection blocked"). See §9.
2. **Decision-level transparency.** Show *why*, not just *what* — the Planner's reasoning
   for the sub-tasks it chose and the Critic's rationale for accepting or rejecting/retrying
   a draft. This "decision rationale" is carried by the event schema and rendered in the UI.
3. **Plain-English "How it works" explainer.** A founder-friendly panel, side by side with
   the technical React Flow graph, explaining what just happened and why it's hard.
4. **Claim / citation verification (anti-hallucination).** The Critic verifies the brief's
   key claims against the cited sources before release and flags anything unsupported.

Plus the supporting capabilities: live React Flow agent graph over SSE; HITL approval
checkpoint; Critic-driven error recovery/retries; cited, downloadable brief; shareable run
permalink; cost/safety guardrails (§8); and a lead-gen CTA + analytics (§11).

**"Done" (v1) means a visitor can:**
1. Trigger the Market Research Brief workflow from the browser.
2. Watch the **live agent graph** (React Flow) update as agents run, streamed via SSE.
3. See **decision rationale** — *why* the Planner chose its sub-tasks and *why* the Critic
   accepted or retried — not just tokens/cost/output. *(feature 2)*
4. Read a plain-English **"How it works" explainer** sitting beside the graph. *(feature 3)*
5. Hit the **human approval checkpoint**, approve or adjust, and resume the run.
6. See **error recovery** in action (Critic-driven retries) without the run dying.
7. Trust the output: the **Critic verifies key claims against the cited sources** and
   flags unsupported ones before the brief is released. *(feature 4)*
8. See **injection defense** working: untrusted web/tool content is screened before the
   model acts, with a "content screened / injection blocked" indicator when triggered.
   *(feature 1)*
9. Download a **cited** brief and share a **permalink** that replays/loads the saved run.
10. Do all of this **safely and cheaply** — within the cost & safety guardrails in §8,
    the agent-security rules in §9, and the privacy rules in §10.
11. Convert: the showcase fires the lead-gen analytics events and surfaces the
    "Book a build call" CTA in §11.

---

## 2. Non-goals (explicit — stop scope creep)

This is a **showcase / lead-gen demo**, not a product. It is **NOT**:

- **NOT a SaaS** — no user accounts, **no auth**, no login.
- **NOT multi-tenant** — no orgs, workspaces, or per-customer isolation.
- **NOT billed** — no subscriptions, metering-as-a-product, or payment flows.
- **NOT a custom workflow builder** — visitors run *our* curated workflows; they do not
  compose their own graphs.
- **NOT a general agent platform / API product** — no public API, SDK, or webhooks for
  third parties.

If a request implies any of the above, flag it as scope creep and check before building.
The cost/safety knobs in §8 are internal guardrails, **not** a billing system.

---

## 3. Tech decisions & reasoning

| Decision | Why |
|----------|-----|
| **Next.js + TypeScript + Tailwind + shadcn/ui** | Fast, production-grade React with type safety; shadcn gives clean, ownable components without a heavy UI dependency. |
| **React Flow** for the agent graph | Purpose-built for node/edge graphs; lets the on-screen graph mirror the LangGraph structure 1:1, which is the core "watch agents collaborate" wow-factor. |
| **Server-Sent Events (SSE)** | Agent activity is one-directional server→client streaming. SSE is simpler and more robust than WebSockets for this, works over plain HTTP, and survives proxies cleanly. |
| **FastAPI (Python)** | Async-first, great for streaming responses; Python is the native ecosystem for LangGraph and the agent/LLM tooling. |
| **LangGraph** for orchestration | Stateful multi-agent graphs with **native human-in-the-loop interrupts** and **retry** semantics — exactly the agentic features we're showcasing. The graph structure mirrors the React Flow UI. |
| **Claude API + model routing** | Route cheap/mechanical sub-steps to **Haiku** and reasoning-heavy steps to **Sonnet** to control cost and latency without sacrificing quality where it matters. |
| **Tavily/Brave + Firecrawl** | Tavily/Brave for web search results; Firecrawl for reliable, clean page-content extraction (handles JS-heavy pages and returns LLM-ready markdown). |
| **Redis** | One tool for run state, event pub/sub (fan-out to SSE), per-IP rate limiting, and caching of common inputs. |
| **PostgreSQL** | Durable store for saved runs, logs, artifacts, and shareable permalinks. |
| **Langfuse (self-hosted)** | LLM observability — traces, token/cost accounting, debugging agent steps, and the eval harness sink (§7) — without sending data to a third party. |
| **Docker + docker-compose, Caddy, GitHub Actions** | Reproducible local + prod env; Caddy gives automatic TLS for `agents.devs-core.com`; Actions for CI/CD. |
| **DigitalOcean droplet** | Simple, cost-predictable host for a single self-contained demo stack. |

---

## 4. Architecture

```
        Browser (Next.js)
          React Flow graph  ║  "How it works" explainer   (side by side)
            │   trigger run (POST)          ▲  live agent events + rationale (SSE)
            ▼                               │
        ┌─────────────────────────────────────────────┐
        │  FastAPI gateway (apps/api)                   │
        │   - REST endpoints (start run, approve, etc.) │
        │   - SSE endpoint (subscribes to Redis pub/sub)│
        └───────────────┬───────────────────────────────┘
                        │ invokes
                        ▼
        ┌─────────────────────────────────────────────┐
        │  LangGraph orchestrator (packages/orchestrator)│
        │   graphs/  multi-agent graph (mirrors UI)      │
        │   agents/  Planner/Researcher/Analyst/Writer/  │
        │            Critic (Claude calls, model-routed) │
        │   tools/   web search + Firecrawl              │
        │   guard/   injection screen on ALL tool output │
        │   - emits events incl. decision rationale      │
        │     ──▶ Redis pub/sub                          │
        │   - HITL via LangGraph interrupts              │
        │   - Critic verifies claims vs. cited sources   │
        └───────┬───────────────────────┬───────────────┘
                │                        │
                ▼                        ▼
         Redis (state, pub/sub,    PostgreSQL (saved runs,
         rate limit, cache)        logs, artifacts, permalinks)
                │
                ▼
         Langfuse (traces / cost / evals / debugging)
```

**Request → result flow:**
1. Browser POSTs a run request to FastAPI; FastAPI creates a run, stores initial state in Redis/Postgres, and kicks off the LangGraph graph.
2. The graph runs agents. Each meaningful step **emits an event** (per the event schema) onto a Redis pub/sub channel keyed by run id. Events carry **decision rationale** (Planner sub-task reasoning, Critic verdicts) and **injection-screening status**, not just results.
3. All fetched/tool content passes the **injection guard** before any agent reasons over it (§9).
4. FastAPI's SSE endpoint subscribes to that channel and streams events to the browser, which updates the React Flow graph **and the "How it works" explainer** in real time.
5. At the **HITL checkpoint**, LangGraph **interrupts**; the run pauses with state persisted. The browser shows an approval UI; the user's decision resumes the graph.
6. The **Critic QAs the draft and verifies key claims against the cited sources**; unsupported claims or failures trigger **retries/loops** (error recovery).
7. On completion, the cited, claim-verified brief + run metadata are persisted to Postgres and exposed via a **shareable permalink**.

**Event schema = the FE/BE contract.** It lives in **`packages/shared`** and is the single
source of truth for everything the orchestrator emits and the UI renders — including the
**decision-rationale fields** (feature 2) and the **injection-screening status** (feature 1).
The LangGraph topology and the on-screen React Flow graph are the *same shape*; the event
schema is what keeps them in sync.

---

## 5. Repo conventions

**Monorepo layout:**

```
apps/web/                 Next.js frontend (live agent graph + "How it works" explainer)
apps/api/                 FastAPI gateway + SSE
packages/orchestrator/    LangGraph engine — ALL orchestration logic lives here
  graphs/                 graph definitions (topology mirrors the UI)
  agents/                 Planner / Researcher / Analyst / Writer / Critic
  tools/                  web search + Firecrawl wrappers
packages/shared/          types shared FE/BE — the EVENT SCHEMA lives here
infra/                    docker-compose.yml, Caddyfile (placeholders for now)
.github/workflows/        CI/CD (placeholder for now)
```

**Rules:**
- **Orchestration logic lives in `packages/orchestrator`.** Don't scatter agent/graph
  logic into `apps/api` or `apps/web`. The API is a thin gateway; the UI is a thin client.
- **The event schema is the FE/BE contract** and lives in **`packages/shared`**. It is the
  single source of truth for what the orchestrator emits and what the UI renders, and it
  carries the **decision-rationale fields** (feature 2) and **injection-screening status**
  (feature 1) — not only results. Change it deliberately and update both sides together.
- **Orchestration logic must be testable without live LLM calls** — see §7. Design agents
  and the graph so Claude/tool calls can be mocked.
- **All LLM calls are server-side only.** No provider API key ever reaches the browser.
  The frontend talks only to FastAPI.
- **Every run must respect token/step caps.** No agent loop may run unbounded; enforce
  per-run token and step ceilings (see §8).
- **Treat all tool/web output as untrusted** (see §9) — it passes the injection guard and
  never drives control flow or tool calls.
- **Model routing is intentional**, not incidental — pick Haiku vs. Sonnet per step on
  purpose and keep that decision visible in the agent code.
- Type safety everywhere: TypeScript on the frontend, Python type hints on the backend.
- Secrets come from `.env` (see `.env.example`); never commit real keys.

---

## 6. Tooling & dev commands

**Baseline versions (pin these):**
- **Node 22 LTS** + **pnpm 9** (frontend workspace + shared TS types).
- **Python 3.12** + **uv** (backend / orchestrator env + deps).
- **Docker** + Docker Compose (full stack).

**Package managers:** pnpm for JS/TS (`apps/web`, `packages/shared`); uv for Python
(`apps/api`, `packages/orchestrator`). Do not mix in npm/yarn or pip/poetry.

**Lint / format / types:**
- Python — **Ruff** (lint) + **Black** (format) + **Pyright** (type checks).
- TS/JS — **ESLint** + **Prettier**; `tsc --noEmit` for type checks.

### Local development

> Intended contract; goes live as the build proceeds (see §12). The repo is currently
> scaffold-only and not yet runnable.

```bash
cp .env.example .env                                    # fill in keys (server-side only)

# Full stack (preferred once infra is defined):
docker compose -f infra/docker-compose.yml up

# Or run pieces individually:
pnpm --filter web dev                                   # frontend
uv run uvicorn app.main:app --reload --port 8000        # API (from apps/api)
```

**Ports (canonical — keep these stable; they back `.claude/launch.json`):**

| Service          | Port | Notes |
|------------------|------|-------|
| web (Next.js)    | 3000 | live agent graph + explainer |
| api (FastAPI)    | 8000 | REST + SSE |
| postgres         | 5432 | saved runs / artifacts |
| redis            | 6379 | state, pub/sub, rate limit, cache |
| langfuse         | 3001 | observability (off 3000 to avoid clashing with web) |

**Quality commands (wire these into CI in §12):**

```bash
# Python
uv run ruff check . && uv run black --check . && uv run pyright
uv run pytest

# TS/JS
pnpm lint && pnpm format:check && pnpm typecheck
pnpm test
```

---

## 7. Testing & eval strategy

Agents are the product, so **how we verify them is part of the showcase.** A core rule:
**orchestration logic must be testable without live LLM calls.**

**Deterministic tests (fast, run in CI):**
- **Mocked-LLM unit tests for the graph topology.** Stub Claude/tool calls so the LangGraph
  graph is exercised with fixed responses — assert routing, the HITL interrupt/resume path,
  Critic retry loops, claim-verification behavior, the injection guard's
  block/sanitize/pass decisions, token/step-cap enforcement, and the **event-schema
  contract** (every emitted event — including decision-rationale and screening-status
  fields — validates against `packages/shared`). No live LLM in CI.
- **Tool wrapper tests** with recorded/fixture responses for web search + Firecrawl.
- **Frontend** — component/contract tests (the UI must render every event type the schema
  can emit, including rationale + "content screened" states) and a Playwright happy-path
  that drives a mocked run end-to-end.

**Eval harness (quality — run on demand / nightly, not blocking PRs):**
- A small **eval set** of sample briefs, scored on **quality and citation coverage**
  (LLM-as-judge + structural checks: citations present, every key claim grounded in a cited
  source, format valid).
- Log results to **Langfuse**; track regressions across prompt / model-routing changes.
  Treat a quality or citation-coverage drop as a release blocker even if unit tests pass.

**How to run:** `uv run pytest` for unit tests; the eval harness runs via its own command
(documented when built) against the eval set and writes scores to Langfuse.

**Rule:** new agent/graph behavior ships with mocked-LLM tests; prompt or routing changes
ship with an eval run.

---

## 8. Cost & safety rules (core requirements, not optional)

These are **requirements**. Implement and enforce them, don't treat them as nice-to-haves.

1. **Daily global LLM spend cap.** A hard ceiling on total LLM spend per day across all
   visitors; when hit, new runs are refused gracefully (fall back to a cached example run).
2. **Per-IP rate limiting via Redis.** Throttle how many runs a single IP can start.
3. **Per-run token/step ceilings.** Every run has a maximum token budget and a maximum
   number of graph steps; exceeding either ends the run cleanly.
4. **Model routing.** Use Haiku for cheap/mechanical sub-steps, Sonnet for reasoning, to
   minimize cost per run.
5. **Cache common inputs.** Cache web fetches / repeated sub-results (Redis) so identical
   or popular requests don't re-spend on the LLM or tools.
6. **Light bot gate.** A bot mitigation (Cloudflare Turnstile / hCaptcha) on run-trigger,
   **or** a free, cached "example run" path so curious visitors cost nothing.
7. **All API keys server-side only.** Keys live in the backend env, never shipped to the
   browser, never in client bundles.
8. **Bring-your-own-key (BYOK) is the default funding model.** Visitors run on *their own*
   provider + key, billed to *them*, so the showcase's own LLM spend floor is **$0**. A
   no-key visitor gets the free cached example run (rule 6), never a billed one. An optional
   *house* key (off by default) can fund key-less real runs, but only behind the daily spend
   cap (rule 1) and the per-IP limit (rule 2); when the cap is hit it falls back to the
   cached run. The visitor's key is the **one** key allowed past the browser — their own
   transient, per-request input, **never stored or logged** (§10) — which does not weaken
   rule 7 (that bars *our* provider keys from the client). The public GA4/GTM measurement
   IDs (§11) are the only other client-side identifiers, and they are not secrets.

---

## 9. Agent security

The Researcher agents browse the open web, so **the model consumes attacker-controllable
text.** **Indirect prompt injection is the #1 LLM risk (OWASP `LLM01`)** — we treat it as a
first-class threat, not an edge case. We follow the **OWASP Top 10 for LLM Applications**
and **OWASP's Top 10 for Agentic Applications / agentic-AI threat guidance** as our standard.

**Core rule:** *Screen and quarantine tool/web output before the model acts on it.* All
fetched content (search snippets, Firecrawl page text) is **untrusted data, never
instructions**, and passes the **injection guard** first.

- **Injection guard / classifier step.** Every tool/web result flows through a guard before
  any agent reasons over it. If it detects embedded instructions / injection attempts, it
  **sanitizes or blocks** the content and emits a screening-status event so the UI can show
  a **"content screened / injection blocked"** indicator.
- **Untrusted by default + separate channels.** Inject retrieved content as clearly-delimited
  untrusted data (e.g. an explicit `<untrusted_source>` block), never merged into
  system/developer instructions.
- **Least-privilege tools.** Each agent gets only the tools it needs; the Writer/Critic get
  no web/fetch tools. Tool selection is decided by *our* graph logic, never by page content.
- **Input & output screening.** Sanitize/escape control sequences and truncate to the
  per-step token budget on the way in; validate agent **outputs** against the event schema
  before they touch Redis/Postgres or the SSE stream; reject malformed/oversized payloads.
- **Human approval for high-risk actions.** Anything beyond read-only research routes
  through the HITL checkpoint (§4) — the model cannot take a consequential action on its own.
- **Cite & verify.** Every claim in the brief carries a source URL, and the Critic verifies
  claims against those sources (feature 4) — both a product feature and an
  injection-resistance check (ungrounded claims are a red flag).

If page content reads like instructions to the agent, that is an injection attempt: the
guard handles it, the content stays analyzed data, and the UI flags it.

---

## 10. Data & privacy / retention

The demo is **public, has no auth, saves runs, and exposes shareable permalinks** — so
treat stored data conservatively.

- **Assume permalinks are public.** Anyone with the link can view a saved run. Never put
  anything sensitive in run state, logs, or artifacts.
- **Avoid storing PII.** Don't ask visitors for personal data. The query a visitor types is
  stored as part of the run — warn briefly, and redact secrets/PII (API keys, emails,
  tokens) from stored logs and Langfuse traces. Don't retain raw IPs beyond what rate
  limiting needs.
- **Retention policy.** Saved runs, logs, and artifacts **auto-expire after 30 days**
  (default `N` — confirm before changing). Provide a way to purge a specific run on request.
- **Permalinks are unguessable** (random ids), but that is obscurity, not access control —
  pair it with retention; never rely on it for anything that must stay private.
- **Data stays first-party.** Langfuse is self-hosted; don't add third-party log sinks that
  ship run content off-box beyond the documented stack.

---

## 11. Business / conversion hooks (lead-gen showcase)

This is a **LEAD-GEN showcase** whose job is converting founders/CTOs into Devs Core build
calls. Conversion is a first-class feature, not an afterthought.

- **"Book a build call" CTA.** Shown clearly **under the finished output** (and on the
  permalink page), framed for a non-technical founder evaluating whether we can build
  agentic systems for them.
- **Instrument GA4 / GTM** with these funnel events, at minimum:
  - `demo_run_started`
  - `demo_run_completed`
  - `demo_hitl_approved`
  - `book_call` (the conversion event)
  *(optional secondary: `brief_downloaded`, `permalink_shared`.)*
- **Cross-domain measurement.** Configure GA4/GTM cross-domain tracking between
  **`devs-core.com`** and **`agents.devs-core.com`** so a visitor's journey from the main
  site → demo → book-call is one attributed session.
- **GA4/GTM IDs are client-side and public** (`NEXT_PUBLIC_GA_ID` / GTM container) — that's
  the one exception to "no keys in the browser." Still no *provider/API* keys client-side (§8).
- **Don't bury the conversion.** The live agent graph + explainer are the hook; keep the
  path from wow-moment → CTA short and obvious.

---

## 12. Planned build order

Build in this sequence; each step should be demoable/testable before the next.

1. **Event schema** (`packages/shared`) — define the FE/BE contract first, **including the
   decision-rationale fields** (Planner reasoning, Critic verdicts) and the
   **injection-screening status** fields.
2. **Testing harness (early)** — stand up mocked-LLM unit-test scaffolding + the eval-harness
   skeleton right after the schema, so every later step ships with tests (§7).
3. **Research graph with mocked LLM** — LangGraph topology (Planner→Researchers→Analyst→
   HITL→Writer→Critic) wired end-to-end with mocked responses, **emitting events incl.
   decision rationale**. Ships with mocked-LLM tests.
4. **Tools** — real web search (Tavily/Brave) + Firecrawl page fetch.
5. **Injection guard (right after tools)** — route all tool/web output through the
   guard/classifier; emit "content screened / injection blocked" status (§9).
6. **Claim / citation verification (in the Critic)** — Critic verifies key claims against
   cited sources, flags unsupported ones, and retries on failure (feature 4).
7. **FastAPI + SSE** — gateway endpoints + the SSE stream backed by Redis pub/sub.
8. **React Flow UI + "How it works" explainer** — live agent graph and the founder-friendly
   explainer side by side, consuming the SSE stream (incl. rationale + screening indicators).
9. **Rate limiting & cost caps** — Redis rate limiting, daily spend cap, per-run token/step
   ceilings, model routing, caching, bot gate (§8).
10. **HITL** — wire the LangGraph interrupt to a real approval UI + resume.
11. **Persistence & permalinks** — Postgres for saved runs/logs/artifacts + shareable links,
    with the retention policy from §10.
12. **Lead-gen layer** — "Book a build call" CTA + GA4/GTM events + cross-domain tracking (§11).
13. **Docker / Caddy / CI** — docker-compose stack, Caddy TLS for `agents.devs-core.com`,
    GitHub Actions (lint/format/type/test from §6–§7), deploy to the DigitalOcean droplet.

(Real Claude calls replace the mocks once the graph + tools are stable, before or alongside
steps 7–9, gated by the cost & safety rules in §8 and the agent-security rules in §9.)

---

## 13. Commit workflow

> After completing each feature or unit of work, output a clear, humanized git commit
> message (conventional-commit style subject line + a short plain-English body describing
> what changed and why). Do NOT auto-commit or auto-push — present the message and the
> exact git commands for me to run myself.
