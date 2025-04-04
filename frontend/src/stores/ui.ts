import { useCookie } from "#imports"

import { LocaleObject } from "@nuxtjs/i18n"
import { defineStore } from "pinia"

import type { RealBreakpoint } from "#shared/constants/screens"
import { ALL_SCREEN_SIZES } from "#shared/constants/screens"
import { needsTranslationBanner } from "#shared/utils/translation-banner"
import type { BannerId } from "#shared/types/banners"
import {
  defaultPersistientCookieState,
  type OpenverseCookieState,
  persistentCookieOptions,
} from "#shared/types/cookies"

const desktopBreakpoints: RealBreakpoint[] = ["2xl", "xl", "lg"]

export type SnackbarState = "not_shown" | "visible" | "dismissed"
export type ColorMode = "dark" | "light" | "system"

export function isColorMode(value: undefined | string): value is ColorMode {
  return (
    typeof value === "string" && ["light", "dark", "system"].includes(value)
  )
}

export interface UiState {
  /**
   * whether to show the instructions snackbar.
   */
  instructionsSnackbarState: SnackbarState
  /**
   * whether the filters are shown (sidebar on desktop or modal on mobile).
   * This is the inner value, components should use the un-prefixed getter.
   */
  innerFilterVisible: boolean
  /**
   * (only for desktop layout) whether the filters were dismissed. If true,
   * the filters should be closed on SSR for the first load on desktop layout.
   */
  isFilterDismissed: boolean
  /**
   * whether the site layout is desktop (or mobile).
   */
  isDesktopLayout: boolean
  /**
   * the screen's max-width breakpoint.
   */
  breakpoint: RealBreakpoint
  /**
   * whether the request user agent is mobile or not.
   */
  dismissedBanners: BannerId[]
  /**
   * Whether to blur sensitive content in search and single result pages.
   * Value should *not* be set directly, use setShouldBlurSensitive(value: boolean)
   * to ensure necessary side-effects are executed.
   */
  shouldBlurSensitive: boolean
  /* A list of sensitive single result UUIDs the user has opted-into seeing */
  revealedSensitiveResults: string[]
  headerHeight: number

  /* The user-chosen color theme of the site. */
  colorMode: ColorMode
  /** whether the user has seen the dark mode toggle */
  isDarkModeSeen: boolean
}

export const breakpoints = Object.keys(ALL_SCREEN_SIZES)

export const defaultUiState: UiState = {
  instructionsSnackbarState: "not_shown",
  innerFilterVisible: false,
  isFilterDismissed: false,
  isDesktopLayout: false,
  breakpoint: "sm",
  dismissedBanners: [],
  shouldBlurSensitive: true,
  revealedSensitiveResults: [],
  headerHeight: 80,
  colorMode: "system",
  isDarkModeSeen: false,
}

