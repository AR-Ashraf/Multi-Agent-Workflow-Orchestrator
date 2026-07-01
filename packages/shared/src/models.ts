/**
 * Provider / model registry — shared by the BYOK config panel (apps/web) and
 * the provider-agnostic LLM client layer (packages/orchestrator/agents).
 *
 * BYOK (CLAUDE.md §5/§6): visitors run on their own provider + key, billed to
 * them. This registry is data-driven so adding a provider/model is a one-line
 * change. Keys themselves NEVER live here and never reach the client bundle as
 * anything but the user's own transient input.
 */

import type { NodeId } from "./topology";

export const PROVIDER_IDS = ["anthropic", "openai", "google", "groq", "mistral"] as const;
export type ProviderId = (typeof PROVIDER_IDS)[number];

/** Which model tier a step runs on. Reasoning steps = "smart"; mechanical = "fast". */
export type ModelTier = "smart" | "fast";

export interface ModelOption {
  /** Stable per-provider model id (sent to the backend). */
  readonly id: string;
  /** Human-readable label shown in the model <select>. */
  readonly label: string;
  /** Short badge shown on graph nodes. */
  readonly badge: string;
}

export interface ProviderInfo {
  readonly id: ProviderId;
  readonly label: string;
  /** Placeholder shown in the API-key input. */
  readonly keyHint: string;
  /** Badge for the provider's cheap/fast model (used for mechanical steps when routing is on). */
  readonly fastBadge: string;
  readonly models: readonly ModelOption[];
  /** Index into `models` used as the default selection. */
  readonly defaultModelIndex: number;
  /** Whether a real BYOK adapter exists today (else the UI shows "coming soon"). */
  readonly supported: boolean;
}

export const PROVIDERS: Record<ProviderId, ProviderInfo> = {
  anthropic: {
    id: "anthropic",
    label: "Anthropic (Claude)",
    supported: true,
    keyHint: "sk-ant-...",
    fastBadge: "Haiku",
    models: [
      { id: "claude-opus", label: "Claude Opus", badge: "Opus" },
      { id: "claude-sonnet", label: "Claude Sonnet", badge: "Sonnet" },
      { id: "claude-haiku", label: "Claude Haiku", badge: "Haiku" },
    ],
    defaultModelIndex: 1,
  },
  openai: {
    id: "openai",
    label: "OpenAI (GPT)",
    supported: true,
    keyHint: "sk-...",
    fastBadge: "mini",
    models: [
      { id: "gpt-5", label: "GPT-5", badge: "GPT-5" },
      { id: "gpt-5-mini", label: "GPT-5 mini", badge: "mini" },
      { id: "gpt-4.1", label: "GPT-4.1", badge: "4.1" },
      { id: "o4-mini", label: "o4-mini", badge: "o4-mini" },
    ],
    defaultModelIndex: 0,
  },
  google: {
    id: "google",
    label: "Google (Gemini)",
    supported: false,
    keyHint: "AIza...",
    fastBadge: "Flash",
    models: [
      { id: "gemini-2.5-pro", label: "Gemini 2.5 Pro", badge: "2.5 Pro" },
      { id: "gemini-2.5-flash", label: "Gemini 2.5 Flash", badge: "Flash" },
    ],
    defaultModelIndex: 0,
  },
  groq: {
    id: "groq",
    label: "Groq (Llama / Mixtral)",
    supported: false,
    keyHint: "gsk_...",
    fastBadge: "8B",
    models: [
      { id: "llama-3.3-70b", label: "Llama 3.3 70B", badge: "70B" },
      { id: "llama-3.1-8b", label: "Llama 3.1 8B", badge: "8B" },
      { id: "mixtral-8x7b", label: "Mixtral 8x7B", badge: "Mixtral" },
    ],
    defaultModelIndex: 0,
  },
  mistral: {
    id: "mistral",
    label: "Mistral",
    supported: false,
    keyHint: "...",
    fastBadge: "Small",
    models: [
      { id: "mistral-large", label: "Mistral Large", badge: "Large" },
      { id: "mistral-small", label: "Mistral Small", badge: "Small" },
    ],
    defaultModelIndex: 0,
  },
};

/** Reasoning-heavy steps — always run on the visitor's selected ("smart") model. */
export const SMART_NODES: readonly NodeId[] = ["planner", "analyst", "critic"];

/** Mechanical steps — downgraded to the provider's fast model when cost-routing is on. */
export const MECHANICAL_NODES: readonly NodeId[] = [
  "researcher-a",
  "researcher-b",
  "researcher-c",
  "writer",
];

export interface ModelAssignment {
  readonly nodeId: NodeId;
  readonly modelLabel: string;
  readonly tier: ModelTier;
}

export function getProvider(provider: ProviderId): ProviderInfo {
  return PROVIDERS[provider];
}

export function resolveModel(provider: ProviderId, modelId: string): ModelOption {
  const info = PROVIDERS[provider];
  return info.models.find((m) => m.id === modelId) ?? info.models[info.defaultModelIndex]!;
}

/**
 * Decide which model badge each model-bearing node shows, given the selected
 * model and whether auto cost-routing is on. Mirrors the prototype's
 * `setModelBadges`: smart nodes get the selected model; mechanical nodes get
 * the provider's fast model when routing is enabled (CLAUDE.md §8.4).
 */
export function assignModels(
  provider: ProviderId,
  modelId: string,
  routingEnabled: boolean,
): ModelAssignment[] {
  const info = PROVIDERS[provider];
  const selected = resolveModel(provider, modelId);
  const smartBadge = selected.badge;
  const mechanicalBadge = routingEnabled ? info.fastBadge : selected.badge;

  return [
    ...SMART_NODES.map((nodeId): ModelAssignment => ({ nodeId, modelLabel: smartBadge, tier: "smart" })),
    ...MECHANICAL_NODES.map(
      (nodeId): ModelAssignment => ({
        nodeId,
        modelLabel: mechanicalBadge,
        tier: routingEnabled ? "fast" : "smart",
      }),
    ),
  ];
}
