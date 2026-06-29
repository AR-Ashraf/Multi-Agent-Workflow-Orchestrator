import { defineConfig, devices } from "@playwright/test";

/**
 * Drives the live Console against the client-side demo replay (no backend /
 * no API key needed — CLAUDE.md §8.6). Runs the happy path on a desktop and a
 * ≤414px phone viewport to guard the mobile-first layout.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  reporter: "list",
  timeout: 60_000,
  expect: { timeout: 20_000 },
  use: { baseURL: "http://localhost:3000", trace: "on-first-retry" },
  webServer: {
    command: "pnpm dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "mobile", use: { ...devices["Pixel 5"] } }, // 393px wide, has touch
  ],
});
