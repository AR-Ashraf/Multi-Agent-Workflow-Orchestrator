"use client";

import { useMemo } from "react";
import {
  Background,
  Handle,
  Position,
  ReactFlow,
  type Edge,
  type Node,
  type NodeProps,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { EDGES, NODES, type EdgeStatus, type NodeStatus } from "@cadenza/shared";

// Left→right layout; researchers fan out/in, the critic→writer retry curves back.
const POS: Record<string, { x: number; y: number }> = {
  planner: { x: 0, y: 150 },
  "researcher-a": { x: 210, y: 20 },
  "researcher-b": { x: 210, y: 150 },
  "researcher-c": { x: 210, y: 280 },
  analyst: { x: 430, y: 150 },
  hitl: { x: 650, y: 150 },
  writer: { x: 870, y: 150 },
  critic: { x: 1090, y: 150 },
  output: { x: 1310, y: 150 },
};

interface AgentData extends Record<string, unknown> {
  label: string;
  role: string;
  icon: string;
  hasModel: boolean;
  status: NodeStatus;
  badge?: string;
}

function AgentNode({ data }: NodeProps<Node<AgentData>>) {
  return (
    <div className={`agent-node ${data.status !== "idle" ? data.status : ""}`}>
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <span className="an-dot" />
      <div className="an-top">
        <div className="an-ic">{data.icon}</div>
        <div>
          <div className="an-nm">{data.label}</div>
          <div className="an-role">{data.role}</div>
        </div>
      </div>
      {data.hasModel && data.badge ? <div className="an-badge">{data.badge}</div> : null}
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />
    </div>
  );
}

const nodeTypes = { agent: AgentNode };

function edgeAttrs(status: EdgeStatus): Pick<Edge, "animated" | "style"> {
  switch (status) {
    case "flow":
      return { animated: true, style: { stroke: "var(--gold)", strokeWidth: 2.4 } };
    case "done":
      return { animated: false, style: { stroke: "var(--green)", strokeWidth: 2 } };
    case "retry":
      return { animated: false, style: { stroke: "var(--clay)", strokeWidth: 2, strokeDasharray: "4 5" } };
    case "retry-flow":
      return { animated: true, style: { stroke: "var(--clay)", strokeWidth: 2.4, strokeDasharray: "4 5" } };
    default:
      return { animated: false, style: { stroke: "var(--line-2)", strokeWidth: 2 } };
  }
}

export function AgentGraph({
  nodes,
  edges,
  badges,
}: {
  nodes: Record<string, NodeStatus>;
  edges: Record<string, EdgeStatus>;
  badges: Record<string, string>;
}) {
  const rfNodes = useMemo<Node<AgentData>[]>(
    () =>
      NODES.map((n) => ({
        id: n.id,
        type: "agent",
        position: POS[n.id] ?? { x: 0, y: 0 },
        data: {
          label: n.label,
          role: n.role,
          icon: n.icon,
          hasModel: n.hasModel,
          status: nodes[n.id] ?? "idle",
          badge: badges[n.id],
        },
        draggable: false,
        selectable: false,
      })),
    [nodes, badges],
  );

  const rfEdges = useMemo<Edge[]>(
    () =>
      EDGES.map((e) => ({
        id: e.id,
        source: e.from,
        target: e.to,
        type: "default",
        ...edgeAttrs(edges[e.id] ?? "idle"),
      })),
    [edges],
  );

  return (
    <ReactFlow
      className="cadenza-graph"
      nodes={rfNodes}
      edges={rfEdges}
      nodeTypes={nodeTypes}
      fitView
      fitViewOptions={{ padding: 0.18 }}
      minZoom={0.3}
      maxZoom={1.5}
      nodesDraggable={false}
      nodesConnectable={false}
      elementsSelectable={false}
      panOnScroll
      zoomOnPinch
      proOptions={{ hideAttribution: true }}
    >
      <Background gap={26} size={1.3} color="var(--line)" />
    </ReactFlow>
  );
}
