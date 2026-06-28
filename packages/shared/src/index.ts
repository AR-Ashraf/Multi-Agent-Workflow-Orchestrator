/**
 * @cadenza/shared — the FE/BE contract.
 *
 * The event schema, the agent-graph topology, and the provider/model registry,
 * shared by the LangGraph orchestrator, the FastAPI gateway, and the Next.js UI.
 */

export * from "./topology";
export * from "./models";
export * from "./events";
export { buildMockRunEvents, type MockRunParams } from "./fixtures/mock-run";