export const useUiStore = defineStore("ui", {
  state: (): UiState => ({ ...defaultUiState }),

  getters: {
    cookieState(state): OpenverseCookieState["ui"] {
      return {
        instructionsSnackbarState: state.instructionsSnackbarState,
        isFilterDismissed: state.isFilterDismissed,
        breakpoint: state.breakpoint,
        dismissedBanners: Array.from(this.dismissedBanners),
        colorMode: state.colorMode,
        isDarkModeSeen: state.isDarkModeSeen,
      }
    },
    areInstructionsVisible(state): boolean {
      return state.instructionsSnackbarState === "visible"
    },

    /**
     * On desktop, we only hide the filters sidebar if it was
     * specifically dismissed on the desktop layout.
     *
     * The filters state could diverge if the layout changed from desktop to mobile:
     * closing the filters on mobile sets `isFilterVisible` to false, but does not
     * save the `isFilterDismissed` because it only applies on the desktop layout.
     *
     * This getter correct the state if it diverged, and then returns the visibility state.
     */
    isFilterVisible(state: UiState): boolean {
      if (
        state.isDesktopLayout &&
        !state.isFilterDismissed &&
        !state.innerFilterVisible
      ) {
        state.innerFilterVisible = true
      }
      return state.innerFilterVisible
    },
    /**
     * The analytics banner is shown if the user hasn't dismissed it yet.
     */
    shouldShowAnalyticsBanner(): boolean {
      return !this.dismissedBanners.includes("analytics")
    },
  },

  actions: {
    /**
     * The translation banner is shown if the translated percentage is below 90%,
     * and the banner for the current locale was not dismissed (status from cookies).
     */
    shouldShowTranslationBanner(localeProperties: LocaleObject): boolean {
      const locale = localeProperties.code
      return (
        !this.dismissedBanners.includes(`translation-${locale}`) &&
        needsTranslationBanner(localeProperties)
      )
    },
    showInstructionsSnackbar() {
      if (this.instructionsSnackbarState === "not_shown") {
        this.instructionsSnackbarState = "visible"
      }
    },

    hideInstructionsSnackbar() {
      if (this.instructionsSnackbarState === "visible") {
        this.instructionsSnackbarState = "not_shown"
      }
    },

    dismissInstructionsSnackbar() {
      this.instructionsSnackbarState = "dismissed"
    },

    /**
     * Given a list of key value pairs of UI state parameters and their states,
     * populate the store state to match the cookie.
     *
     * Since the cookies are passed through `JSON.parse()`, they can have the
     * wrong types. This function resets cookies to the default value if their
     * type is incorrect.
     *
     * @param cookies - mapping of UI state parameters and their states.
     */
    initFromCookies(cookies: OpenverseCookieState["ui"]) {
      let breakpoint = this.breakpoint
      if (
        cookies.breakpoint &&
        Object.keys(ALL_SCREEN_SIZES).includes(cookies.breakpoint)
      ) {
        breakpoint = cookies.breakpoint
      }
      this.updateBreakpoint(breakpoint, false)

      if (typeof cookies.isFilterDismissed === "boolean") {
        this.isFilterDismissed = cookies.isFilterDismissed
      }

      this.innerFilterVisible = this.isDesktopLayout
        ? !this.isFilterDismissed
        : false

      if (Array.isArray(cookies.dismissedBanners)) {
        this.dismissedBanners = cookies.dismissedBanners
      }

      if (isColorMode(cookies.colorMode)) {
        this.setColorMode(cookies.colorMode, false)
      }

      if (typeof cookies.isDarkModeSeen === "boolean") {
        this.setIsDarkModeSeen(cookies.isDarkModeSeen, false)
      }

      this.writeToCookie()
    },
    /**
     * Write the current state of the feature flags to the cookie. These cookies
     * are read in the corresponding `initFromCookies` method.
     */
    writeToCookie() {
      const uiCookie = useCookie<OpenverseCookieState["ui"]>(
        "ui",
        persistentCookieOptions
      )

      uiCookie.value = {
        ...defaultPersistientCookieState.ui,
        ...this.cookieState,
      }
    },

    /**
     * If the breakpoint is different from the state, updates the state, and saves it into app cookies.
     *
     * @param breakpoint - the `min-width` tailwind breakpoint for the screen width.
     * @param saveToCookie - whether to save the new breakpoint in the cookie.
     */
    updateBreakpoint(breakpoint: RealBreakpoint, saveToCookie = true) {
      if (this.breakpoint === breakpoint) {
        return
      }

      this.breakpoint = breakpoint

      if (saveToCookie) {
        this.writeToCookie()
      }

      this.isDesktopLayout = desktopBreakpoints.includes(breakpoint)
    },

    /**
     * Sets the filter state based on the `visible` parameter.
     * If the filter state is changed on desktop, updates the `isFilterDismissed`
     * 'ui' cookie value.
     *
     * @param visible - whether the filters should be visible.
     */
    setFiltersState(visible: boolean) {
      this.innerFilterVisible = visible
      if (this.isDesktopLayout) {
        this.isFilterDismissed = !visible

        this.writeToCookie()
      }
    },

    /**
     * Toggles filter state and saves the new state in a cookie.
     */
    toggleFilters() {
      this.setFiltersState(!this.isFilterVisible)
    },
    /**
     * If the banner wasn't dismissed before, dismisses it and saves the new state in a cookie.
     * @param bannerId - the id of the banner to dismiss.
     */
    dismissBanner(bannerId: BannerId) {
      if (this.dismissedBanners.includes(bannerId)) {
        return
      }

      this.dismissedBanners.push(bannerId)

      this.writeToCookie()
    },
    isBannerDismissed(bannerId: BannerId) {
      return this.dismissedBanners.includes(bannerId)
    },
    /**
     * Similar to CSS `@media` queries, this function returns a boolean
     * indicating whether the current breakpoint is greater than or equal to
     * the breakpoint passed as a parameter.
     */
    isBreakpoint(breakpoint: RealBreakpoint): boolean {
      return (
        breakpoints.indexOf(breakpoint) >= breakpoints.indexOf(this.breakpoint)
      )
    },
    setShouldBlurSensitive(value: boolean) {
      this.shouldBlurSensitive = value
      this.revealedSensitiveResults = []
    },

    /**
     * Update the user's preferred color mode.
     *
     * @param colorMode - the user's preferred color mode.
     * @param saveToCookie - whether to save the new breakpoint in the cookie.
     */
    setColorMode(colorMode: ColorMode, saveToCookie = true) {
      this.colorMode = colorMode

      if (saveToCookie) {
        this.writeToCookie()
      }
    },

    /**
     * Update the value of whether the user has seen dark mode.
     *
     * @param value - the new value of whether the user has seen dark mode
     * @param saveToCookie - whether to save the new breakpoint in the cookie.
     */
    setIsDarkModeSeen(value: boolean, saveToCookie = true) {
      this.isDarkModeSeen = value

      if (saveToCookie) {
        this.writeToCookie()
      }
    },
    setHeaderHeight(height: number) {
      this.headerHeight = Math.max(height, 80)
    },
  },
})
