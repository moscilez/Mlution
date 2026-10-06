import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("mlution.locale", "en"));
});

test("registration, empty dashboard, session restore and logout", async ({
  page,
}) => {
  await page.goto("/register");
  await page
    .getByLabel("Email", { exact: true })
    .fill(`browser-${Date.now()}@example.com`);
  await page
    .getByLabel("Password", { exact: true })
    .fill("browser-safe-password-123");
  await page
    .getByRole("button", { name: "Create account", exact: true })
    .click();
  await expect(page).toHaveURL(/dashboard/);
  await expect(page.getByText("No projects yet")).toBeVisible();
  await page.keyboard.press("Control+k");
  await expect(
    page.getByRole("dialog", { name: "Command palette" }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await page.reload();
  await expect(
    page.getByRole("heading", { name: "Your ML workspace" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(page).toHaveURL(/login/);
  await page.goto("/dashboard");
  await expect(page).toHaveURL(/login/);
});

test("demo project, real training, results and playground", async ({
  page,
}) => {
  await page.goto("/");
  await page.getByRole("button", { name: "Try demo", exact: true }).click();
  await expect(page).toHaveURL(/projects\/[^/]+$/);
  await expect(
    page.getByRole("heading", { name: "Telco Churn Demo" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Run pipeline", exact: true }).click();
  await expect(
    page.getByText("Completed", { exact: true }).first(),
  ).toBeVisible({ timeout: 90_000 });
  await expect(page.getByRole("progressbar")).toHaveAttribute(
    "aria-valuenow",
    "100",
  );
  await page.getByRole("button", { name: "Playground", exact: true }).click();
  await expect(page).toHaveURL(/predict/);
  await expect(page.getByRole("heading").first()).toBeVisible();
  await page.getByRole("button", { name: /predict/i }).click();
  await expect(
    page.getByText("Predicted class", { exact: true }),
  ).toBeVisible();
});

test("dashboard displays a recoverable API error", async ({ page }) => {
  await page.goto("/login");
  await page
    .getByRole("button", { name: "Continue with demo account" })
    .click();
  await expect(page).toHaveURL(/projects\/[^/]+$/);
  await page.route("**/api/projects", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "Service temporarily unavailable" }),
    }),
  );
  await page.goto("/dashboard");
  await expect(page.getByText("Could not load projects")).toBeVisible();
});

test("mobile landing and authentication have no horizontal overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of ["/", "/login", "/register"]) {
    await page.goto(path);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
});
