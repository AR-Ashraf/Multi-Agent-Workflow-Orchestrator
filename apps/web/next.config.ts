import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Compile the workspace TS package (the shared event schema / topology) directly.
  transpilePackages: ["@cadenza/shared"],
};

export default nextConfig;
