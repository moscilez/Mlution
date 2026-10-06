import { test, expect } from "@playwright/test";

test("Russian default and persistent language across routes", async ({
  page,
}) => {
  await page.goto("/");
  await expect(page.locator("html")).toHaveAttribute("lang", "ru");
  await expect(
    page.getByRole("button", { name: "Попробовать демо", exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "English", exact: true })
    .first()
    .click();
  await expect(page.locator("html")).toHaveAttribute("lang", "en");
  await page.reload();
  await expect(
    page.getByRole("button", { name: "Try demo", exact: true }),
  ).toBeVisible();
  await page.goto("/login");
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Русский", exact: true }).click();
  await expect(page.getByLabel("Пароль", { exact: true })).toBeVisible();
});

test("process explorer supports keyboard and preserves its stage on language change", async ({
  page,
}) => {
  await page.goto("/");
  const tab = page.getByRole("tab", { name: "01 Анализ", exact: true });
  await tab.focus();
  await tab.press("End");
  await expect(
    page.getByRole("tab", { name: "07 Результат", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await expect(
    page.getByRole("tabpanel").getByText("model.joblib", { exact: true }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "English", exact: true })
    .first()
    .click();
  await expect(
    page.getByRole("tab", { name: "07 Finalize", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
});

test("language switch preserves form draft and mobile layout", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/login");
  await page
    .getByLabel("Электронная почта", { exact: true })
    .fill("draft@example.com");
  await page.getByRole("button", { name: "English", exact: true }).click();
  await expect(page.getByLabel("Email", { exact: true })).toHaveValue(
    "draft@example.com",
  );
  for (const path of ["/", "/login", "/register"]) {
    await page.goto(path);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth,
      ),
    ).toBeTruthy();
  }
});
