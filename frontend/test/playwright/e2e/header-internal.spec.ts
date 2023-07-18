import { test, expect, Page } from "@playwright/test"

import {
  isDialogOpen,
  LanguageDirection,
  preparePageForTests,
  scrollToBottom,
  setBreakpointCookie,
  t,
} from "~~/test/playwright/utils/navigation"
import breakpoints from "~~/test/playwright/utils/breakpoints"

const currentPageLink = 'div[role="dialog"] >> [aria-current="page"]'
const currentPageLinkInPopover = '.popover-content >> [aria-current="page"]'

const getMenuButton = async (page: Page) => {
  return page.getByRole("button", { name: t("header.aria.menu") })
}

const clickMenuButton = async (page: Page) => {
  return (await getMenuButton(page)).click()
}

const closeMenu = async (page: Page, dir: LanguageDirection = "ltr") => {
  await page
    .getByRole("button", { name: t("modal.closePagesMenu", dir) })
    .click()
}

const isPagesPopoverOpen = async (page: Page) =>
  page.locator(".popover-content").isVisible({ timeout: 100 })

test.describe.configure({ mode: "parallel" })

test.describe("Header internal", () => {
  breakpoints.describeXs(() => {
    test.beforeEach(async ({ page }) => {
      await preparePageForTests(page, "xs")
    })

    test("can open and close the modal on xs breakpoint", async ({ page }) => {
      await page.goto("/about")
      await clickMenuButton(page)
      expect(await isDialogOpen(page)).toBe(true)
      await expect(page.locator(currentPageLink)).toBeVisible()
      await expect(page.locator(currentPageLink)).toHaveText("About")

      await closeMenu(page)
      expect(await isDialogOpen(page)).toBe(false)
      await expect(await getMenuButton(page)).toBeVisible()
    })

    test("the modal locks the scroll on xs breakpoint", async ({ page }) => {
      await page.goto("/about")
      await scrollToBottom(page)

      await clickMenuButton(page)
      await closeMenu(page)

      const scrollPosition = await page.evaluate(() => window.scrollY)
      expect(scrollPosition).toBeGreaterThan(100)
    })

    test("the modal opens an external link in a new window and it closes the modal", async ({
      page,
    }) => {
      await page.goto("/about")
      await scrollToBottom(page)
      await clickMenuButton(page)

      // Open the external link in a new tab, close the tab
      const [popup] = await Promise.all([
        page.waitForEvent("popup"),
        page.locator('div[role="dialog"] >> text=API').click(),
      ])
      await popup.close()
      // If we want the modal to stay open, we'll need to change this to `true`,
      // and implement the change
      expect(await isDialogOpen(page)).toBe(false)
    })

    test("content page opened from home should be scrollable", async ({
      page,
    }) => {
      await page.goto("/")
      await clickMenuButton(page)
      await page.getByRole("link", { name: t("navigation.about") }).click()
      await page.waitForURL("/about")
      await scrollToBottom(page)
      const scrollPosition = await page.evaluate(() => window.scrollY)
      expect(scrollPosition).toBeGreaterThan(100)
    })

    test("can open a content page from home and go back", async ({ page }) => {
      await page.goto("/")
      const homeUrl = page.url()
      await clickMenuButton(page)
      await page.getByRole("link", { name: t("navigation.about") }).click()
      // "Openverse Home" is hardcoded because our translation helper
      // doesn't support named interpolation.
      await page
        .getByRole("banner")
        .getByRole("link", { name: "Openverse Home" })
        .click()
      expect(page.url()).toBe(homeUrl)
    })
  })

  breakpoints.describeMd(() => {
    test("can open and close the popover on sm breakpoint", async ({
      page,
    }) => {
      await setBreakpointCookie(page, "sm")
      await page.goto("/about")
      await clickMenuButton(page)
      expect(await isPagesPopoverOpen(page)).toBe(true)
      await expect(page.locator(currentPageLinkInPopover)).toBeVisible()
      await expect(page.locator(currentPageLinkInPopover)).toHaveText("About")

      await clickMenuButton(page)
      expect(await isPagesPopoverOpen(page)).toBe(false)
      await expect(await getMenuButton(page)).toBeVisible()
    })
  })
})
