import { expect, Page } from "@playwright/test"

import { test } from "~~/test/playwright/utils/test-fixture"

const goToCustomAudioPage = async (page: Page) => {
  // Test in a custom audio detail page, it should apply the same for any audio.
  await page.goto("audio/7e063ee6-343f-48e4-a4a5-f436393730f6")
}

const showsErrorPage = async (page: Page) => {
  await expect(page.locator("h1")).toHaveText(
    /The content you’re looking for seems to have disappeared/
  )
}

test.describe.configure({ mode: "parallel" })

test("shows the data that is only available in single result, not search response", async ({
  page,
}) => {
  await goToCustomAudioPage(page)
  await expect(
    page.locator('dd:has-text("I Love My Dog You Love Your Cat")')
  ).toBeVisible()
})

test("shows the 404 error page when no valid id", async ({ page }) => {
  await page.goto("audio/foo")
  await showsErrorPage(page)
})

test("shows the 404 error page when no id", async ({ page }) => {
  await page.goto("audio/")
  await showsErrorPage(page)
})
