import { expect, Page } from "@playwright/test";

export async function runSearch(page: Page, query: string, filterText: string) {
  await page.goto("/");
  await page.getByTestId("search-query-input").fill(query);
  await page.getByTestId("search-filter-input").fill(filterText);
  await page.getByTestId("search-submit-button").click();
  await expect(page.getByTestId("video-list")).toBeVisible();
  await expect(page.getByTestId("video-card").first()).toBeVisible();
}

export async function syncFromExplore(page: Page, query: string, filterText: string) {
  await runSearch(page, query, filterText);
  await page.getByTestId("search-sync-button").click();
  await expect(page.getByTestId("explore-success-banner")).toContainText("同步完成");
}
