import type {
  Brief,
  CadenzaEvent,
  EdgeStatus,
  NodeStatus,
  RunState,
} from "@cadenza/shared";
import { EDGE_IDS, NODE_IDS, TOTAL_STEPS } from "@cadenza/shared";

export interface LogEntry {
  seq: number;
  kind: string;
  who: string;
  text: string;
}

export interface ConsoleState {
  runState: RunState;
  runLabel: string;
  step: number;
  totalSteps: number;
  tokens: number;
  costUsd: number;
  elapsedMs: number;
  nodes: Record<string, NodeStatus>;
  edges: Record<string, EdgeStatus>;
  badges: Record<string, string>;
  log: LogEntry[];
  injection: { nodeId: string; status: string } | null;
  hitl: { prompt: string; proposedDirection: string[] } | null;
  brief: Brief | null;
  lastSeq: number;
}

export function initialState(): ConsoleState {
  const nodes: Record<string, NodeStatus> = {};
  NODE_IDS.forEach((id) => (nodes[id] = "idle"));
  const edges: Record<string, EdgeStatus> = {};
  EDGE_IDS.forEach((id) => (edges[id] = "idle"));
  return {
    runState: "idle",
    runLabel: "Idle",
    step: 0,
    totalSteps: TOTAL_STEPS,
    tokens: 0,
    costUsd: 0,
    elapsedMs: 0,
    nodes,
    edges,
    badges: {},
    log: [],
    injection: null,
    hitl: null,
    brief: null,
    lastSeq: -1,
  };
}

/** Founder-friendly explainer copy per workflow step (feature 3). */
export const STAGE_COPY: Record<number, { stage: string; body: string; hard: string }> = {
  1: {
    stage: "1 · Planner is thinking",
    body: "The Planner reads your question and decides what to research — breaking one fuzzy ask into focused, parallel sub-questions.",
    hard: "A vague goal can’t be researched directly. Good decomposition is what makes the rest accurate instead of generic.",
  },
  2: {
    stage: "2 · Researchers search the web",
    body: "Three Researcher agents search and read live web pages at the same time — one per sub-question. Each page is untrusted until screened.",
    hard: "Parallelism is fast but risky: every page is attacker-controllable text. This is where most agents get hijacked.",
  },
  3: {
    stage: "3 · Analyst synthesizes",
    body: "The Analyst merges what the Researchers found into a small set of structured insights — and proposes a direction for the brief.",
    hard: "Raw search results aren’t insight. Turning scattered facts into a defensible point of view is the reasoning-heavy step.",
  },
  4: {
    stage: "4 · Your approval checkpoint",
    body: "The run paused on purpose. Before the Writer drafts anything, you approve or adjust the proposed direction. State is saved while it waits.",
    hard: "Unattended agents that take consequential actions are how things go wrong. A human gate is non-negotiable in production.",
  },
  5: {
    stage: "5 · Writer drafts the brief",
    body: "With your approval, the Writer drafts the brief from the Analyst’s insights. It has no web access — only vetted, in-run material.",
    hard: "Least-privilege matters: the agent that writes shouldn’t be able to browse. That alone closes a whole class of attacks.",
  },
  6: {
    stage: "6 · Critic verifies every claim",
    body: "The Critic checks each key claim in the draft against its cited source — and can send the draft back if anything doesn’t hold up.",
    hard: "This is the anti-hallucination guarantee. Without claim verification, a confident-but-wrong brief is the default LLM failure mode.",
  },
  7: {
    stage: "7 · Error recovery — retry loop",
    body: "The Critic caught an unsupported number and sent the draft back to the Writer instead of releasing it. The run self-corrects.",
    hard: "Graceful retries separate a demo from a system. Real workflows must recover from their own mistakes automatically.",
  },
  8: {
    stage: "8 · Verified brief released",
    body: "Done. Every key claim is grounded in a cited source, the brief is downloadable, and the run is saved to a shareable permalink.",
    hard: "You now have something you can trust and act on — produced transparently, defended against injection, checked by a second agent.",
  },
};

export function reduce(state: ConsoleState, e: CadenzaEvent): ConsoleState {
  const s: ConsoleState = { ...state, lastSeq: Math.max(state.lastSeq, e.seq) };
  switch (e.type) {
    case "run.started":
      return { ...s, totalSteps: e.totalSteps };
    case "run.state":
      return { ...s, runState: e.state, runLabel: e.label };
    case "step.changed":
      return { ...s, step: e.step, totalSteps: e.totalSteps };
    case "node.status": {
      const nodes = { ...s.nodes, [e.nodeId]: e.status };
      const injection =
        s.injection && s.injection.nodeId === e.nodeId && e.status === "active" ? null : s.injection;
      return { ...s, nodes, injection };
    }
    case "edge.status":
      return { ...s, edges: { ...s.edges, [e.edgeId]: e.status } };
    case "meters":
      return { ...s, tokens: e.tokens, costUsd: e.costUsd, elapsedMs: e.elapsedMs ?? s.elapsedMs };
    case "model.routing": {
      const badges = { ...s.badges };
      e.assignments.forEach((a) => (badges[a.nodeId] = a.modelLabel));
      return { ...s, badges };
    }
    case "log":
      return { ...s, log: [...s.log, { seq: e.seq, kind: e.kind, who: e.who, text: e.text }] };
    case "injection.screened":
      return { ...s, injection: { nodeId: e.nodeId, status: e.status } };
    case "hitl.requested":
      return { ...s, hitl: { prompt: e.prompt, proposedDirection: e.proposedDirection } };
    case "hitl.resolved":
      return { ...s, hitl: null };
    case "brief.released":
      return { ...s, brief: e.brief };
    case "run.completed":
      return { ...s, tokens: e.tokens, costUsd: e.costUsd, elapsedMs: e.elapsedMs };
    default:
      // agent.rationale, claim.verified, error → surfaced via the event log
      return s;
  }
}
