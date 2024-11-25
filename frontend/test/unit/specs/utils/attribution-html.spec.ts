import { describe, expect, it } from "vitest"

import { i18n } from "~~/test/unit/test-utils/i18n"

import type { AttributableMedia } from "~/utils/attribution-html"
import { getAttribution } from "~/utils/attribution-html"

const t = i18n.t

const mediaItem: AttributableMedia = {
  originalTitle: "Title",
  foreign_landing_url: "https://foreign.landing/url",
  creator: "Creator",
  creator_url: "https://creator/url",
  license: "pdm",
  license_version: "1.0",
  license_url: "https://license/url",
  frontendMediaType: "image",
  attribution:
    '"Title" by Creator is marked with Public Domain Mark 1.0 . To view a copy of this license, visit https://creativecommons.org/publicdomain/zero/1.0/?ref=openverse.',
}

describe("getAttribution", () => {
  it("returns attribution for media with i18n", async () => {
    const attributionText =
      '"Title" by Creator is marked with Public Domain Mark 1.0 .'
    document.body.innerHTML = getAttribution(mediaItem, t)
    const attributionP = document.getElementsByClassName("attribution")[0]
    expect(attributionP.textContent?.trim()).toEqual(attributionText)
  })

  // TODO: fix fakeT function
  it("returns attribution for media without i18n", async () => {
    // const attributionText = '"Title" by Creator is marked with PDM 1.0 .'
    console.log(getAttribution(mediaItem, null))
    document.body.innerHTML = getAttribution(mediaItem, null)
    const attributionP = document.getElementsByClassName("attribution")[0]
    expect(attributionP.textContent?.trim()).toBe("")
  })

  it("uses generic title if not known", async () => {
    const mediaItemNoTitle = { ...mediaItem, originalTitle: "" }
    const attrText = getAttribution(mediaItemNoTitle, t, {
      isPlaintext: true,
    })
    const expectation =
      "This work by Creator is marked with Public Domain Mark 1.0"
    expect(attrText).toContain(expectation)
  })

  it("omits creator if not known", async () => {
    const mediaItemNoCreator = { ...mediaItem, creator: undefined }
    const attrText = getAttribution(mediaItemNoCreator, t, {
      isPlaintext: true,
    })
    const expectation = '"Title" is marked with Public Domain Mark 1.0'
    expect(attrText).toContain(expectation)
  })

  it("escapes embedded HTML", async () => {
    const mediaItemWithHtml = {
      ...mediaItem,
      originalTitle: '<script>console.log("HELLO");</script>',
    }
    const attrText = getAttribution(mediaItemWithHtml, t)
    const expectation =
      "&lt;script&gt;console.log(&quot;HELLO&quot;);&lt;/script&gt;"
    expect(attrText).toContain(expectation)
    expect(attrText).not.toContain(mediaItemWithHtml.originalTitle)
  })

  it("does not use anchors in plain-text mode", async () => {
    document.body.innerHTML = getAttribution(mediaItem, t)
    expect(document.getElementsByTagName("a")).not.toHaveLength(0)
    document.body.innerHTML = getAttribution(mediaItem, t, {
      isPlaintext: true,
    })
    expect(document.getElementsByTagName("a")).toHaveLength(0)
  })

  it("renders the correct text in plain-text mode", async () => {
    const attrText = getAttribution(mediaItem, t, { isPlaintext: true })
    const expectation =
      '"Title" by Creator is marked with Public Domain Mark 1.0. To view the terms, visit https://license/url?ref=openverse.'
    expect(attrText).toEqual(expectation)
  })

  it("skips the link if URL is missing", async () => {
    const mediaItemNoLicenseUrl = { ...mediaItem, license_url: undefined }
    const attrText = getAttribution(mediaItemNoLicenseUrl, t, {
      isPlaintext: true,
    })
    const antiExpectation = "To view"
    expect(attrText).not.toContain(antiExpectation)
  })

  it("does not add license element icons in no-icons mode", () => {
    document.body.innerHTML = getAttribution(mediaItem, t)
    expect(document.getElementsByTagName("img")).not.toHaveLength(0)
    document.body.innerHTML = getAttribution(mediaItem, t, {
      includeIcons: false,
    })
    expect(document.getElementsByTagName("img")).toHaveLength(0)
  })
})
