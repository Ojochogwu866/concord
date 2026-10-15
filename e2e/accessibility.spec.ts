import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const WCAG_22_AA_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

const publicPages = [{ name: "not found page", path: "/this-page-does-not-exist/" }];

for (const { name, path } of publicPages) {
  test.describe(name, () => {
    test.beforeEach(async ({ page }) => {
      await page.goto(path);
    });

    test("has no WCAG 2.2 AA violations", async ({ page }) => {
      const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA_TAGS).analyze();

      expect(results.violations).toEqual([]);
    });

    test("skip link is the first tab stop and moves focus to main", async ({ page }) => {
      const skipLink = page.getByRole("link", { name: "Skip to main content" });

      await page.keyboard.press("Tab");
      await expect(skipLink).toBeFocused();
      await expect(skipLink).toBeInViewport();

      await page.keyboard.press("Enter");
      await expect(page.locator("main")).toBeFocused();
    });
  });
}
