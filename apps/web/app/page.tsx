import { CadenzaMark } from "@/components/CadenzaMark";
import { MiniFlow } from "@/components/MiniFlow";
import { Nav } from "@/components/Nav";

export default function Home() {
  return (
    <>
      <Nav />
      <a id="top" />

      {/* ===================== HERO ===================== */}
      <section className="hero">
        <div className="wrap hero-grid">
          <div>
            <span className="eyebrow">A Devs Core showcase · Custom-coded AI agents</span>
            <h1>
              AI agents that research, <span className="accent">debate, and fact-check</span> — live
              in your browser.
            </h1>
            <p className="hero-lead">
              Cadenza runs a real team of AI agents that plan, search the web, synthesize, pause for
              your approval, then verify every claim before handing you a cited brief. Watch the hard
              parts happen — not just the output.
            </p>
            <div className="hero-cta">
              <a href="#demo" className="btn btn-gold">
                ▶ Run the live demo
              </a>
              <a href="#why" className="btn btn-ghost">
                See why it’s hard
              </a>
            </div>
            <div className="trust">
              <div className="trust-label">Production stack · bring your own model &amp; key</div>
              <div className="trust-row">
                <span>Claude / GPT / Gemini</span>
                <span className="dot">·</span>
                <span>LangGraph</span>
                <span className="dot">·</span>
                <span>FastAPI + SSE</span>
                <span className="dot">·</span>
                <span>React Flow</span>
                <span className="dot">·</span>
                <span>Redis</span>
                <span className="dot">·</span>
                <span>Postgres</span>
              </div>
            </div>
          </div>

          <div className="hero-card">
            <div className="hc-top">
              <span className="tag">workflow · ai-market-research-brief</span>
              <span className="live-pill">
                <span className="pulse" /> Live
              </span>
            </div>
            <MiniFlow />
          </div>
        </div>
      </section>

      {/* ===================== DEMO (console arrives in 7b) ===================== */}
      <section id="demo" className="band">
        <div className="wrap">
          <div className="sec-head">
            <span className="eyebrow">The live demo</span>
            <h2>Trigger the workflow. Watch the agents collaborate.</h2>
            <p>
              Type a question, hit run, and follow the live agent graph while a plain-English
              explainer tells you what’s happening and why it’s hard.
            </p>
          </div>
          <div className="console-shell">
            <div className="console-bar">
              <div className="title">
                <CadenzaMark className="mark" />
                Cadenza Console <span className="wf">— AI Market Research Brief</span>
              </div>
            </div>
            <div className="console-placeholder">
              The live console — bring your own model &amp; key, the React Flow agent graph, the
              event log, and the cited brief — streams in here.
            </div>
          </div>
        </div>
      </section>

      {/* ===================== WHY IT'S HARD ===================== */}
      <section id="why">
        <div className="wrap">
          <div className="sec-head">
            <span className="eyebrow">Why it’s hard</span>
            <h2>Four things that separate a real agent system from a toy.</h2>
            <p>
              Anyone can chain a prompt to a web search. The difficulty — and the reason these
              systems fail in production — lives in the parts you just watched the demo handle.
            </p>
          </div>
          <div className="feat-grid">
            <div className="feat">
              <span className="fnum">01</span>
              <div className="fi" style={{ background: "var(--clay-wash)" }}>
                🛡️
              </div>
              <h3>Prompt-injection defense</h3>
              <p>
                The moment an agent reads the open web, attackers can hide instructions in a page.
                Cadenza screens every fetched page <i>before</i> the model acts on it, treating web
                content as data, never commands. You saw the “injection blocked” flag fire live.
              </p>
            </div>
            <div className="feat">
              <span className="fnum">02</span>
              <div className="fi" style={{ background: "var(--gold-wash)" }}>
                🔍
              </div>
              <h3>Decision transparency</h3>
              <p>
                Most demos show you <i>what</i> the AI produced. Cadenza shows you <i>why</i> — the
                Planner’s reasoning for the sub-tasks it picked, and the Critic’s verdict on whether
                to accept or retry a draft. No black box.
              </p>
            </div>
            <div className="feat">
              <span className="fnum">03</span>
              <div className="fi" style={{ background: "var(--green-wash)" }}>
                ✓
              </div>
              <h3>Claim verification</h3>
              <p>
                AI makes things up. Before the brief is released, the Critic checks every key claim
                against the actual cited source and flags anything unsupported — then loops back to
                fix it. That’s the anti-hallucination guarantee founders actually need.
              </p>
            </div>
            <div className="feat">
              <span className="fnum">04</span>
              <div className="fi" style={{ background: "var(--plum-wash)" }}>
                🙋
              </div>
              <h3>Human-in-the-loop control</h3>
              <p>
                Real workflows can’t run fully unattended. Cadenza pauses at a checkpoint and waits
                for a human to approve or adjust direction before anything consequential happens —
                with the run state safely persisted while it waits.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ===================== HOW IT WORKS ===================== */}
      <section id="how" className="band">
        <div className="wrap">
          <div className="sec-head">
            <span className="eyebrow">Under the workflow</span>
            <h2>One question in. A verified, cited brief out.</h2>
            <p>
              The same engine can run other workflows — outreach drafts, content outlines, competitor
              teardowns. The orchestration is the product.
            </p>
          </div>
          <div className="how-grid">
            <div className="howstep">
              <div className="hs-n">Step 1 · Plan &amp; research</div>
              <h4>Decompose, then search in parallel</h4>
              <p>
                A Planner breaks your question into focused sub-questions; three Researchers search
                and read the web at the same time, each screened for injection.
              </p>
            </div>
            <div className="howstep">
              <div className="hs-n">Step 2 · Synthesize &amp; approve</div>
              <h4>Insights, then your checkpoint</h4>
              <p>
                An Analyst turns raw findings into structured insights and proposes a direction. The
                run pauses for your approval before a single word is written.
              </p>
            </div>
            <div className="howstep">
              <div className="hs-n">Step 3 · Write &amp; verify</div>
              <h4>Draft, fact-check, release</h4>
              <p>
                A Writer drafts the brief; a Critic verifies every claim against its source, retries
                on failure, and only then releases a cited, downloadable brief with a permalink.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* ===================== TECH ===================== */}
      <section id="tech">
        <div className="wrap">
          <div className="sec-head">
            <span className="eyebrow">Under the hood</span>
            <h2>Built like software, because it is software.</h2>
            <p>
              No rented no-code workflow you can’t own. Every layer is version-controlled, testable
              without burning LLM spend, and yours at the end.
            </p>
          </div>
          <div className="tech-grid">
            {[
              ["LangGraph", "Stateful multi-agent graph with native human-in-the-loop interrupts & retries."],
              ["Bring your own model", "Run on your own Claude, GPT, Gemini, Llama or Mistral key — your tokens, your bill, never ours."],
              ["Model routing", "Cheaper model for mechanical steps, your strongest for reasoning — cost controlled on purpose."],
              ["FastAPI + SSE", "Async gateway streaming every agent event to the browser in real time."],
              ["React Flow", "The on-screen graph mirrors the orchestration graph 1:1."],
              ["Injection guard", "OWASP-aligned screening on all tool/web output before the model acts."],
              ["Redis + Postgres", "Run state, pub/sub, rate-limiting, plus durable saved runs & permalinks."],
              ["Langfuse (self-hosted)", "Traces, token/cost accounting & evals — your data stays first-party."],
            ].map(([tn, td]) => (
              <div className="techcard" key={tn}>
                <div className="tn">{tn}</div>
                <div className="td">{td}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===================== FINAL CTA ===================== */}
      <section style={{ paddingTop: 0 }}>
        <div className="wrap">
          <div className="final" id="book">
            <h2>You just watched the pitch run itself.</h2>
            <p>
              If this is the level of agentic system you want built — owned by you, engineered to
              scale — let’s talk about your workflow.
            </p>
            <div className="fbtns">
              <a href="#book" className="btn btn-gold">
                Book a build call
              </a>
              <a href="#demo" className="btn btn-ghost" style={{ color: "#fff", borderColor: "rgba(255,255,255,.3)" }}>
                Run the demo again
              </a>
            </div>
            <div className="micro">
              Custom-coded AI agents &amp; automation for US businesses · serving founders in Florida,
              Georgia &amp; nationwide
            </div>
          </div>
        </div>
      </section>

      {/* ===================== FOOTER ===================== */}
      <footer>
        <div className="wrap foot-grid">
          <div className="brand">
            <CadenzaMark />
            <div>
              <div className="brand-name">Cadenza</div>
              <div className="brand-sub">by Devs Core</div>
            </div>
          </div>
          <div className="foot-links">
            <a href="#demo">Live demo</a>
            <a href="#why">Why it’s hard</a>
            <a href="#how">How it works</a>
            <a href="#tech">Under the hood</a>
            <a href="#book">Book a build call</a>
          </div>
        </div>
        <div className="wrap" style={{ marginTop: 22 }}>
          <div className="fmeta">
            © 2026 Devs Core · Custom-coded AI agents &amp; workflow automation. We build it, you own
            it.
          </div>
        </div>
      </footer>
    </>
  );
}
