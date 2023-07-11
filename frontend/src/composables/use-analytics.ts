import { computed, onMounted } from "vue"
import { useContext } from "@nuxtjs/composition-api"

import type { Events, EventName } from "~/types/analytics"
import { useUiStore } from "~/stores/ui"
import { useFeatureFlagStore } from "~/stores/feature-flag"

import { log } from "~/utils/console"

/**
 * The `ctx` parameter must be supplied if using this composable outside the
 * bounds of the composition API.
 */
export const useAnalytics = () => {
  const { $plausible } = useContext()
  const uiStore = useUiStore()
  const featureFlagStore = useFeatureFlagStore()

  onMounted(() => {
    featureFlagStore.syncAnalyticsWithLocalStorage()
  })

  /**
   * the Plausible props that work identically on the server-side and the
   * client-side; This excludes props that need `window`.
   */
  const isomorphicProps = computed(() => ({
    breakpoint: uiStore.breakpoint,
  }))

  /**
   * the Plausible props that work only on the client-side; This only includes
   * props that need `window`.
   */
  const windowProps = computed(() =>
    window
      ? {
          width: window.innerWidth,
          height: window.innerHeight,
        }
      : {}
  )

  /**
   * Send a custom event to Plausible. Mandatory props are automatically merged
   * with the event-specific props.
   *
   * @param name - the name of the event being recorded
   * @param payload - the additional information to record about the event
   */
  const sendCustomEvent = <T extends EventName>(
    name: T,
    payload: Events[T]
  ) => {
    log(`Analytics event: ${name}`, payload)
    $plausible.trackEvent(name, {
      props: {
        ...isomorphicProps.value,
        ...windowProps.value,
        ...payload,
      },
    })
  }

  return {
    sendCustomEvent,
  }
}
