"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import type { Brief, CadenzaEvent } from "@cadenza/shared";
import { CadenzaMark } from "@/components/CadenzaMark";
import { AgentGraph } from "@/components/console/AgentGraph";
import { type ConsoleState, initialState, reduce } from "@/lib/console/reducer";

interface SavedRecord {
  run_id: string;
  status: string;
  mode: string;
  model_label: string;
  created_at: string;
  expires_at: string;
  brief: Brief | null;
  events: CadenzaEvent[];
  claims_verified: { verified: number; total: number };
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE ?? "";
const TAGS: Record<string, [string, string]> = {
  rationale: ["r", "WHY"],
  security: ["s", "SECURITY"],
  verify: ["v", "VERIFY"],
  human: ["h", "HUMAN"],
};

type Phase = "loading" | "notfound" | "error" | "ok";

const foldAll = (events: CadenzaEvent[]): ConsoleState => events.reduce(reduce, initialState());

const fmtDate = (iso: string): string => {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
};

export function SavedRun({ runId }: { runId: string }) {
  const [record, setRecord] = useState<SavedRecord | null>(null);
  // Without an API base there is no backend to hit — start in the error state
  // rather than calling setState synchronously inside the effect.
  const [phase, setPhase] = useState<Phase>(API_BASE ? "loading" : "error");
  const [view, setView] = useState<ConsoleState>(() => initialState());
  const [replaying, setReplaying] = useState(false);
  const [activeCite, setActiveCite] = useState<string | null>(null);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (!API_BASE) return;
    let alive = true;
    fetch(`${API_BASE}/api/runs/${runId}/record`)
      .then(async (r) => {
        if (r.status === 404) return "notfound" as const;
        if (!r.ok) throw new Error(String(r.status));
        return (await r.json()) as SavedRecord;
      })
      .then((res) => {
        if (!alive) return;
        if (res === "notfound") {
          setPhase("notfound");
          return;
        }
        setRecord(res);
        setView(foldAll(res.events));
        setPhase("ok");
      })
      .catch(() => alive && setPhase("error"));
    return () => {
      alive = false;
      if (timer.current) clearTimeout(timer.current);
    };
  }, [runId]);

  const replay = () => {
    if (!record || replaying) return;
    setReplaying(true);
    const events = record.events;
    let i = 0;
    let s = initialState();
    setView(s);
    const step = () => {
      if (i >= events.length) {
        setReplaying(false);
        return;
      }
      const cur = events[i]!;
      s = reduce(s, cur);
      setView({ ...s });
      const next = events[i + 1];
      i += 1;
      const delay = next ? Math.max(24, Math.min(900, (next.ts - cur.ts) * 0.5)) : 0;
      timer.current = setTimeout(step, delay);
    };
    step();
  };

  if (phase === "loading") {
    return <div className="run-msg">Loading saved run…</div>;
  }
  if (phase === "notfound") {
    return (
      <div className="run-msg">
        <h2>Run not found</h2>
        <p>This permalink has expired or never existed. Saved runs auto-expire after 30 days.</p>
        <Link className="btn btn-gold" href="/#demo">
          Run the demo →
        </Link>
      </div>
    );
  }
  if (phase === "error" || !record) {
    return (
      <div className="run-msg">
        <h2>Couldn’t load this run</h2>
        <p>The live demo backend isn’t reachable right now. Try the interactive demo instead.</p>
        <Link className="btn btn-gold" href="/#demo">
          Open the demo →
        </Link>
      </div>
    );
  }

  const brief = record.brief;
  return (
    <div className="console-shell">
      <div className="console-bar">
        <div className="title">
          <CadenzaMark className="mark" />
          Cadenza <span className="wf">— saved run</span>
        </div>
        <div className={`runstate ${view.runState}`}>
          <span className="led" />
          {record.status === "completed" ? "Complete" : view.runLabel}
        </div>
      </div>

      <div className="saved-meta">
        <span>
          Ran on <b>{record.model_label || "—"}</b> · {record.mode === "live" ? "live" : "cached demo"}
        </span>
        <span>Saved {fmtDate(record.created_at)}</span>
        <span>Expires {fmtDate(record.expires_at)}</span>
        <button className="btn btn-ghost btn-sm" onClick={replay} disabled={replaying}>
          {replaying ? "Replaying…" : "▶ Replay run"}
        </button>
      </div>

      <div className="console-main">
        <div className="graph-pane">
          {view.injection ? (
            <div className="inj-badge">
              ⚠ Content screened — {view.injection.status === "blocked" ? "injection blocked" : "sanitized"}
            </div>
          ) : null}
          <AgentGraph nodes={view.nodes} edges={view.edges} badges={view.badges} />
        </div>

        <div className="rail">
          <div className="log-wrap">
            <div className="log-head">
              <span className="lh">Event log · decision rationale</span>
              <span className="lh">{view.log.length ? `${view.log.length} events` : ""}</span>
            </div>
            <div className="log">
              {view.log.map((l) => {
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
              })}
            </div>
          </div>
        </div>
      </div>

      {brief ? (
        <div className="output-zone">
          <div className="ob-head">
            <div className="oh-l">
              <span className="verified-stamp">
                ✓ {brief.claimsVerified.verified} of {brief.claimsVerified.total} key claims verified
                against sources
              </span>
            </div>
          </div>
          <div className="brief">
            <h3 className="bt">{brief.title}</h3>
            <div className="byline">{brief.byline}</div>
            {brief.sections.map((s) => (
              <div key={s.heading}>
                <h4>{s.heading}</h4>
                <p>
                  <BriefBody body={s.body} onCite={setActiveCite} />
                </p>
              </div>
            ))}
            {activeCite ? <div className="cite-note">📎 {activeCite}</div> : null}
            <div className="sources">
              <h4>Sources</h4>
              <ol>
                {brief.sources.map((s) => (
                  <li key={s.id}>{s.label}</li>
                ))}
              </ol>
            </div>
            <div className="perma">
              <span style={{ color: "var(--muted)" }}>Permalink:</span> <code>{brief.permalink}</code>
            </div>
          </div>

          <div className="convert">
            <div>
              <h3>Want an agent team like this for your business?</h3>
              <p>
                This is the kind of custom-coded, production-grade automation Devs Core builds — owned
                by you, engineered to scale.
              </p>
            </div>
            <Link href="/#book" className="btn btn-gold">
              Book a build call →
            </Link>
          </div>
        </div>
      ) : null}
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
