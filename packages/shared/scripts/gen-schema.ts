/**
 * Export the canonical event schema (Zod) to JSON Schema so non-TS consumers —
 * the Python orchestrator's contract test — validate against the SAME contract.
 *
 * Run: pnpm --filter @cadenza/shared gen:schema
 * Output (committed): packages/shared/schema/cadenza-events.schema.json
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { zodToJsonSchema } from "zod-to-json-schema";
import { CadenzaEventSchema } from "../src/events.js";

const jsonSchema = zodToJsonSchema(CadenzaEventSchema, {
  name: "CadenzaEvent",
  $refStrategy: "none",
});

const here = dirname(fileURLToPath(import.meta.url));
const out = resolve(here, "../schema/cadenza-events.schema.json");
mkdirSync(dirname(out), { recursive: true });
writeFileSync(out, `${JSON.stringify(jsonSchema, null, 2)}\n`);
console.log(`wrote ${out}`);
