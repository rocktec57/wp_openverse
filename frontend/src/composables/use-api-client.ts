import { useNuxtApp } from "#imports"

import { createApiClient } from "~/data/api-service"
import { useFeatureFlagStore } from "~/stores/feature-flag"

export function useApiClient() {
  const { $openverseApiToken: accessToken } = useNuxtApp()
  const featureFlagStore = useFeatureFlagStore()

  const fakeSensitive =
    featureFlagStore.isOn("fake_sensitive") &&
    featureFlagStore.isOn("fetch_sensitive")

  return createApiClient({ accessToken, fakeSensitive })
}
