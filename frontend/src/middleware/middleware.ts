import { useProviderStore } from "~/stores/provider"
import { useFeatureFlagStore } from "~/stores/feature-flag"
import { useUiStore } from "~/stores/ui"

import { cookieOptions } from "~/utils/cookies"

import type { Context, Middleware } from "@nuxt/types"

/**
 * In embedded mode, the app sends its url
 * to the outer window to improve the user experience.
 *
 * The app is in embedded mode by default. To set it to
 * standalone mode with larger header and a footer,
 * add `?embedded=false` to the end of the URL.
 *
 * Messages sent to the outer window have the following format:
 * `{type: <event type>, value: <event value>}`.
 * Currently, one event type is used:
 * - `urlChange` sends the relative path of the URL on every URL change.
 */
const middleware: Middleware = async ({
  $cookies,
  $ua,
  query,
  $pinia,
}: Context) => {
  /* Provider store */
  const providerStore = useProviderStore($pinia)
  await providerStore.fetchMediaProviders()

  /* Feature flag store */

  const featureFlagStore = useFeatureFlagStore($pinia)
  featureFlagStore.initFromCookies($cookies.get("features") ?? {})
  featureFlagStore.initFromQuery(query)

  /* UI store */

  const uiStore = useUiStore($pinia)
  const isMobileUa = $ua ? $ua.isMobile : false

  $cookies.set("uiIsMobileUa", isMobileUa, { ...cookieOptions })
  uiStore.initFromCookies($cookies.getAll() ?? {})
}
export default middleware
