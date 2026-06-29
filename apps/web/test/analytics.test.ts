import { afterEach, describe, expect, it, vi } from "vitest";
import { EVENTS, track } from "@/lib/analytics";

interface TestGlobal {
  window?: { dataLayer?: unknown[]; gtag?: (...a: unknown[]) => void };
}
const g = globalThis as unknown as TestGlobal;

afterEach(() => {
  delete g.window;
});

describe("analytics track()", () => {
  it("is a no-op on the server (no window)", () => {
    expect(g.window).toBeUndefined();
    expect(() => track(EVENTS.bookCall)).not.toThrow();
  });

  it("pushes the event + params onto the GTM dataLayer", () => {
    g.window = {};
    track(EVENTS.runStarted, { mode: "demo" });
    expect(g.window.dataLayer).toEqual([{ event: "demo_run_started", mode: "demo" }]);
  });

  it("also forwards to GA4 gtag when present", () => {
    const gtag = vi.fn();
    g.window = { gtag };
    track(EVENTS.bookCall, { location: "nav" });
    expect(gtag).toHaveBeenCalledWith("event", "book_call", { location: "nav" });
  });

  it("exposes the documented funnel event names (§11)", () => {
    expect(Object.values(EVENTS)).toEqual(
      expect.arrayContaining([
        "demo_run_started",
        "demo_run_completed",
        "demo_hitl_approved",
        "book_call",
      ]),
    );
  });
});
