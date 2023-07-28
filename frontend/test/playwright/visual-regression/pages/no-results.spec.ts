import { test } from "@playwright/test"

import {
  goToSearchTerm,
  languageDirections,
  preparePageForTests,
} from "~~/test/playwright/utils/navigation"
import breakpoints from "~~/test/playwright/utils/breakpoints"
import { setViewportToFullHeight } from "~~/test/playwright/utils/viewport"

import { supportedSearchTypes } from "~/constants/media"

test.describe.configure({ mode: "parallel" })
test.describe.configure({ retries: 2 })

for (const searchType of supportedSearchTypes) {
  for (const dir of languageDirections) {
    breakpoints.describeEvery(({ breakpoint, expectSnapshot }) => {
      test(`No results ${searchType} ${dir} page snapshots`, async ({
        page,
      }) => {
        await preparePageForTests(page, breakpoint)

        await goToSearchTerm(page, "querywithnoresults", { dir, searchType })

        await setViewportToFullHeight(page)

        await page.mouse.move(0, 82)

        await expectSnapshot(`no-results-${searchType}-${dir}`, page)
      })
    })
  }
}
