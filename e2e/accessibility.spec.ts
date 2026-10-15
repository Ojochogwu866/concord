import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

const WCAG_22_AA_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];

const skipLinkNames = { en: "Skip to main content", fr: "Aller au contenu principal" };

const publicPages = [
  { name: "home page", path: "/en/", language: "en" },
  { name: "briefs index", path: "/en/briefs/", language: "en" },
  { name: "not found page", path: "/en/this-page-does-not-exist/", language: "en" },
  { name: "French home page", path: "/fr/", language: "fr" },
  { name: "French briefs index", path: "/fr/notes/", language: "fr" },
  { name: "French not found page", path: "/fr/page-introuvable/", language: "fr" },
] as const;

for (const { name, path, language } of publicPages) {
  test.describe(name, () => {
    // Axe measures colours as rendered, so entrance animations must be settled first.
    test.use({ contextOptions: { reducedMotion: "reduce" } });

    test.beforeEach(async ({ page }) => {
      await page.goto(path);
    });

    test("has no WCAG 2.2 AA violations", async ({ page }) => {
      const results = await new AxeBuilder({ page }).withTags(WCAG_22_AA_TAGS).analyze();

      expect(results.violations).toEqual([]);
    });

    test("skip link is the first tab stop and moves focus to main", async ({ page }) => {
      const skipLink = page.getByRole("link", { name: skipLinkNames[language] });

      await page.keyboard.press("Tab");
      await expect(skipLink).toBeFocused();
      await expect(skipLink).toBeInViewport();

      await page.keyboard.press("Enter");
      await expect(page.locator("main")).toBeFocused();
    });
  });
}

test.describe("entrance animations", () => {
  test.use({ contextOptions: { reducedMotion: "no-preference" } });

  test("every section is revealed once scrolled into view", async ({ page }) => {
    await page.goto("/en/");
    const sections = page.locator("[data-reveal]");

    for (const section of await sections.all()) {
      await section.scrollIntoViewIfNeeded();
      await expect(section).toHaveClass(/is-revealed/);
    }
  });
});
