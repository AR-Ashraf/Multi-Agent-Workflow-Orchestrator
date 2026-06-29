"use client";

import { useEffect, useMemo, useReducer, useRef, useState } from "react";
import { type CadenzaEvent, PROVIDERS, type ProviderId, assignModels } from "@cadenza/shared";
import { CadenzaMark } from "@/components/CadenzaMark";
import { BookCTA } from "@/components/BookCTA";
import { AgentGraph } from "@/components/console/AgentGraph";
import { track } from "@/lib/analytics";
import { type RunController, createController } from "@/lib/console/controller";
import { STAGE_COPY, type ConsoleState, initialState, reduce } from "@/lib/console/reducer";

type Action = { kind: "event"; event: CadenzaEvent } | { kind: "reset" };
const rootReducer = (s: ConsoleState, a: Action): ConsoleState =>
  a.kind === "reset" ? initialState() : reduce(s, a.event);

const CHIPS = [
  { q: "Market for AI scheduling assistants for US dental clinics", label: "AI scheduling for dental clinics" },
  { q: "Competitive landscape for AI customer-support agents in e-commerce", label: "AI support agents for e-commerce" },
  { q: "Demand for AI invoice-processing automation for SMB accounting firms", label: "AI invoicing for accounting firms" },
];

const TAGS: Record<string, [string, string]> = {
  rationale: ["r", "WHY"],
  security: ["s", "SECURITY"],
  verify: ["v", "VERIFY"],
  human: ["h", "HUMAN"],
};

