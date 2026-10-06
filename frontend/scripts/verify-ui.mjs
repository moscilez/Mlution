import { chromium } from "@playwright/test";
import { mkdir } from "node:fs/promises";

await mkdir("test-results", { recursive: true });
const browser = await chromium.launch({ headless: true });
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
try {
  await page.goto("http://localhost:3000/");
  await page.screenshot({ path: "test-results/landing.png", fullPage: true });
  await page.getByRole("button", { name: "Try demo", exact: true }).click();
  await page.waitForURL(/projects\/[^/]+$/);
  await page.getByRole("button", { name: "Run pipeline", exact: true }).waitFor();
  await page.screenshot({ path: "test-results/workspace.png", fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of [null, "/dashboard", "/projects/new", "/settings"]) {
    if (path) await page.goto(`http://localhost:3000${path}`);
    await page.getByRole("button", { name: "Sign out", exact: true }).waitFor();
    const dimensions = await page.evaluate(() => ({ viewport: innerWidth, content: document.documentElement.scrollWidth }));
    console.log(`${path ?? "workspace"}: ${JSON.stringify(dimensions)}`);
    if (dimensions.content > dimensions.viewport) throw new Error(`Horizontal overflow on ${path ?? "workspace"}`);
    await page.screenshot({ path: `test-results/mobile-${path?.split("/").pop() ?? "workspace"}.png`, fullPage: true });
  }
} finally {
  await browser.close();
}
