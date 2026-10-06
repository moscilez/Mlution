import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 120_000,
  workers: 1,
  retries: 0,
  use: {
    baseURL: process.env.E2E_FRONTEND_URL ?? "http://localhost:3000",
    browserName: "chromium",
    trace: "retain-on-failure",
  },
});
