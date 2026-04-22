import { expect, test } from "@playwright/test";

import { syncFromExplore } from "./helpers";

test("sync creates local library items and detail page remains reachable", async ({ page }) => {
  await syncFromExplore(page, "fastapi", "只看教程，排除直播切片");

  await page.goto("/library");
  await expect(page.getByTestId("video-list")).toBeVisible();
  await page.getByTestId("library-sort-select").selectOption("published_at");
  await page.getByTestId("library-apply-button").click();
  await expect(page.getByTestId("video-card").first()).toBeVisible();

  await page.getByTestId("video-detail-link").first().click();
  await expect(page.getByTestId("video-detail-page")).toBeVisible();
  await expect(page.getByTestId("video-detail-title")).toBeVisible();
  await expect(page.getByTestId("video-detail-source")).toBeVisible();
});
