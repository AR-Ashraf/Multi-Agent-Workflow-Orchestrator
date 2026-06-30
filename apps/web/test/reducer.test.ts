import { describe, expect, it } from "vitest";
import {
  buildMockRunEvents,
  EVENT_TYPES,
  parseEvent,
  TOTAL_STEPS,
  type Brief,
  type CadenzaEvent,
  type CadenzaEventType,
} from "@cadenza/shared";
import { initialState, reduce, STAGE_COPY } from "@/lib/console/reducer";

const fold = (events: CadenzaEvent[]): ReturnType<typeof initialState> =>
  events.reduce(reduce, initialState());

const SAMPLE_BRIEF: Brief = {
  title: "T",
  byline: "b",
  query: "q",
  model: "m",
  mode: "demo",
  sections: [{ heading: "h", body: "b" }],
  sources: [{ id: "Source 1", label: "L" }],
  claimsVerified: { verified: 1, total: 1 },
  permalink: "cadenza.devs-core.com/run/x",
};

/** One schema-valid sample per event type — the FE side of the contract. */
const SAMPLES: Record<CadenzaEventType, CadenzaEvent> = {
  "run.started": { runId: "t", seq: 0, ts: 0, type: "run.started", query: "q", provider: "anthropic", modelId: "claude-sonnet", modelLabel: "Claude Sonnet", routingEnabled: true, mode: "demo", totalSteps: 8 },
  "run.state": { runId: "t", seq: 1, ts: 1, type: "run.state", state: "running", label: "Running" },
  "step.changed": { runId: "t", seq: 2, ts: 2, type: "step.changed", step: 1, totalSteps: 8 },
  "node.status": { runId: "t", seq: 3, ts: 3, type: "node.status", nodeId: "planner", status: "active" },
  "edge.status": { runId: "t", seq: 4, ts: 4, type: "edge.status", edgeId: "planner->researcher-a", status: "flow" },
  meters: { runId: "t", seq: 5, ts: 5, type: "meters", tokens: 100, costUsd: 0.01, elapsedMs: 10 },
  "model.routing": { runId: "t", seq: 6, ts: 6, type: "model.routing", routingEnabled: true, assignments: [{ nodeId: "planner", modelLabel: "Sonnet", tier: "smart" }] },
  log: { runId: "t", seq: 7, ts: 7, type: "log", kind: "rationale", who: "Planner", text: "x" },
  "agent.rationale": { runId: "t", seq: 8, ts: 8, type: "agent.rationale", agentId: "planner", summary: "x", items: ["a"] },
  "injection.screened": { runId: "t", seq: 9, ts: 9, type: "injection.screened", nodeId: "researcher-b", status: "blocked", detail: "x" },
  "claim.verified": { runId: "t", seq: 10, ts: 10, type: "claim.verified", claimId: "c1", claimText: "x", sourceId: "Source 1", verdict: "grounded" },
  "hitl.requested": { runId: "t", seq: 11, ts: 11, type: "hitl.requested", prompt: "x", proposedDirection: ["a"], options: ["approve", "adjust"] },
  "hitl.resolved": { runId: "t", seq: 12, ts: 12, type: "hitl.resolved", decision: "approve" },
  "brief.released": { runId: "t", seq: 13, ts: 13, type: "brief.released", brief: SAMPLE_BRIEF },
  "run.completed": { runId: "t", seq: 14, ts: 14, type: "run.completed", tokens: 1, costUsd: 0.1, elapsedMs: 100, claimsVerified: { verified: 3, total: 3 } },
  error: { runId: "t", seq: 15, ts: 15, type: "error", code: "E", message: "m", recoverable: false },
};

describe("event-schema contract (FE)", () => {
  it("has a sample for every event type and nothing extra", () => {
    expect(Object.keys(SAMPLES).sort()).toEqual([...EVENT_TYPES].sort());
    expect(EVENT_TYPES).toHaveLength(16);
  });

  it("every sample validates against the shared schema", () => {
    for (const type of EVENT_TYPES) {
      expect(parseEvent(SAMPLES[type]).type).toBe(type);
    }
  });

  it("the reducer handles every event type without throwing and advances lastSeq", () => {
    for (const type of EVENT_TYPES) {
      const e = SAMPLES[type];
      const next = reduce(initialState(), e);
      expect(next.lastSeq).toBe(e.seq);
    }
  });
});

