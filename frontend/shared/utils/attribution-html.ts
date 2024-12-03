/*
 * This module highly mirrors the Python code present in the backend repository.
 * For any changes made here, please make the corresponding changes in the
 * backend, or open an issue to track it.
 */
import enJson from "~~/i18n/locales/en.json"

import type { LicenseElement } from "#shared/constants/license"
import {
  getElements,
  getFullLicenseName,
  isPublicDomain,
} from "#shared/utils/license"
import type { Media } from "#shared/types/media"

import type { Composer } from "vue-i18n"

/* Helper functions */

/**
 * Escape characters that have special meaning in HTML to break script injection
 * attacks.
 *
 * @param unsafe - the unsafe text to sanitise
 * @returns the sanitised text content
 */
const escapeHtml = (unsafe: string) =>
  unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;")

/**
 * Create an HTML tag with the given name, attributes and children.
 *
 * @param name - the tag name
 * @param attrs - the attributes associated with the tag
 * @param children - the tags children
 * @returns the HTML markup of the tag
 */
const h = (
  name: string,
  attrs: Record<string, string>,
  children: string[] | null = null
): string => {
  const selfClosingTags = [
    "area",
    "base",
    "br",
    "col",
    "embed",
    "hr",
    "img",
    "input",
    "link",
    "meta",
    "param",
    "source",
    "track",
    "wbr",
  ]

  const map = Object.entries(attrs)
    .map(([key, value]) => `${key}="${value}"`)
    .join(" ")

  if (selfClosingTags.includes(name)) {
    return map ? `<${name} ${map} />` : `<${name} />`
  }

  const opening = map ? `<${name} ${map}>` : `<${name}>`
  const closing = `</${name}>`
  return `${opening}${(children ?? []).join("\n")}${closing}`
}

/**
 * Format the given string by replacing all placeholder keys with their values.
 * The pairs of placeholders and values are passed as a dictionary.
 *
 * @param text - the string in which to perform the formatting
 * @param replacements - the mapping of placeholders to values
 * @returns the formatted string
 */
const fmt = (text: string, replacements: Record<string, string>): string => {
  Object.entries(replacements).forEach(([key, value]) => {
    text = text.replace(`{${key}}`, value)
  })
  return text
}

/**
 * Perform the same role as `i18n.t` except that it's restricted to reading
 * English from `en.json`.
 *
 * @param path - the key to the JSON value to read
 * @param replacements - the pair of placeholders and their replacement strings
 * @returns the English string with placeholders substituted
 */
const fakeT = (
  path: string,
  replacements: Record<string, string> = {}
): string => {
  interface NestedRecord {
    [key: string]: string | NestedRecord
  }

  const segments = path.split(".")
  let fraction: NestedRecord = enJson["mediaDetails"].reuse.credit
  let text: string | undefined = undefined
  segments.forEach((segment) => {
    const piece = fraction[segment]
    if (typeof piece === "string") {
      text = piece
    } else {
      fraction = piece
    }
  })
  return text ? fmt(text, replacements) : ""
}

/**
 * Get an `<img>` tag corresponding to a license element.
 *
 * @param licenseElement - the license element for which to get the `<img>` tag
 * @returns the HTML markup of the `<img>` tag
 */
const licenseElementImg = (licenseElement: LicenseElement): string => {
  const filename = licenseElement.replace("-", ".")
  const src = `https://mirrors.creativecommons.org/presskit/icons/${filename}.svg`
  return h("img", {
    src,
    style: "height: 1em; margin-right: 0.125em; display: inline;",
  })
}

/**
 * Get an HTML `<a>` tag set up with the `target` and `rel` attributes.
 *
 * @param href - the link that the anchor tag should point to
 * @param text - the textual content of the anchor tag
 * @returns the HTML markup of the `<a>` tag
 */
const extLink = (href: string, text: string) =>
  h("a", { rel: "noopener noreferrer", href }, [text])

/**
 * Generate a Dublin Core conforming XML attribution snippet.
 *
 * @param mediaItem - the media item being attributed
 * @returns the XML markup of the attribution
 */
