// @vitest-environment jsdom

import { beforeEach, describe, expect, it } from "vitest"
import { setActivePinia, createPinia } from "~~/test/unit/test-utils/pinia"

import { AUDIO, IMAGE } from "#shared/constants/media"
import type { MediaProvider } from "#shared/types/media-provider"
import { useProviderStore } from "~/stores/provider"

const testProviders: MediaProvider[] = [
  {
    source_name: "test_source",
    display_name: "",
    source_url: "https://test.org",
    logo_url: null,
    media_count: 4,
  },
  {
    source_name: "wikimedia",
    display_name: "Wikimedia Commons",
    source_url: "https://commons.wikimedia.org",
    logo_url: null,
    media_count: 47823833,
  },
  {
    source_name: "wordpress",
    display_name: "WP Photo Directory",
    source_url: "https://wordpress.org/photos",
    logo_url: null,
    media_count: 154,
  },
]

describe("provider store", () => {
  let providerStore: ReturnType<typeof useProviderStore>
  beforeEach(() => {
    setActivePinia(createPinia())
    providerStore = useProviderStore()
  })

  it("sets the default state", () => {
    expect(providerStore.providers.audio.length).toEqual(0)
    expect(providerStore.providers.image.length).toEqual(0)
    expect(providerStore.fetchState).toEqual({
      [AUDIO]: { hasStarted: false, isFetching: false, fetchingError: null },
      [IMAGE]: { hasStarted: false, isFetching: false, fetchingError: null },
    })
  })

  it.each`
    providerCode     | displayName
    ${"wikimedia"}   | ${"Wikimedia Commons"}
    ${"wordpress"}   | ${"WP Photo Directory"}
    ${"test_source"} | ${"Test Source"}
  `(
    "getProviderName returns provider name or capitalizes providerCode",
    async ({ providerCode, displayName }) => {
      await providerStore.$patch({ providers: { [IMAGE]: testProviders } })
      expect(providerStore.getProviderName(providerCode, IMAGE)).toEqual(
        displayName
      )
    }
  )
})
