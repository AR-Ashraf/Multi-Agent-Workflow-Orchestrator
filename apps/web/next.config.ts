import path from "node:path";
import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Self-contained server bundle for the Docker image (CLAUDE.md §13).
  output: "standalone",
  // Trace files from the monorepo root so the workspace package is bundled.
  outputFileTracingRoot: path.join(__dirname, "../../"),
  // Compile the workspace TS package (the shared event schema / topology) directly.
  transpilePackages: ["@cadenza/shared"],
};

export default nextConfig;
