import { test } from "@playwright/test"

import breakpoints from "~~/test/playwright/utils/breakpoints"
import {
  goToSearchTerm,
  languageDirections,
  openFirstResult,
  pathWithDir,
  preparePageForTests,
} from "~~/test/playwright/utils/navigation"

import { supportedMediaTypes } from "~/constants/media"

test.describe.configure({ mode: "parallel" })

for (const mediaType of supportedMediaTypes) {
  for (const dir of languageDirections) {
    breakpoints.describeEvery(({ breakpoint, expectSnapshot }) => {
      test(`${mediaType} ${dir} single-result page snapshots from search results`, async ({
        page,
      }) => {
        await preparePageForTests(page, breakpoint)

        await goToSearchTerm(page, "birds", { dir })
        // This will include the "Back to results" link.
        await openFirstResult(page, mediaType)

        await expectSnapshot(
          `${mediaType}-${dir}-from-search-results`,
          page,
          { fullPage: true },
          { maxDiffPixelRatio: 0.02 }
        )
      })
    })
  }
}

for (const dir of languageDirections) {
  breakpoints.describeMobileAndDesktop(({ breakpoint, expectSnapshot }) => {
    test(`${dir} full-page report snapshots`, async ({ page }) => {
      await preparePageForTests(page, breakpoint)

      const IMAGE_ID = "da5cb478-c093-4d62-b721-cda18797e3fb"
      const path = pathWithDir(`/image/${IMAGE_ID}/report`, dir)

      await page.goto(path)
      await expectSnapshot(`${dir}-full-page-report`, page, { fullPage: true })
    })
  })
}
