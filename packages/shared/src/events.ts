/**
 * THE EVENT SCHEMA — Cadenza's FE/BE contract (CLAUDE.md §4, §5).
 *
 * Single source of truth for everything the LangGraph orchestrator emits onto
 * Redis pub/sub and everything the React UI renders over SSE. It deliberately
 * carries more than results:
 *   - decision rationale            → `agent.rationale`   (feature 2, "WHY" log)
 *   - injection-screening status    → `injection.screened`(feature 1, "SECURITY")
 *   - claim-verification verdicts   → `claim.verified`    (feature 4, "VERIFY")
 *   - human-in-the-loop checkpoint  → `hitl.requested/resolved` ("HUMAN")
 *   - BYOK per-step model routing   → `run.started` + `model.routing`
 *
 * Every emitted event is validated against `CadenzaEventSchema` before it
 * touches Redis/Postgres or the SSE stream (output screening, CLAUDE.md §9).
 */

import { z } from "zod";
import { EDGE_IDS, NODE_IDS } from "./topology";
import { PROVIDER_IDS } from "./models";

/* ----------------------------- shared enums ------------------------------ */

export const NodeIdSchema = z.enum(NODE_IDS);
export const EdgeIdSchema = z.enum(EDGE_IDS);
export const ProviderIdSchema = z.enum(PROVIDER_IDS);

export const RunStateSchema = z.enum(["idle", "running", "paused", "done", "error"]);
export type RunState = z.infer<typeof RunStateSchema>;

export const RunModeSchema = z.enum(["live", "demo"]);
export type RunMode = z.infer<typeof RunModeSchema>;

export const NodeStatusSchema = z.enum(["idle", "active", "done", "blocked", "hitl"]);
export type NodeStatus = z.infer<typeof NodeStatusSchema>;

export const EdgeStatusSchema = z.enum(["idle", "flow", "done", "retry", "retry-flow"]);
export type EdgeStatus = z.infer<typeof EdgeStatusSchema>;

/** Event-log entry kind. `info` has no tag; the rest map to WHY/SECURITY/VERIFY/HUMAN. */
export const LogKindSchema = z.enum(["info", "rationale", "security", "verify", "human"]);
export type LogKind = z.infer<typeof LogKindSchema>;

export const ModelTierSchema = z.enum(["smart", "fast"]);
export const ScreenStatusSchema = z.enum(["passed", "sanitized", "blocked"]);
export type ScreenStatus = z.infer<typeof ScreenStatusSchema>;

export const ClaimVerdictSchema = z.enum(["grounded", "unsupported"]);
export type ClaimVerdict = z.infer<typeof ClaimVerdictSchema>;

export const CriticVerdictSchema = z.enum(["accept", "retry"]);
export type CriticVerdict = z.infer<typeof CriticVerdictSchema>;

export const HitlDecisionSchema = z.enum(["approve", "adjust"]);
export type HitlDecision = z.infer<typeof HitlDecisionSchema>;

/* ----------------------------- nested shapes ----------------------------- */

export const ModelAssignmentSchema = z.object({
  nodeId: NodeIdSchema,
  modelLabel: z.string().min(1),
  tier: ModelTierSchema,
});

export const ClaimsVerifiedSchema = z.object({
  verified: z.number().int().nonnegative(),
  total: z.number().int().nonnegative(),
});

export const BriefSourceSchema = z.object({
  id: z.string().min(1),
  label: z.string().min(1),
  url: z.string().url().optional(),
});

export const BriefSectionSchema = z.object({
  heading: z.string().min(1),
  /** Body text; may embed inline citation markers like [Source 1]. */
  body: z.string(),
});

export const BriefSchema = z.object({
  title: z.string().min(1),
  byline: z.string(),
  query: z.string(),
  model: z.string(),
  mode: RunModeSchema,
  sections: z.array(BriefSectionSchema),
  sources: z.array(BriefSourceSchema),
  claimsVerified: ClaimsVerifiedSchema,
  permalink: z.string().min(1),
});
export type Brief = z.infer<typeof BriefSchema>;

/* ------------------------------- base shape ------------------------------ */

/**
 * Every event carries a monotonic `seq` (for ordering + reconnect/resume — the
 * client re-subscribes with the last seq it saw) and a `ts` (ms epoch).
 */
const base = z.object({
  runId: z.string().min(1),
  seq: z.number().int().nonnegative(),
  ts: z.number().int().nonnegative(),
});

/* ------------------------------- event union ----------------------------- */

export const RunStartedEvent = base.extend({
  type: z.literal("run.started"),
  query: z.string(),
  provider: ProviderIdSchema,
  modelId: z.string().min(1),
  modelLabel: z.string().min(1),
  routingEnabled: z.boolean(),
  mode: RunModeSchema,
  totalSteps: z.number().int().positive(),
});

export const RunStateEvent = base.extend({
  type: z.literal("run.state"),
  state: RunStateSchema,
  label: z.string(),
});

export const StepChangedEvent = base.extend({
  type: z.literal("step.changed"),
  step: z.number().int().nonnegative(),
  totalSteps: z.number().int().positive(),
});

