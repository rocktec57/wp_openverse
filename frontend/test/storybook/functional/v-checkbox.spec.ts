import { expect } from "@playwright/test"
import { test } from "~~/test/playwright/utils/test"
import { makeGotoWithArgs } from "~~/test/storybook/utils/args"

test.describe.configure({ mode: "parallel" })
;["default", "switch"].forEach((type) => {
  const goToStory = makeGotoWithArgs(`components-vcheckbox--${type}`)
  const goToAndWait = async (
    ...[page, ...args]: Parameters<typeof goToStory>
  ) => {
    await goToStory(page, ...args)
    await page.getByRole("checkbox").waitFor()
  }

  test.describe(`VCheckbox-${type}`, () => {
    test("should load with checked state", async ({ page }) => {
      const name = "loaded with checked state"
      await goToAndWait(page, { checked: true, name })
      const checkboxes = page.getByLabel(name)
      expect(await checkboxes.all()).toHaveLength(1)
      await expect(checkboxes).toBeChecked()
    })

    test("should load with unchecked state", async ({ page }) => {
      const name = "loaded with unchecked state"
      await goToAndWait(page, { checked: false, name })
      const checkboxes = page.getByLabel(name)
      expect(await checkboxes.all()).toHaveLength(1)
      await expect(checkboxes).not.toBeChecked()
    })

    test("should toggle to unchecked when loaded as checked", async ({
      page,
    }) => {
      const name = "loaded with checked state"
      await goToAndWait(page, { checked: true, name })
      const checkboxes = page.getByLabel(name)
      expect(await checkboxes.all()).toHaveLength(1)
      await expect(checkboxes).toBeChecked()
      await checkboxes.click()
      await expect(checkboxes).not.toBeChecked()
    })

    test("should toggle to checked when loaded as unchecked", async ({
      page,
    }) => {
      const name = "loaded with unchecked state"
      await goToAndWait(page, { checked: false, name })
      const checkboxes = page.getByLabel(name)
      expect(await checkboxes.all()).toHaveLength(1)
      await expect(checkboxes).not.toBeChecked()
      await checkboxes.click()
      await expect(checkboxes).toBeChecked()
    })
  })
})
