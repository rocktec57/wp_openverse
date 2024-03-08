import { expect, test } from "@playwright/test"

import { getH1 } from "~~/test/playwright/utils/components"
import { preparePageForTests } from "~~/test/playwright/utils/navigation"

test.describe.configure({ mode: "parallel" })

test("sources table has links to source pages", async ({ page }) => {
  await preparePageForTests(page, "xl", {
    features: { additional_search_views: "on" },
  })
  await page.goto("/sources")
  await page
    .getByRole("cell", { name: "Flickr", exact: true })
    .getByRole("link")
    .click()
  await page.waitForURL("/image/collection?source=flickr")

  await expect(getH1(page, "Flickr")).toBeVisible()
})
