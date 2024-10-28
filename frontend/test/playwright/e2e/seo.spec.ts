import { expect } from "@playwright/test"

import { test } from "~~/test/playwright/utils/test"

import { preparePageForTests } from "~~/test/playwright/utils/navigation"

test.describe.configure({ mode: "parallel" })
const DESCRIPTION =
  "Search over 800 million free and openly licensed images, photos, audio, and other media types for reuse and remixing."
const NO_INDEX = "noindex, nofollow"
const INDEX =
  "index, follow, max-image-preview:large, max-snippet:-1, max-video-preview:-1"
const INDEX_NO_FOLLOW = "index, nofollow"
const DEFAULT_IMAGE = "/openverse-default.jpg"

const pages = {
  home: {
    url: "/",
    title: "Openly Licensed Images, Audio and More | Openverse",
    ogImage: DEFAULT_IMAGE,
    ogTitle: "Openverse",
    robots: INDEX,
  },
  allSearch: {
    url: "/search/?q=birds",
    title: "birds | Openverse",
    ogImage: DEFAULT_IMAGE,
    ogTitle: "Openverse",
    robots: NO_INDEX,
  },
  imageSearch: {
    url: "/search/image?q=birds",
    title: "birds | Openverse",
    ogImage: DEFAULT_IMAGE,
    ogTitle: "Openverse",
    robots: NO_INDEX,
  },
  audioSearch: {
    url: "/search/audio?q=birds",
    title: "birds | Openverse",
    ogImage: DEFAULT_IMAGE,
    ogTitle: "Openverse",
    robots: NO_INDEX,
  },
  imageDetail: {
    url: "/image/da5cb478-c093-4d62-b721-cda18797e3fb",
    title: "bird | Openverse",
    ogImage: new RegExp(
      "/v1/images/da5cb478-c093-4d62-b721-cda18797e3fb/thumb/"
    ),
    ogTitle: "bird",
    robots: NO_INDEX,
  },
  audioDetail: {
    url: "/audio/7e063ee6-343f-48e4-a4a5-f436393730f6",
    title: "I Love My Dog You Love your Cat | Openverse",
    ogImage: new RegExp(
      "/v1/audio/7e063ee6-343f-48e4-a4a5-f436393730f6/thumb/"
    ),
    ogTitle: "I Love My Dog You Love your Cat",
    robots: NO_INDEX,
  },
  about: {
    url: "/about",
    title: "About Openverse | Openverse",
    ogImage: DEFAULT_IMAGE,
    ogTitle: "Openverse",
    robots: INDEX,
  },
  tag: {
    url: "/image/collection?tag=cat",
    title: "cat images | Openverse",
    ogImage: DEFAULT_IMAGE,
    ogTitle: "cat images | Openverse",
    robots: NO_INDEX,
  },
  source: {
    url: "/image/collection?source=flickr",
    title: "Flickr images | Openverse",
    ogImage: DEFAULT_IMAGE,
    ogTitle: "Flickr images | Openverse",
    robots: INDEX_NO_FOLLOW,
  },
  creator: {
    url: "/image/collection?source=flickr&creator=strogoscope",
    title: "strogoscope | Openverse",
    ogImage: DEFAULT_IMAGE,
    ogTitle: "strogoscope | Openverse",
    robots: NO_INDEX,
  },
}
test.describe("page metadata", () => {
  for (const openversePage of Object.values(pages)) {
    test(`${openversePage.url}`, async ({ page }) => {
      await preparePageForTests(page, "xl")
      await page.goto(openversePage.url)
      await expect(page).toHaveTitle(openversePage.title)
      const metaDescription = page.locator('meta[name="description"]')
      await expect(metaDescription).toHaveAttribute("content", DESCRIPTION)

      const metaRobots = page.locator('meta[name="robots"]')
      await expect(metaRobots).toHaveAttribute("content", openversePage.robots)

      const metaOgImage = page.locator('meta[property="og:image"]')
      await expect(metaOgImage).toHaveAttribute(
        "content",
        openversePage.ogImage
      )

      const metaOgTitle = page.locator('meta[property="og:title"]')
      await expect(metaOgTitle).toHaveAttribute(
        "content",
        openversePage.ogTitle
      )
    })
  }
})

test.describe("robots.txt", () => {
  test("snapshot", async ({ page }) => {
    await page.goto("/robots.txt")
    const robotsText = await page.innerText("body")

    expect(robotsText).toMatchSnapshot({ name: "robots.txt" })
  })
})
