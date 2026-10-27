import { defineConfig, devices } from "@playwright/test";

// Drives the real UI against a running web (:3000) + gateway (:8000).
// Start both before running: `make up` (or make api + make web).
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
