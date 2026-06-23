import { describe, it, expect } from "vitest";
import {
  CadenzaEventSchema,
  EVENT_TYPES,
  parseEvent,
  safeParseEvent,
  type CadenzaEvent,
  type CadenzaEventType,
} from "../events.js";

/** Minimal valid sample for every event type (used to prove the union accepts each). */
const SAMPLES: Record<CadenzaEventType, Record<string, unknown>> = {
  "run.started": {
    type: "run.started", query: "q", provider: "anthropic", modelId: "claude-sonnet",
    modelLabel: "Claude Sonnet", routingEnabled: true, mode: "demo", totalSteps: 8,
  },
  "run.state": { type: "run.state", state: "running", label: "Running" },
  "step.changed": { type: "step.changed", step: 1, totalSteps: 8 },
  "node.status": { type: "node.status", nodeId: "planner", status: "active" },
  "edge.status": { type: "edge.status", edgeId: "planner->researcher-a", status: "flow" },
  meters: { type: "meters", tokens: 100, costUsd: 0.01 },
  "model.routing": {
    type: "model.routing", routingEnabled: true,
    assignments: [{ nodeId: "planner", modelLabel: "Sonnet", tier: "smart" }],
  },
  log: { type: "log", kind: "rationale", who: "Planner", text: "chose 3 sub-questions" },
  "agent.rationale": { type: "agent.rationale", agentId: "critic", summary: "retry", verdict: "retry" },
  "injection.screened": { type: "injection.screened", nodeId: "researcher-b", status: "blocked", detail: "prompt injection" },
  "claim.verified": { type: "claim.verified", claimId: "c1", claimText: "x", sourceId: "Source 1", verdict: "grounded" },
  "hitl.requested": { type: "hitl.requested", prompt: "approve?", proposedDirection: ["a", "b"] },
  "hitl.resolved": { type: "hitl.resolved", decision: "approve" },
  "brief.released": {
    type: "brief.released",
    brief: {
      title: "T", byline: "b", query: "q", model: "Sonnet", mode: "demo",
      sections: [{ heading: "H", body: "B" }],
      sources: [{ id: "Source 1", label: "L" }],
      claimsVerified: { verified: 3, total: 3 }, permalink: "agents.devs-core.com/run/x",
    },
  },
  "run.completed": { type: "run.completed", tokens: 100, costUsd: 0.2, elapsedMs: 1000, claimsVerified: { verified: 3, total: 3 } },
  error: { type: "error", code: "E", message: "m" },
};

const withEnvelope = (s: Record<string, unknown>): Record<string, unknown> => ({
  runId: "r1", seq: 0, ts: 0, ...s,
});

describe("event schema contract", () => {
  it("EVENT_TYPES matches the union members exactly", () => {
    expect(new Set(EVENT_TYPES)).toEqual(new Set(Object.keys(SAMPLES)));
    expect(EVENT_TYPES.length).toBe(16);
  });

  it.each(EVENT_TYPES)("accepts a valid %s event", (type) => {
    const parsed = parseEvent(withEnvelope(SAMPLES[type]));
    expect(parsed.type).toBe(type);
  });

  it("discriminates on `type`", () => {
    const e = parseEvent(withEnvelope(SAMPLES["claim.verified"])) as Extract<CadenzaEvent, { type: "claim.verified" }>;
    expect(e.verdict).toBe("grounded");
  });

  it("applies declared defaults", () => {
    const e = parseEvent(withEnvelope(SAMPLES["hitl.requested"])) as Extract<CadenzaEvent, { type: "hitl.requested" }>;
    expect(e.options).toEqual(["approve", "adjust"]);
    const err = parseEvent(withEnvelope(SAMPLES.error)) as Extract<CadenzaEvent, { type: "error" }>;
    expect(err.recoverable).toBe(false);
  });

  it("rejects an unknown event type", () => {
    expect(safeParseEvent(withEnvelope({ type: "totally.bogus" })).success).toBe(false);
  });

  it("rejects a bad enum value", () => {
    expect(safeParseEvent(withEnvelope({ type: "node.status", nodeId: "planner", status: "exploded" })).success).toBe(false);
  });

  it("rejects an unknown nodeId / edgeId", () => {
    expect(safeParseEvent(withEnvelope({ type: "node.status", nodeId: "wizard", status: "active" })).success).toBe(false);
    expect(safeParseEvent(withEnvelope({ type: "edge.status", edgeId: "a->b", status: "flow" })).success).toBe(false);
  });

  it("requires the run envelope (runId/seq/ts)", () => {
    expect(CadenzaEventSchema.safeParse(SAMPLES["run.state"]).success).toBe(false);
  });

  it("rejects negative meters", () => {
    expect(safeParseEvent(withEnvelope({ type: "meters", tokens: -1, costUsd: 0 })).success).toBe(false);
  });
});
