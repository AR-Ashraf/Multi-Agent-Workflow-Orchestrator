import { describe, it, expect } from "vitest";
import { NODES, NODE_IDS, EDGES, EDGE_IDS, RESEARCHER_NODE_IDS, TOTAL_STEPS } from "../topology.js";
import { assignModels, SMART_NODES, MECHANICAL_NODES } from "../models.js";

describe("graph topology", () => {
  it("has 9 nodes and 11 edges with unique ids", () => {
    expect(NODES).toHaveLength(9);
    expect(EDGES).toHaveLength(11);
    expect(new Set(NODE_IDS).size).toBe(NODE_IDS.length);
    expect(new Set(EDGE_IDS).size).toBe(EDGE_IDS.length);
  });

  it("every edge connects two real nodes", () => {
    const ids = new Set<string>(NODE_IDS);
    for (const e of EDGES) {
      expect(ids.has(e.from)).toBe(true);
      expect(ids.has(e.to)).toBe(true);
    }
  });

  it("has exactly one retry edge: critic → writer", () => {
    const retry = EDGES.filter((e) => e.kind === "retry");
    expect(retry).toHaveLength(1);
    expect(retry[0]).toMatchObject({ from: "critic", to: "writer" });
  });

  it("planner fans out to all three researchers; analyst fans them in", () => {
    expect(EDGES.filter((e) => e.from === "planner").map((e) => e.to).sort()).toEqual([...RESEARCHER_NODE_IDS].sort());
    expect(EDGES.filter((e) => e.to === "analyst").map((e) => e.from).sort()).toEqual([...RESEARCHER_NODE_IDS].sort());
  });

  it("only the HITL and output nodes lack a model badge", () => {
    const noModel = NODES.filter((n) => !n.hasModel).map((n) => n.id).sort();
    expect(noModel).toEqual(["hitl", "output"]);
  });

  it("TOTAL_STEPS is 8", () => {
    expect(TOTAL_STEPS).toBe(8);
  });
});

describe("model routing", () => {
  it("smart + mechanical nodes cover every model-bearing node exactly once", () => {
    const modelNodes = NODES.filter((n) => n.hasModel).map((n) => n.id).sort();
    expect([...SMART_NODES, ...MECHANICAL_NODES].sort()).toEqual(modelNodes);
  });

  it("routing on → mechanical steps use the fast badge, smart steps the selected model", () => {
    const a = assignModels("anthropic", "claude-sonnet", true);
    const byId = Object.fromEntries(a.map((x) => [x.nodeId, x]));
    expect(byId.planner).toMatchObject({ modelLabel: "Sonnet", tier: "smart" });
    expect(byId["researcher-a"]).toMatchObject({ modelLabel: "Haiku", tier: "fast" });
    expect(byId.writer).toMatchObject({ modelLabel: "Haiku", tier: "fast" });
  });

  it("routing off → every node uses the selected model", () => {
    const a = assignModels("anthropic", "claude-sonnet", false);
    expect(a.every((x) => x.modelLabel === "Sonnet")).toBe(true);
    expect(a.every((x) => x.tier === "smart")).toBe(true);
  });
});
