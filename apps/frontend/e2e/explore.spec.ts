import { expect, test } from "@playwright/test";

import { runSearch } from "./helpers";

test("explore search renders provider-backed results", async ({ page }) => {
  await runSearch(page, "fastapi", "只看教程，排除直播切片");
  await expect(page.getByTestId("explore-query-context")).toContainText("候选总数");
  await expect(page.getByTestId("video-card").first()).toContainText(/Provider|Search Result|Local Cache/);
});
