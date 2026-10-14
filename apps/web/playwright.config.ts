import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  timeout: 60_000,
  use: { baseURL: "http://127.0.0.1:3000", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { viewport: { width: 1440, height: 900 } } },
    {
      name: "mobile",
      use: {
        viewport: { width: 390, height: 844 },
        isMobile: true,
        hasTouch: true,
      },
    },
  ],
  webServer: [
    {
      command: "npm run start -- --hostname 127.0.0.1",
      url: "http://127.0.0.1:3000/login",
      reuseExistingServer: false,
      timeout: 120_000,
      env: { API_ORIGIN: "http://127.0.0.1:8000" },
    },
    {
      command:
        process.platform === "win32"
          ? "..\\..\\.venv\\Scripts\\python -m uvicorn scripts.http_e2e:create_test_app --factory --host 127.0.0.1 --port 8000 --app-dir ../.."
          : "python -m uvicorn scripts.http_e2e:create_test_app --factory --host 127.0.0.1 --port 8000 --app-dir ../..",
      url: "http://127.0.0.1:8000/health/ready",
      reuseExistingServer: false,
      timeout: 120_000,
    },
  ],
});