describe("reduce — targeted state transitions", () => {
  it("run.state drives runState + label", () => {
    const s = reduce(initialState(), SAMPLES["run.state"]);
    expect(s.runState).toBe("running");
    expect(s.runLabel).toBe("Running");
  });

  it("model.routing writes per-node badges", () => {
    const s = reduce(initialState(), SAMPLES["model.routing"]);
    expect(s.badges.planner).toBe("Sonnet");
  });

  it("log appends entries preserving kind/who/text", () => {
    const s = reduce(initialState(), SAMPLES.log);
    expect(s.log).toHaveLength(1);
    expect(s.log[0]).toMatchObject({ kind: "rationale", who: "Planner", text: "x" });
  });

  it("agent.rationale / claim.verified / error are no-ops on state (surfaced via log)", () => {
    for (const type of ["agent.rationale", "claim.verified", "error"] as const) {
      const before = initialState();
      const after = reduce(before, SAMPLES[type]);
      expect({ ...after, lastSeq: -1 }).toEqual(before);
    }
  });
});

describe("injection screening (feature 1)", () => {
  it("an injection.screened block raises the indicator until the node resumes", () => {
    const blocked = fold([
      { runId: "r", seq: 0, ts: 0, type: "node.status", nodeId: "researcher-b", status: "blocked" },
      { runId: "r", seq: 1, ts: 1, type: "injection.screened", nodeId: "researcher-b", status: "blocked", detail: "hidden instructions" },
    ]);
    expect(blocked.injection).toEqual({ nodeId: "researcher-b", status: "blocked" });

    const resumed = reduce(blocked, {
      runId: "r",
      seq: 2,
      ts: 2,
      type: "node.status",
      nodeId: "researcher-b",
      status: "active",
    });
    expect(resumed.injection).toBeNull();
  });
});

describe("HITL checkpoint (feature: human approval)", () => {
  it("pauses with the proposed direction, then clears on resolve", () => {
    const events = buildMockRunEvents();
    const upToPause = events.slice(0, events.findIndex((e) => e.type === "hitl.requested") + 1);
    const paused = fold(upToPause);
    expect(paused.runState).toBe("paused");
    expect(paused.step).toBe(4);
    expect(paused.hitl?.proposedDirection).toHaveLength(3);

    const resolved = reduce(paused, { runId: "demo-run", seq: 9999, ts: 9999, type: "hitl.resolved", decision: "approve" });
    expect(resolved.hitl).toBeNull();
  });
});

describe("full mocked run folds to a verified, cited brief", () => {
  const events = buildMockRunEvents();
  const final = fold(events);

  it("ends complete at the last step", () => {
    expect(final.runState).toBe("done");
    expect(final.runLabel).toBe("Complete");
    expect(final.step).toBe(TOTAL_STEPS);
    expect(final.totalSteps).toBe(8);
  });

  it("releases a brief with 3-of-3 claims verified and a permalink", () => {
    expect(final.brief).not.toBeNull();
    expect(final.brief?.claimsVerified).toEqual({ verified: 3, total: 3 });
    expect(final.brief?.permalink).toBe("cadenza.devs-core.com/run/demo-run");
  });

  it("clears the HITL gate and the injection indicator by the end", () => {
    expect(final.hitl).toBeNull();
    expect(final.injection).toBeNull();
  });

  it("applies cost-routing badges (smart=Sonnet, mechanical=Haiku)", () => {
    expect(final.badges.planner).toBe("Sonnet");
    expect(final.badges.analyst).toBe("Sonnet");
    expect(final.badges["researcher-a"]).toBe("Haiku");
    expect(final.badges.writer).toBe("Haiku");
  });

  it("logs all four tagged kinds (rationale, security, verify, human) plus info", () => {
    const kinds = new Set(final.log.map((l) => l.kind));
    for (const k of ["info", "rationale", "security", "verify", "human"]) {
      expect(kinds.has(k)).toBe(true);
    }
  });

  it("verifies four claims with c3 transitioning unsupported → grounded (retry loop)", () => {
    const claims = events.filter((e) => e.type === "claim.verified");
    expect(claims).toHaveLength(4);
    const c3 = claims.filter((e) => e.claimId === "c3").map((e) => e.verdict);
    expect(c3).toEqual(["unsupported", "grounded"]);
  });

  it("carries a non-zero BYOK spend through to completion", () => {
    expect(final.tokens).toBeGreaterThan(0);
    expect(final.costUsd).toBeGreaterThan(0);
  });
});

describe("explainer copy (feature 3)", () => {
  it("has founder-friendly stage/body/hard copy for steps 1..8", () => {
    for (let step = 1; step <= TOTAL_STEPS; step++) {
      const copy = STAGE_COPY[step];
      expect(copy).toBeDefined();
      expect(copy.stage.length).toBeGreaterThan(0);
      expect(copy.body.length).toBeGreaterThan(0);
      expect(copy.hard.length).toBeGreaterThan(0);
    }
  });
});
