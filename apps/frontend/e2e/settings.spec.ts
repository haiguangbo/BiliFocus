import { expect, test } from "@playwright/test";

test("settings persists source strategy and default filter", async ({ page }) => {
  await page.goto("/settings");
  await page.getByTestId("preferences-source-select").selectOption("mock");
  await page.getByTestId("preferences-limit-input").fill("9");
  await page.getByTestId("preferences-filter-input").fill("排除直播切片");
  await page.getByTestId("preferences-library-sort-select").selectOption("views");
  await page.getByTestId("preferences-save-button").click();
  await expect(page.getByTestId("preferences-message")).toContainText("设置已保存");
});
