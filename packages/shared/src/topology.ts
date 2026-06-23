/**
 * Canonical agent-graph topology — the single shape shared by the LangGraph
 * orchestrator (packages/orchestrator) and the on-screen React Flow graph
 * (apps/web). CLAUDE.md §4: "the LangGraph topology and the on-screen React
 * Flow graph are the *same shape*."
 *
 * Node/edge IDs here are stable contract identifiers. The orchestrator emits
 * `node.status` / `edge.status` events keyed by these IDs; the UI maps them to
 * its rendered nodes/edges 1:1.
 */

/** Stable node identifiers, in nominal execution order. */
export const NODE_IDS = [
  "planner",
  "researcher-a",
  "researcher-b",
  "researcher-c",
  "analyst",
  "hitl",
  "writer",
  "critic",
  "output",
] as const;
export type NodeId = (typeof NODE_IDS)[number];

/** How a node is rendered / what role it plays. */
export type NodeKind = "agent" | "hitl" | "output";

export interface GraphNode {
  readonly id: NodeId;
  readonly label: string;
  readonly role: string;
  /** Single-glyph icon used in the graph node + mini-flow. */
  readonly icon: string;
  readonly kind: NodeKind;
  /** True when the node runs an LLM and therefore shows a model badge. */
  readonly hasModel: boolean;
}

export const NODES: readonly GraphNode[] = [
  { id: "planner", label: "Planner", role: "decomposes task", icon: "P", kind: "agent", hasModel: true },
  { id: "researcher-a", label: "Researcher A", role: "market size", icon: "R", kind: "agent", hasModel: true },
  { id: "researcher-b", label: "Researcher B", role: "top competitors", icon: "R", kind: "agent", hasModel: true },
  { id: "researcher-c", label: "Researcher C", role: "pricing signals", icon: "R", kind: "agent", hasModel: true },
  { id: "analyst", label: "Analyst", role: "synthesizes insights", icon: "A", kind: "agent", hasModel: true },
  { id: "hitl", label: "Human approval", role: "you review direction", icon: "✓", kind: "hitl", hasModel: false },
  { id: "writer", label: "Writer", role: "drafts the brief", icon: "W", kind: "agent", hasModel: true },
  { id: "critic", label: "Critic", role: "verifies claims", icon: "C", kind: "agent", hasModel: true },
  { id: "output", label: "Cited brief", role: "verified + downloadable", icon: "★", kind: "output", hasModel: false },
] as const;

/** Stable edge identifiers (`from->to`). */
export const EDGE_IDS = [
  "planner->researcher-a",
  "planner->researcher-b",
  "planner->researcher-c",
  "researcher-a->analyst",
  "researcher-b->analyst",
  "researcher-c->analyst",
  "analyst->hitl",
  "hitl->writer",
  "writer->critic",
  "critic->writer",
  "critic->output",
] as const;
export type EdgeId = (typeof EDGE_IDS)[number];

export type EdgeKind = "normal" | "retry";

export interface GraphEdge {
  readonly id: EdgeId;
  readonly from: NodeId;
  readonly to: NodeId;
  readonly kind: EdgeKind;
}

export const EDGES: readonly GraphEdge[] = [
  { id: "planner->researcher-a", from: "planner", to: "researcher-a", kind: "normal" },
  { id: "planner->researcher-b", from: "planner", to: "researcher-b", kind: "normal" },
  { id: "planner->researcher-c", from: "planner", to: "researcher-c", kind: "normal" },
  { id: "researcher-a->analyst", from: "researcher-a", to: "analyst", kind: "normal" },
  { id: "researcher-b->analyst", from: "researcher-b", to: "analyst", kind: "normal" },
  { id: "researcher-c->analyst", from: "researcher-c", to: "analyst", kind: "normal" },
  { id: "analyst->hitl", from: "analyst", to: "hitl", kind: "normal" },
  { id: "hitl->writer", from: "hitl", to: "writer", kind: "normal" },
  { id: "writer->critic", from: "writer", to: "critic", kind: "normal" },
  // The Critic→Writer retry edge: error recovery when a claim is unsupported.
  { id: "critic->writer", from: "critic", to: "writer", kind: "retry" },
  { id: "critic->output", from: "critic", to: "output", kind: "normal" },
] as const;

export const RESEARCHER_NODE_IDS = ["researcher-a", "researcher-b", "researcher-c"] as const;

/** Total user-facing workflow steps shown in the "Step n/8" meter. */
export const TOTAL_STEPS = 8;
