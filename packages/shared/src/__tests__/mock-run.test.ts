import { describe, it, expect } from "vitest";
import { buildMockRunEvents } from "../fixtures/mock-run.js";
import { CadenzaEventSchema, type CadenzaEvent } from "../events.js";

function build(): CadenzaEvent[] {
  return buildMockRunEvents({ runId: "test-run", routingEnabled: true });
}

describe("mocked run fixture", () => {
  it("every event validates against the schema contract", () => {
    for (const e of build()) {
      const r = CadenzaEventSchema.safeParse(e);
      if (!r.success) throw new Error(`invalid ${e.type} @seq ${e.seq}: ${r.error.message}`);
      expect(r.success).toBe(true);
    }
  });

  it("seq is strictly increasing and ts is monotonic", () => {
    const events = build();
    for (let i = 1; i < events.length; i++) {
      expect(events[i]!.seq).toBe(events[i - 1]!.seq + 1);
      expect(events[i]!.ts).toBeGreaterThanOrEqual(events[i - 1]!.ts);
    }
  });

  it("starts with run.started and ends run.completed → run.state done", () => {
    const events = build();
    expect(events[0]!.type).toBe("run.started");
    const completed = events.findIndex((e) => e.type === "run.completed");
    const last = events[events.length - 1]!;
    expect(completed).toBeGreaterThan(0);
    expect(last).toMatchObject({ type: "run.state", state: "done" });
  });

  it("fires the injection block on Researcher B (feature 1)", () => {
    const inj = build().filter((e) => e.type === "injection.screened");
    expect(inj).toHaveLength(1);
    expect(inj[0]).toMatchObject({ nodeId: "researcher-b", status: "blocked" });
  });

  it("pauses for HITL then resolves with approval (feature: HITL)", () => {
    const events = build();
    const reqIdx = events.findIndex((e) => e.type === "hitl.requested");
    const resIdx = events.findIndex((e) => e.type === "hitl.resolved");
    expect(reqIdx).toBeGreaterThan(0);
    expect(resIdx).toBeGreaterThan(reqIdx);
    expect(events.some((e) => e.type === "run.state" && e.state === "paused")).toBe(true);
  });

  it("runs the Critic retry loop on an unsupported claim (feature 4 + recovery)", () => {
    const events = build();
    const claims = events.filter((e) => e.type === "claim.verified");
    // 4 verdicts: c1✓, c2✓, c3✗ (unsupported) then c3✓ (re-checked)
    expect(claims).toHaveLength(4);
    expect(claims.some((c) => c.verdict === "unsupported")).toBe(true);
    expect(events.some((e) => e.type === "agent.rationale" && e.verdict === "retry")).toBe(true);
    expect(events.some((e) => e.type === "edge.status" && e.edgeId === "critic->writer" && e.status === "retry-flow")).toBe(true);
  });

  it("carries decision rationale as structured fields (feature 2)", () => {
    const events = build();
    const planner = events.find((e) => e.type === "agent.rationale" && e.agentId === "planner");
    expect(planner).toBeDefined();
    expect((planner as Extract<CadenzaEvent, { type: "agent.rationale" }>).items).toEqual([
      "market size", "top competitors", "pricing",
    ]);
  });

  it("releases a cited brief with all key claims verified", () => {
    const released = build().find((e) => e.type === "brief.released") as
      | Extract<CadenzaEvent, { type: "brief.released" }>
      | undefined;
    expect(released).toBeDefined();
    const brief = released!.brief;
    expect(brief.sources.length).toBeGreaterThanOrEqual(3);
    expect(brief.claimsVerified).toEqual({ verified: 3, total: 3 });
    expect(brief.permalink).toContain("test-run");
  });

  it("demo mode never claims live billing; live mode does", () => {
    const demo = buildMockRunEvents({ mode: "demo" }).find((e) => e.type === "log" && e.who === "Setup");
    const live = buildMockRunEvents({ mode: "live" }).find((e) => e.type === "log" && e.who === "Setup");
    expect((demo as Extract<CadenzaEvent, { type: "log" }>).text).toMatch(/cached demo|nothing billed/i);
    expect((live as Extract<CadenzaEvent, { type: "log" }>).text).toMatch(/your API key|billed to your account/i);
  });
});
