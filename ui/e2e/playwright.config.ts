import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  retries: 2,
  use: {
    baseURL: process.env.CHAT_URL || "http://localhost:3000",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      // Backend server
      command: [
        "cd .. &&",
        "SWARMMIND_DATABASE_URL=sqlite:///e2e_test.db",
        "LLM_PROVIDER=anthropic",
        `ANTHROPIC_API_KEY=${process.env.KIMI_API_KEY || ""}`,
        "ANTHROPIC_BASE_URL=https://api.kimi.com/coding/v1",
        "LLM_MODEL=kimi-for-coding",
        "uv run uvicorn swarmmind.api.supervisor:app --host 127.0.0.1 --port 8000",
      ].join(" "),
      port: 8000,
      timeout: 30_000,
      reuseExistingServer: false,
    },
    {
      // Frontend dev server
      command: "npm run dev",
      cwd: "..",
      port: 3000,
      timeout: 30_000,
      reuseExistingServer: false,
    },
  ],
});