export function Console() {
  const [state, dispatch] = useReducer(rootReducer, undefined, initialState);
  const controllerRef = useRef<RunController | null>(null);

  const [provider, setProvider] = useState<ProviderId>("anthropic");
  const providerInfo = PROVIDERS[provider];
  const [modelId, setModelId] = useState(providerInfo.models[providerInfo.defaultModelIndex]!.id);
  const [apiKey, setApiKey] = useState("");
  const [showKey, setShowKey] = useState(false);
  const [routing, setRouting] = useState(true);
  const [query, setQuery] = useState(CHIPS[0]!.q);
  const [started, setStarted] = useState(false);
  const [tab, setTab] = useState<"graph" | "activity">("graph");
  const [toast, setToast] = useState<string | null>(null);
  const [activeCite, setActiveCite] = useState<string | null>(null);

  const [elapsed, setElapsed] = useState(0);
  const clock = useRef<ReturnType<typeof setInterval> | null>(null);
  const startTs = useRef(0);
  const completedFired = useRef(false);

  const logRef = useRef<HTMLDivElement>(null);
  const hitlRef = useRef<HTMLDivElement>(null);
  const outputRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    controllerRef.current = createController();
    return () => {
      controllerRef.current?.stop();
      if (clock.current) clearInterval(clock.current);
    };
  }, []);

  // live elapsed clock while running / paused
  useEffect(() => {
    if (state.runState === "done" || state.runState === "error") {
      if (clock.current) clearInterval(clock.current);
      clock.current = null;
      if (state.runState === "done" && !completedFired.current) {
        completedFired.current = true;
        track("demo_run_completed");
      }
    }
  }, [state.runState]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [state.log.length]);

  useEffect(() => {
    if (state.hitl) hitlRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [state.hitl]);

  useEffect(() => {
    if (state.brief) outputRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [state.brief]);

  const previewBadges = useMemo(() => {
    const out: Record<string, string> = {};
    assignModels(provider, modelId, routing).forEach((a) => (out[a.nodeId] = a.modelLabel));
    return out;
  }, [provider, modelId, routing]);
  const badges = Object.keys(state.badges).length ? state.badges : previewBadges;

  const showToast = (msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 2600);
  };

  const run = () => {
    if (state.runState === "running" || state.runState === "paused") return;
    completedFired.current = false;
    dispatch({ kind: "reset" });
    setStarted(true);
    setElapsed(0);
    startTs.current = performance.now();
    if (clock.current) clearInterval(clock.current);
    clock.current = setInterval(() => setElapsed(performance.now() - startTs.current), 100);
    track("demo_run_started", { mode: apiKey ? "live" : "demo", provider });
    controllerRef.current?.start(
      { query: query.trim() || CHIPS[0]!.q, provider, modelId, routing, apiKey: apiKey || undefined },
      (event) => dispatch({ kind: "event", event }),
    );
  };

  const reset = () => {
    controllerRef.current?.stop();
    if (clock.current) clearInterval(clock.current);
    dispatch({ kind: "reset" });
    setStarted(false);
    setElapsed(0);
  };

  const approve = () => {
    track("demo_hitl_approved");
    controllerRef.current?.approve();
    showToast("✓ Approved — the Writer is drafting now");
  };
  const adjust = () => {
    controllerRef.current?.adjust("emphasize pricing & the mid-market gap");
    showToast("✎ Scope adjusted — passing your note to the Writer");
  };

  const stage = state.step >= 1 ? STAGE_COPY[state.step] : null;
  const keySet = apiKey.trim().length > 0;

  const downloadBrief = () => {
    if (!state.brief) return;
    const b = state.brief;
    const txt = [
      b.title,
      "",
      ...b.sections.map((s) => `## ${s.heading}\n${s.body}`),
      "",
      "Sources:",
      ...b.sources.map((s, i) => `${i + 1}. ${s.label}`),
      "",
      `Permalink: https://${b.permalink}`,
    ].join("\n");
    const url = URL.createObjectURL(new Blob([txt], { type: "text/plain" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = "cadenza-market-brief.txt";
    a.click();
    URL.revokeObjectURL(url);
    track("brief_downloaded");
    showToast("⬇ Brief downloaded");
  };

  const copyPermalink = () => {
    if (!state.brief) return;
    navigator.clipboard?.writeText(`https://${state.brief.permalink}`).catch(() => {});
    track("permalink_shared");
    showToast("🔗 Permalink copied");
  };

  return (
    <div className="console-shell">
      <div className="console-bar">
        <div className="title">
          <CadenzaMark className="mark" />
          Cadenza Console <span className="wf">— AI Market Research Brief</span>
        </div>
        <div className={`runstate ${state.runState}`}>
          <span className="led" />
          {state.runLabel}
        </div>
      </div>

      <div className="query-zone">
        {/* BYOK */}
        <div className="model-config">
          <div className="mc-head">
            <div className="mc-title">
              🔑 Model &amp; API key <span className="byo">Bring your own</span>
            </div>
            <div className={`keystatus ${keySet ? "ok" : ""}`}>
              <span className="led" />
              {keySet ? "Key set · running on your tokens" : "No key — running in demo mode"}
            </div>
          </div>
          <div className="mc-grid">
            <div className="mc-field">
              <label htmlFor="provider">Provider</label>
              <select
                id="provider"
                className="mc-select"
                value={provider}
                onChange={(e) => {
                  const p = e.target.value as ProviderId;
                  setProvider(p);
                  setModelId(PROVIDERS[p].models[PROVIDERS[p].defaultModelIndex]!.id);
                }}
              >
                {Object.values(PROVIDERS).map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="mc-field">
              <label htmlFor="model">Model</label>
              <select id="model" className="mc-select" value={modelId} onChange={(e) => setModelId(e.target.value)}>
                {providerInfo.models.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="mc-field">
              <label htmlFor="apikey">API key</label>
              <div className="key-wrap">
                <input
                  id="apikey"
                  className="mc-key"
                  type={showKey ? "text" : "password"}
                  autoComplete="off"
                  spellCheck={false}
                  placeholder={providerInfo.keyHint || "your key"}
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                />
                <button className="eye" type="button" aria-label="Show or hide key" onClick={() => setShowKey((v) => !v)}>
                  {showKey ? "🙈" : "👁"}
                </button>
              </div>
            </div>
          </div>
          <div className="mc-foot">
            <label className="route-toggle">
              <input type="checkbox" checked={routing} onChange={(e) => setRouting(e.target.checked)} />
              <span className="sw" />
              <span>Auto cost-routing — use the cheaper model for mechanical steps</span>
            </label>
            <div className="privacy-note">
              🔒{" "}
              <span>
                <b>Your key, your tokens.</b> Used only to run this workflow — never stored, never billed to us.
              </span>
            </div>
          </div>
        </div>

        <div className="ql">Your research question</div>
        <div className="query-input">
          <input value={query} onChange={(e) => setQuery(e.target.value)} aria-label="Research question" />
          {!started || state.runState === "done" ? (
            <button className="btn btn-gold" onClick={run} disabled={state.runState === "running"}>
              ▶ Run workflow
            </button>
          ) : null}
          {state.runState === "done" ? (
            <button className="btn btn-ghost" onClick={reset}>
              ↻ Run again
            </button>
          ) : null}
        </div>
        <div className="chips">
          {CHIPS.map((c) => (
            <span key={c.q} className="chip" onClick={() => setQuery(c.q)}>
              {c.label}
            </span>
          ))}
        </div>
      </div>

      {/* mobile tab switcher */}
      <div className="console-tabs">
        <button className={tab === "graph" ? "active" : ""} onClick={() => setTab("graph")}>
          Agent graph
        </button>
        <button className={tab === "activity" ? "active" : ""} onClick={() => setTab("activity")}>
          Activity
        </button>
      </div>

      <div className="console-main">
        <div className="graph-pane pane-graph" data-tab={tab}>
          {state.injection ? (
            <div className="inj-badge">
              ⚠ Content screened — {state.injection.status === "blocked" ? "injection blocked" : "sanitized"}
            </div>
          ) : null}
          <AgentGraph nodes={state.nodes} edges={state.edges} badges={badges} />
          <div className="legend">
            <span>
              <i style={{ background: "var(--gold)" }} /> Active
            </span>
            <span>
              <i style={{ background: "var(--green)" }} /> Done
            </span>
            <span>
              <i style={{ background: "var(--plum)" }} /> Waiting on you
            </span>
            <span>
              <i style={{ background: "var(--clay)" }} /> Blocked
            </span>
          </div>
        </div>

        <div className="rail pane-rail" data-tab={tab}>
          <div className="meters">
            <div className="meter">
              <div className="mv">
                {state.step}/{state.totalSteps}
              </div>
              <div className="ml">Step</div>
            </div>
            <div className="meter">
              <div className="mv">{state.tokens.toLocaleString()}</div>
              <div className="ml">Tokens</div>
            </div>
            <div className="meter">
              <div className="mv">${state.costUsd.toFixed(2)}</div>
              <div className="ml">Your est. cost</div>
            </div>
            <div className="meter">
              <div className="mv">{(elapsed / 1000).toFixed(1)}s</div>
              <div className="ml">Elapsed</div>
            </div>
          </div>

          <div className="explainer">
            <div className="ex-h">📖 How it works</div>
            <div className="ex-stage">{stage ? stage.stage : "Ready when you are"}</div>
            <div className="ex-body">
              {stage
                ? stage.body
                : "Press Run workflow. You’ll watch five kinds of AI agent hand work to each other — and stop to ask you for approval before writing anything."}
            </div>
            {stage ? (
              <div className="ex-hard">
                <b>Why this is hard:</b> {stage.hard}
              </div>
            ) : null}
          </div>

          <div className="log-wrap">
            <div className="log-head">
              <span className="lh">Event log · decision rationale</span>
              <span className="lh" style={{ color: "var(--gold-deep)" }}>
                {state.log.length ? `${state.log.length} events` : ""}
              </span>
            </div>
            <div className="log" ref={logRef}>
              {state.log.length === 0 ? (
                <div className="log-empty">
                  No events yet. Run the workflow to see every decision, search, and verification stream in live.
                </div>
              ) : (
                state.log.map((l) => {
                  const tag = TAGS[l.kind];
                  return (
                    <div key={l.seq} className={`log-item ${l.kind}`}>
                      <span className="lt">{(l.seq / 10).toFixed(0)}</span>
                      <span className="lx">
                        {tag ? <span className={`tagbit ${tag[0]}`}>{tag[1]}</span> : null}
                        <span className="who">{l.who}</span> {l.text}
                      </span>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </div>
      </div>

      {state.hitl ? (
        <div className="hitl-panel" ref={hitlRef}>
          <div className="hp-h">
            <span className="badge">PAUSED</span> Human-in-the-loop checkpoint
          </div>
          <p>
            The agents stopped on purpose. Before the Writer drafts anything, <b>you</b> decide the direction. Nothing
            consequential happens without your sign-off.
          </p>
          <div className="hitl-dir">
            <b>Proposed brief direction:</b>
            <ul>
              {state.hitl.proposedDirection.map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
          </div>
          <div className="hitl-actions">
            <button className="btn btn-gold btn-sm" onClick={approve}>
              ✓ Approve &amp; continue
            </button>
            <button className="btn btn-ghost btn-sm" onClick={adjust}>
              ✎ Adjust scope
            </button>
          </div>
        </div>
      ) : null}

      {state.brief ? (
        <div className="output-zone" ref={outputRef}>
          <div className="ob-head">
            <div className="oh-l">
              <span className="verified-stamp">
                ✓ {state.brief.claimsVerified.verified} of {state.brief.claimsVerified.total} key claims verified
                against sources
              </span>
            </div>
            <div className="ob-actions">
              <button className="btn btn-ghost btn-sm" onClick={downloadBrief}>
                ⬇ Download brief
              </button>
              <button className="btn btn-ghost btn-sm" onClick={copyPermalink}>
                🔗 Copy permalink
              </button>
            </div>
          </div>
          <div className="brief">
            <h3 className="bt">{state.brief.title}</h3>
            <div className="byline">{state.brief.byline}</div>
            {state.brief.sections.map((s) => (
              <div key={s.heading}>
                <h4>{s.heading}</h4>
                <p>
                  <BriefBody body={s.body} onCite={(label) => setActiveCite(label)} />
                </p>
              </div>
            ))}
            {activeCite ? <div className="cite-note">📎 {activeCite}</div> : null}
            <div className="sources">
              <h4>Sources</h4>
              <ol>
                {state.brief.sources.map((s) => (
                  <li key={s.id}>{s.label}</li>
                ))}
              </ol>
            </div>
            <div className="perma">
              <span style={{ color: "var(--muted)" }}>Shareable permalink:</span>{" "}
              <code>{state.brief.permalink}</code>
            </div>
          </div>

          <div className="convert" id="book">
            <div>
              <h3>Want an agent team like this for your business?</h3>
              <p>
                This is the kind of custom-coded, production-grade automation Devs Core builds — owned by you,
                engineered to scale, shipped in weeks not quarters.
              </p>
            </div>
            <BookCTA location="console_output" />
          </div>
        </div>
      ) : null}

      <div className={`toast ${toast ? "show" : ""}`}>{toast}</div>
    </div>
  );
}

function BriefBody({ body, onCite }: { body: string; onCite: (label: string) => void }) {
  const parts = body.split(/(\[Source \d+\])/g);
  return (
    <>
      {parts.map((part, i) => {
        const m = part.match(/^\[(Source \d+)\]$/);
        if (m) {
          return (
            <button key={i} className="cite" onClick={() => onCite(m[1]!)}>
              {part}
            </button>
          );
        }
        return <span key={i}>{part}</span>;
      })}
    </>
  );
}
