import { test, expect } from "@playwright/test";

// These tests require an explicitly isolated local preview server.
// Do not point MARKETPULSE_BASE_URL at a production site or original DB.
test("anonymous user is redirected from dashboard to sign-in", async ({ page }) => {
  await page.goto("/");
  await expect(page).toHaveURL(/\/login\/?$/);
  await expect(page.getByRole("heading", { name: "Welcome back" })).toBeVisible();
});

test("registration and password-reset links are reachable", async ({ page }) => {
  await page.goto("/login");
  await expect(page.getByRole("link", { name: "Create an account" })).toHaveAttribute("href", "/register");
  await page.getByRole("link", { name: "Forgot password?" }).click();
  await expect(page).toHaveURL(/\/forgot-password/);
});

test("authenticated navigation and offline research health", async ({ page }) => {
  test.skip(
    !process.env.MARKETPULSE_E2E_EMAIL || !process.env.MARKETPULSE_E2E_PASSWORD,
    "Create a dedicated account in the isolated preview DB and set credentials",
  );
  await page.goto("/login");
  await page.getByLabel("Email address").fill(process.env.MARKETPULSE_E2E_EMAIL);
  await page.getByLabel("Password", { exact: true }).fill(process.env.MARKETPULSE_E2E_PASSWORD);
  await page.getByRole("button", { name: "Sign in securely" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.getByRole("link", { name: "Research Health" }).click();
  await expect(page.getByRole("heading", { name: "Research health" })).toBeVisible();
  await page.getByRole("link", { name: "Forecast Performance" }).click();
  await expect(page.getByRole("heading", { name: "Prospective forecast performance" })).toBeVisible();
  await page.getByRole("link", { name: "Portfolio" }).click();
  await expect(page.getByRole("heading", { name: "Portfolio overview" })).toBeVisible();
});

test("authenticated forecast scorecard shows no fabricated performance", async ({ page }) => {
  test.skip(
    !process.env.MARKETPULSE_E2E_EMAIL || !process.env.MARKETPULSE_E2E_PASSWORD,
    "Requires isolated preview account",
  );
  await page.goto("/login");
  await page.getByLabel("Email address").fill(process.env.MARKETPULSE_E2E_EMAIL);
  await page.getByLabel("Password", { exact: true }).fill(process.env.MARKETPULSE_E2E_PASSWORD);
  await page.getByRole("button", { name: "Sign in securely" }).click();
  // Wait for the authenticated router transition before performing a
  // full-page navigation, otherwise the test races session establishment.
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Market Intelligence" })).toBeVisible();
  await page.goto("/forecast-performance");
  await expect(page.getByRole("heading", { name: "Prospective forecast performance" })).toBeVisible();
  await expect(page.getByText("Zero-return baseline MAE", { exact: true })).toBeVisible();
});


async function signInWithDisposableAccount(page) {
  await page.goto("/login");
  await page.getByLabel("Email address").fill(process.env.MARKETPULSE_E2E_EMAIL);
  await page.getByLabel("Password", { exact: true }).fill(process.env.MARKETPULSE_E2E_PASSWORD);
  await page.getByRole("button", { name: "Sign in securely" }).click();
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByRole("heading", { name: "Market Intelligence" })).toBeVisible();
}

test("server-verified sign-out stays signed out after reload", async ({ page }) => {
  test.skip(
    !process.env.MARKETPULSE_E2E_EMAIL || !process.env.MARKETPULSE_E2E_PASSWORD,
    "Requires the isolated preview account",
  );
  await signInWithDisposableAccount(page);
  await page.getByRole("button", { name: "Log out", exact: true }).click();
  await expect(page).toHaveURL(/\/login\/?$/);
  await page.reload();
  await expect(page).toHaveURL(/\/login\/?$/);
  const current = await page.request.get("/api/auth/me/");
  expect([401, 403]).toContain(current.status());
  await page.goto("/portfolio");
  await expect(page).toHaveURL(/\/login\/?$/);
});

test("sign-out in one tab cannot restore another tab on refresh", async ({ page, context }) => {
  test.skip(
    !process.env.MARKETPULSE_E2E_EMAIL || !process.env.MARKETPULSE_E2E_PASSWORD,
    "Requires the isolated preview account",
  );
  await signInWithDisposableAccount(page);
  const other = await context.newPage();
  await other.goto("/portfolio");
  await expect(other.getByRole("heading", { name: "Portfolio overview" })).toBeVisible();
  await page.getByRole("button", { name: "Log out", exact: true }).click();
  await expect(page).toHaveURL(/\/login\/?$/);
  await other.reload();
  await expect(other).toHaveURL(/\/login\/?$/);
});

test("authenticated historical scorecard labels uncertainty and baseline performance", async ({ page }) => {
  test.skip(!process.env.MARKETPULSE_E2E_EMAIL || !process.env.MARKETPULSE_E2E_PASSWORD,
    "Requires isolated disposable login account");
  await signInWithDisposableAccount(page);
  await page.getByRole("link", { name: "Model Reliability" }).click();
  await expect(page.getByRole("heading", { name: "Model reliability scorecard" })).toBeVisible();
  await expect(page.getByText("Not measured").first()).toBeVisible();
  await expect(page.getByText("Strongest simple baseline MAE")).toBeVisible();
  await page.getByLabel("Stock to inspect").selectOption("NVDA");
  await expect(page.getByRole("heading", { name: "NVDA · historical model comparison" })).toBeVisible();
});
