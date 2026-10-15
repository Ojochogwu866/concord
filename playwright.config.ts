import { defineConfig, devices } from "@playwright/test";

const baseURL = process.env.BASE_URL ?? "http://localhost:8001";
const viewportWidths = { mobile: 360, tablet: 768, desktop: 1280 };

export default defineConfig({
  testDir: "./e2e",
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL,
    // Production settings redirect to HTTPS unless a proxy reports the original scheme.
    extraHTTPHeaders: baseURL.startsWith("http://") ? { "X-Forwarded-Proto": "https" } : {},
    trace: "retain-on-failure",
  },
  projects: Object.entries(viewportWidths).map(([name, width]) => ({
    name,
    use: { ...devices["Desktop Chrome"], viewport: { width, height: 800 } },
  })),
});
