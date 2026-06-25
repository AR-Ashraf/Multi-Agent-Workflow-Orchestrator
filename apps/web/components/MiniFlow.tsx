"use client";

import { useEffect, useState } from "react";

const NODES = [
  { ic: "P", b: "Planner", s: "breaks the question into sub-tasks" },
  { ic: "R", b: "Researchers ×3", s: "search + read the web in parallel" },
  { ic: "A", b: "Analyst", s: "turns findings into insights" },
  { ic: "✓", b: "You approve", s: "human checkpoint before writing" },
  { ic: "C", b: "Critic", s: "verifies every claim vs. sources" },
];

export function MiniFlow() {
  const [active, setActive] = useState(0);

  useEffect(() => {
    const t = setInterval(() => setActive((p) => (p + 1) % NODES.length), 1100);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="mini-flow" aria-hidden="true">
      {NODES.map((n, idx) => (
        <div key={n.b} className={`mini-node ${idx === active ? "on" : ""}`}>
          <div className="mn-ic">{n.ic}</div>
          <div>
            <b>{n.b}</b>
            <small>{n.s}</small>
          </div>
        </div>
      ))}
    </div>
  );
}