export const NodeStatusEvent = base.extend({
  type: z.literal("node.status"),
  nodeId: NodeIdSchema,
  status: NodeStatusSchema,
});

export const EdgeStatusEvent = base.extend({
  type: z.literal("edge.status"),
  edgeId: EdgeIdSchema,
  status: EdgeStatusSchema,
});

export const MetersEvent = base.extend({
  type: z.literal("meters"),
  /** Cumulative tokens consumed so far this run. */
  tokens: z.number().int().nonnegative(),
  /** Cumulative estimated cost in USD — the VISITOR's spend (BYOK). */
  costUsd: z.number().nonnegative(),
  elapsedMs: z.number().int().nonnegative().optional(),
});

export const ModelRoutingEvent = base.extend({
  type: z.literal("model.routing"),
  routingEnabled: z.boolean(),
  /** Per-node model badge/tier — drives the graph's model badges from real events. */
  assignments: z.array(ModelAssignmentSchema).min(1),
});

export const LogEvent = base.extend({
  type: z.literal("log"),
  kind: LogKindSchema,
  who: z.string().min(1),
  text: z.string(),
  nodeId: NodeIdSchema.optional(),
});

/** Decision rationale as real fields, not prose (feature 2). */
export const AgentRationaleEvent = base.extend({
  type: z.literal("agent.rationale"),
  agentId: NodeIdSchema,
  summary: z.string().min(1),
  /** e.g. the Planner's chosen sub-questions. */
  items: z.array(z.string()).optional(),
  /** e.g. the Critic's accept/retry verdict. */
  verdict: CriticVerdictSchema.optional(),
});

/** Injection guard outcome on a fetched/tool result (feature 1, CLAUDE.md §9). */
export const InjectionScreenedEvent = base.extend({
  type: z.literal("injection.screened"),
  nodeId: NodeIdSchema,
  status: ScreenStatusSchema,
  sourceUrl: z.string().optional(),
  detail: z.string(),
});

/** A single claim checked against its cited source (feature 4). */
export const ClaimVerifiedEvent = base.extend({
  type: z.literal("claim.verified"),
  claimId: z.string().min(1),
  claimText: z.string(),
  sourceId: z.string().min(1),
  verdict: ClaimVerdictSchema,
  detail: z.string().optional(),
});

export const HitlRequestedEvent = base.extend({
  type: z.literal("hitl.requested"),
  prompt: z.string(),
  proposedDirection: z.array(z.string()),
  options: z.array(HitlDecisionSchema).default(["approve", "adjust"]),
});

export const HitlResolvedEvent = base.extend({
  type: z.literal("hitl.resolved"),
  decision: HitlDecisionSchema,
  note: z.string().optional(),
});

export const BriefReleasedEvent = base.extend({
  type: z.literal("brief.released"),
  brief: BriefSchema,
});

export const RunCompletedEvent = base.extend({
  type: z.literal("run.completed"),
  tokens: z.number().int().nonnegative(),
  costUsd: z.number().nonnegative(),
  elapsedMs: z.number().int().nonnegative(),
  claimsVerified: ClaimsVerifiedSchema,
});

export const ErrorEvent = base.extend({
  type: z.literal("error"),
  code: z.string().min(1),
  message: z.string(),
  recoverable: z.boolean().default(false),
});

export const CadenzaEventSchema = z.discriminatedUnion("type", [
  RunStartedEvent,
  RunStateEvent,
  StepChangedEvent,
  NodeStatusEvent,
  EdgeStatusEvent,
  MetersEvent,
  ModelRoutingEvent,
  LogEvent,
  AgentRationaleEvent,
  InjectionScreenedEvent,
  ClaimVerifiedEvent,
  HitlRequestedEvent,
  HitlResolvedEvent,
  BriefReleasedEvent,
  RunCompletedEvent,
  ErrorEvent,
]);

export type CadenzaEvent = z.infer<typeof CadenzaEventSchema>;
export type CadenzaEventType = CadenzaEvent["type"];

/** All event `type` discriminants, for exhaustiveness checks/tests. */
export const EVENT_TYPES = [
  "run.started",
  "run.state",
  "step.changed",
  "node.status",
  "edge.status",
  "meters",
  "model.routing",
  "log",
  "agent.rationale",
  "injection.screened",
  "claim.verified",
  "hitl.requested",
  "hitl.resolved",
  "brief.released",
  "run.completed",
  "error",
] as const satisfies readonly CadenzaEventType[];

/** Parse + validate an unknown value as a CadenzaEvent (throws on failure). */
export function parseEvent(value: unknown): CadenzaEvent {
  return CadenzaEventSchema.parse(value);
}

/** Safe variant — returns a discriminated success/error result. */
export function safeParseEvent(value: unknown): z.SafeParseReturnType<unknown, CadenzaEvent> {
  return CadenzaEventSchema.safeParse(value);
}

/** Serialize an event to a single SSE `data:` line payload (JSON). */
export function serializeEvent(event: CadenzaEvent): string {
  return JSON.stringify(event);
}
