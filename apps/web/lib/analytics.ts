/**
 * Lead-gen funnel instrumentation (CLAUDE.md §11).
 *
 * One dual-path `track()` that works whether the site is wired to GTM (consumes
 * `dataLayer` pushes) or GA4 directly (consumes `gtag('event', …)`). SSR-safe —
 * a no-op on the server. The GA4/GTM IDs are the documented exception to
 * "no keys in the browser" (they are public, client-side measurement ids; no
 * *provider* key ever ships to the client).
 */

export const EVENTS = {
  runStarted: "demo_run_started",
  runCompleted: "demo_run_completed",
  hitlApproved: "demo_hitl_approved",
  bookCall: "book_call", // the conversion event
  briefDownloaded: "brief_downloaded",
  permalinkShared: "permalink_shared",
} as const;

export type FunnelEvent = (typeof EVENTS)[keyof typeof EVENTS];

type Params = Record<string, unknown>;

interface AnalyticsWindow extends Window {
  dataLayer?: unknown[];
  gtag?: (...args: unknown[]) => void;
}

/** Push a funnel event to GTM's dataLayer and (if present) GA4's gtag. */
export function track(event: FunnelEvent | string, params: Params = {}): void {
  if (typeof window === "undefined") return;
  const w = window as AnalyticsWindow;
  w.dataLayer = w.dataLayer ?? [];
  w.dataLayer.push({ event, ...params });
  if (typeof w.gtag === "function") w.gtag("event", event, params);
}

/** The booking destination — real URL in prod, same-page anchor as a fallback. */
export const BOOK_URL = process.env.NEXT_PUBLIC_BOOK_URL || "#book";