const xmlAttribution = (mediaItem: Record<string, string>) =>
  `<attribution xmlns:dc="http://purl.org/dc/elements/1.1/">
	<dc:creator>${mediaItem.creator}</dc:creator>
	<dc:title>${mediaItem.title}</dc:title>
	<dc:rights>${mediaItem.license_url}</dc:rights>
	<dc:identifier>${mediaItem.foreign_landing_url}</dc:identifier>
	<dc:type>${mediaItem.type}</dc:type>
</attribution>`

/* Interfaces */

/**
 * This interface describes a subset of media that contains fields necessary
 * for generating a proper attribution.
 */
export type AttributableMedia = Pick<
  Media,
  | "originalTitle"
  | "foreign_landing_url"
  | "creator"
  | "creator_url"
  | "license"
  | "license_version"
  | "license_url"
  | "frontendMediaType"
  | "attribution"
>

/**
 * This interface describes the options that the `getAttribution` function can
 * take to customise its output.
 */
export interface AttributionOptions {
  includeIcons?: boolean
  isPlaintext?: boolean
  isXml?: boolean
}

/* Actual util */

/**
 * Get the HTML markup for properly attributing the given media item.
 *
 * @param mediaItem - the media item being attributed
 * @param t - the i18n `t` function to access translations
 * @param includePreview - whether to include the preview markup in the HTML
 * @returns the HTML markup of the attribution
 */
export const getAttribution = (
  mediaItem: AttributableMedia,
  t: Composer["t"] | null = null,
  { includeIcons, isPlaintext, isXml }: AttributionOptions = {
    isPlaintext: false,
    includeIcons: true,
    isXml: false,
  }
): string => {
  if (!mediaItem) {
    return ""
  }

  const isPd = isPublicDomain(mediaItem.license)

  const i18nBase = "mediaDetails.reuse.credit"

  const tFn = t
    ? (key: string, values?: Record<string, unknown>) =>
        values
          ? t(`${i18nBase}.${key}`, values as Record<string, unknown>)
          : t(`${i18nBase}.${key}`)
    : fakeT

  /* Title */

  let title = mediaItem.originalTitle || tFn("genericTitle")
  if (!isPlaintext) {
    title = escapeHtml(title)
  }
  if (!isPlaintext && mediaItem.foreign_landing_url) {
    title = extLink(mediaItem.foreign_landing_url, title)
  }
  if (mediaItem.originalTitle) {
    title = tFn("actualTitle", { title })
  }

  /* License */

  const fullLicenseName = getFullLicenseName(
    mediaItem.license,
    mediaItem.license_version,
    t
  )
  let licenseIcons = ""
  if (includeIcons && mediaItem.license) {
    const elements = getElements(mediaItem.license)
    const icons = elements.map((element) => licenseElementImg(element))
    // Icons are only rendered if present for every element
    if (!icons.includes("")) {
      licenseIcons = icons.join("")
    }
  }
  let license = `${fullLicenseName} ${licenseIcons}`.trim()
  if (!isPlaintext && mediaItem.license_url) {
    license = extLink(`${mediaItem.license_url}?ref=openverse`, license)
  }

  /* Attribution */

  const attributionParts: Record<string, string> = {
    title,
    markedLicensed: tFn(isPd ? "marked" : "licensed"),
    license: license,
    viewLegal: "",
    creator: "",
  }

  if (isPlaintext && mediaItem.license_url) {
    attributionParts["viewLegal"] = tFn("viewLegalText", {
      termsCopy: tFn(isPd ? "termsText" : "copyText"),
      url: `${mediaItem.license_url}?ref=openverse`,
    })
  }

  if (mediaItem.creator) {
    let creator = mediaItem.creator
    if (!isPlaintext) {
      creator = escapeHtml(creator)
    }
    if (!isPlaintext && mediaItem.creator_url) {
      creator = extLink(mediaItem.creator_url, creator)
    }
    attributionParts.creator = tFn("creatorText", {
      creatorName: creator,
    })
  }

  const attribution = tFn("text", attributionParts)
    .replace(/\s{2}/g, " ")
    .trim()

  if (isXml) {
    const { frontendMediaType, ...restMediaItem } = mediaItem

    const xmlAttributionParts = {
      ...restMediaItem,
      type: frontendMediaType === "audio" ? "Sound" : "StillImage",
    }

    return xmlAttribution(xmlAttributionParts)
  } else if (isPlaintext) {
    return attribution
  } else {
    return h("p", { class: "attribution" }, [attribution])
  }
}
