import { expect, test } from "@playwright/test";

const RUN = ".query-input button.btn-gold";
const APPROVE = ".hitl-actions button.btn-gold";

async function runToHitl(page: import("@playwright/test").Page) {
  await page.goto("/");
  await page.locator(RUN).click();
  // Injection defense runs during the research phase and is logged durably
  // (the transient badge may clear; the SECURITY log entry persists).
  await expect(page.locator(".log-item.security").first()).toBeAttached({ timeout: 20_000 });
  // The run pauses at the human checkpoint.
  await expect(page.locator(APPROVE)).toBeVisible({ timeout: 20_000 });
}

async function expectVerifiedBrief(page: import("@playwright/test").Page) {
  const stamp = page.locator(".verified-stamp");
  await expect(stamp).toBeVisible({ timeout: 30_000 });
  await expect(stamp).toContainText("3 of 3");
  await expect(page.locator(".brief h3.bt")).toContainText("Market Brief");
  await expect(page.locator(".perma code")).toContainText("agents.devs-core.com/run/");
}

const dataLayerEvents = (page: import("@playwright/test").Page) =>
  page.evaluate(() =>
    ((window as unknown as { dataLayer?: { event?: string }[] }).dataLayer ?? [])
      .map((d) => d.event)
      .filter(Boolean),
  );

test("runs the full mocked workflow to a verified, cited brief", async ({ page }) => {
  await runToHitl(page);
  await page.locator(APPROVE).click();
  await expectVerifiedBrief(page);

  // Lead-gen funnel events fire through the run (§11).
  const fired = await dataLayerEvents(page);
  expect(fired).toContain("demo_run_started");
  expect(fired).toContain("demo_hitl_approved");
  expect(fired).toContain("demo_run_completed");

  // The conversion CTA fires book_call.
  await page.locator(".output-zone .convert a").click();
  expect(await dataLayerEvents(page)).toContain("book_call");
});

test("approve works by tap on a touch device", async ({ page, hasTouch }) => {
  test.skip(!hasTouch, "touch-only assertion");
  await runToHitl(page);
  await page.locator(APPROVE).tap();
  await expectVerifiedBrief(page);
});

test("has no horizontal overflow at the current viewport", async ({ page }) => {
  await page.goto("/");
  const overflows = await page.evaluate(
    () => document.documentElement.scrollWidth > document.documentElement.clientWidth + 1,
  );
  expect(overflows).toBe(false);
});
