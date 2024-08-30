import { computed, useUiStore } from "#imports"

import { useFeatureFlagStore } from "~/stores/feature-flag"

export const DARK_MODE_CLASS = "dark-mode"
export const LIGHT_MODE_CLASS = "light-mode"

/**
 * Determines the dark mode setting based on user preference or feature flag.
 *
 * When dark mode toggling is disabled, the site is in "light mode" unless
 * the `force_dark_mode` feature flag is on.
 *
 * When the "dark_mode_ui_toggle" flag is enabled, the site will respect
 * the user system preference by default.
 *
 */
export function useDarkMode() {
  const uiStore = useUiStore()
  const featureFlagStore = useFeatureFlagStore()

  const darkModeToggleable = computed(() =>
    featureFlagStore.isOn("dark_mode_ui_toggle")
  )
  const forceDarkMode = computed(() => featureFlagStore.isOn("force_dark_mode"))

  const colorMode = computed(() => {
    if (darkModeToggleable.value && !forceDarkMode.value) {
      return uiStore.colorMode
    }
    return forceDarkMode.value ? "dark" : "light"
  })

  const cssClass = computed(() => {
    return {
      light: LIGHT_MODE_CLASS,
      dark: DARK_MODE_CLASS,
      system: "",
    }[colorMode.value]
  })

  return {
    colorMode,
    cssClass,
  }
}
