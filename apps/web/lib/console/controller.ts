import type { CadenzaEvent, ProviderId } from "@cadenza/shared";
import { buildMockRunEvents } from "@cadenza/shared";

export interface RunOptions {
  query: string;
  provider: string;
  modelId: string;
  routing: boolean;
  apiKey?: string;
}

export interface RunController {
  start(opts: RunOptions, onEvent: (e: CadenzaEvent) => void): void;
  approve(): void;
  adjust(note?: string): void;
  stop(): void;
}

const isTerminal = (e: CadenzaEvent) => e.type === "run.state" && e.state === "done";
const clamp = (v: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, v));

/**
 * Client-side replay of the canonical mocked run (CLAUDE.md §8.6 demo path) —
 * no backend required. Paces events from the fixture's timings and pauses at the
 * HITL checkpoint until the visitor approves/adjusts.
 */
export class MockRunController implements RunController {
  private events: CadenzaEvent[] = [];
  private i = 0;
  private timer: ReturnType<typeof setTimeout> | null = null;
  private onEvent: (e: CadenzaEvent) => void = () => {};
  private paused = false;
  private decision: { decision: string; note?: string } | null = null;

  private static readonly SPEED = 0.55;
  private static readonly MIN_DELAY = 24;
  private static readonly MAX_DELAY = 1100;

  start(opts: RunOptions, onEvent: (e: CadenzaEvent) => void): void {
    this.stop();
    this.onEvent = onEvent;
    this.events = buildMockRunEvents({
      runId: Math.random().toString(36).slice(2, 10),
      query: opts.query,
      provider: opts.provider as ProviderId,
      modelId: opts.modelId,
      routingEnabled: opts.routing,
      mode: opts.apiKey ? "live" : "demo",
    });
    this.i = 0;
    this.paused = false;
    this.decision = null;
    this.tick();
  }

  private tick = (): void => {
    if (this.i >= this.events.length) return;
    const e = this.events[this.i]!;
    if (e.type === "hitl.requested" && !this.decision) {
      this.onEvent(e);
      this.i += 1;
      this.paused = true;
      return; // wait for approve()/adjust()
    }
    this.onEvent(this.patch(e));
    this.i += 1;
    const next = this.events[this.i];
    const delay = next
      ? clamp((next.ts - e.ts) * MockRunController.SPEED, MockRunController.MIN_DELAY, MockRunController.MAX_DELAY)
      : 0;
    this.timer = setTimeout(this.tick, delay);
  };

  private patch(e: CadenzaEvent): CadenzaEvent {
    if (this.decision?.decision === "adjust") {
      if (e.type === "hitl.resolved") return { ...e, decision: "adjust", note: this.decision.note };
      if (e.type === "log" && e.who === "You")
        return { ...e, text: "✎ adjusted scope. Resuming the run." };
    }
    return e;
  }

  private resume(decision: string, note?: string): void {
    if (!this.paused) return;
    this.decision = { decision, note };
    this.paused = false;
    this.tick();
  }

  approve(): void {
    this.resume("approve");
  }
  adjust(note?: string): void {
    this.resume("adjust", note);
  }
  stop(): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = null;
  }
}

/** Drives a real run against the FastAPI gateway over SSE. */
export class SseRunController implements RunController {
  private es: EventSource | null = null;
  private runId: string | null = null;
  private readonly base: string;

  constructor(base: string) {
    this.base = base.replace(/\/$/, "");
  }

  start(opts: RunOptions, onEvent: (e: CadenzaEvent) => void): void {
    this.stop();
    void (async () => {
      const res = await fetch(`${this.base}/api/runs`, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({
          query: opts.query,
          provider: opts.provider,
          model: opts.modelId,
          routing: opts.routing,
          api_key: opts.apiKey || null,
        }),
      });
      if (!res.ok) throw new Error(`start failed: ${res.status}`);
      const { run_id: runId } = (await res.json()) as { run_id: string };
      this.runId = runId;
      const es = new EventSource(`${this.base}/api/runs/${runId}/events`);
      es.onmessage = (m) => {
        try {
          const event = JSON.parse(m.data) as CadenzaEvent;
          onEvent(event);
          if (isTerminal(event)) es.close();
        } catch {
          /* ignore malformed frames */
        }
      };
      this.es = es;
    })();
  }

  private decide(decision: string, note?: string): void {
    if (!this.runId) return;
    void fetch(`${this.base}/api/runs/${this.runId}/decision`, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ decision, note: note ?? null }),
    });
  }

  approve(): void {
    this.decide("approve");
  }
  adjust(note?: string): void {
    this.decide("adjust", note);
  }
  stop(): void {
    this.es?.close();
    this.es = null;
  }
}

export function createController(): RunController {
  const base = process.env.NEXT_PUBLIC_API_BASE;
  return base ? new SseRunController(base) : new MockRunController();
}
