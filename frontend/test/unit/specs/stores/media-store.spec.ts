import { expect, describe, it, beforeEach } from "vitest"
import { setActivePinia, createPinia } from "~~/test/unit/test-utils/pinia"
import { image as imageObject } from "~~/test/unit/fixtures/image"

import {
  ALL_MEDIA,
  AUDIO,
  IMAGE,
  type SupportedMediaType,
  supportedMediaTypes,
  VIDEO,
} from "#shared/constants/media"
import { NO_RESULT } from "#shared/constants/errors"
import { ON } from "#shared/constants/feature-flag"
import { deepClone } from "#shared/utils/clone"
import { ImageDetail, Media } from "#shared/types/media"
import { initialResults, useMediaStore } from "~/stores/media"
import { useSearchStore } from "~/stores/search"
import { useFeatureFlagStore } from "~/stores/feature-flag"

// Retrieve the type of the first argument to
// useMediaStore.setMedia()
type SetMediaParams = Parameters<
  ReturnType<typeof useMediaStore>["setMedia"]
>[0]

const uuids = [
  "0dea3af1-27a4-4635-bab6-4b9fb76a59f5",
  "32c22b5b-f2f9-47db-b64f-6b86c2431942",
  "fd527776-00f8-4000-9190-724fc4f07346",
  "81e551de-52ab-4852-90eb-bc3973c342a0",
]
const items = (mediaType: SupportedMediaType): Media[] =>
  uuids.map((uuid, i) => ({
    id: uuid,
    title: `${mediaType} ${i + 1}`,
    creator: `creator ${i + 1}`,
    tags: [],
    sensitivity: [],
    originalTitle: `Title ${i + 1}`,
    url: "",
    foreign_landing_url: "",
    license: "by",
    license_version: "4.0",
    attribution: "",
    frontendMediaType: mediaType,
    provider: "",
    source: "",
    providerName: "",
    sourceName: "",
    detail_url: "",
    related_url: "",
    isSensitive: false,
  }))

const audioItems = items(AUDIO)
const imageItems = items(IMAGE)
const testResultItems = (mediaType: SupportedMediaType) =>
  items(mediaType).reduce<Record<string, Media>>((acc, item) => {
    acc[item.id] = item
    return acc
  }, {})

const testResult = (mediaType: SupportedMediaType) => ({
  count: 240,
  items: testResultItems(mediaType),
  page: 2,
  pageCount: 20,
})

describe("media store", () => {
  describe("state", () => {
    it("sets default state", () => {
      setActivePinia(createPinia())
      const mediaStore = useMediaStore()

      expect(mediaStore.results).toEqual({
        image: { ...initialResults },
        audio: { ...initialResults },
      })
      expect(mediaStore.mediaFetchState).toEqual({
        audio: {
          fetchingError: null,
          hasStarted: false,
          isFetching: false,
          isFinished: false,
        },
        image: {
          fetchingError: null,
          hasStarted: false,
          isFetching: false,
          isFinished: false,
        },
      })
    })
  })

  describe("getters", () => {
    beforeEach(() => {
      setActivePinia(createPinia())
    })

    it("searchType falls back to ALL_MEDIA for additional search types", () => {
      const featureFlagStore = useFeatureFlagStore()
      featureFlagStore.toggleFeature("additional_search_types", ON)

      const searchStore = useSearchStore()
      searchStore.setSearchType(VIDEO)

      const mediaStore = useMediaStore()
      expect(mediaStore._searchType).toEqual(ALL_MEDIA)
    })

    it("getItemById returns undefined if there are no items", () => {
      const mediaStore = useMediaStore()
      expect(mediaStore.getItemById(IMAGE, "foo")).toBeUndefined()
    })

    it("getItemById returns correct item", () => {
      const mediaStore = useMediaStore()
      const expectedItem = imageItems[0]
      mediaStore.results.image.items = { foo: expectedItem }
      expect(mediaStore.getItemById(IMAGE, "foo")).toEqual(expectedItem)
    })

    it("resultItems returns correct items", () => {
      const mediaStore = useMediaStore()
      mediaStore.results.audio = testResult(AUDIO)
      mediaStore.results.image = testResult(IMAGE)

      expect(mediaStore.resultItems).toEqual({
        [AUDIO]: audioItems,
        [IMAGE]: imageItems,
      })
    })

    it("allMedia returns correct items", () => {
      const mediaStore = useMediaStore()
      mediaStore.results.audio = testResult(AUDIO)
      mediaStore.results.image = testResult(IMAGE)

      expect(mediaStore.allMedia).toEqual([
        imageItems[0],
        audioItems[0],
        audioItems[1],
        imageItems[1],
        imageItems[2],
        imageItems[3],
      ])
    })

    /**
     * Normally, this should randomly intersperse items from other media types.
     * Now, however, it simply returns the audio items in order.
     * TODO: Add video and check for randomization.
     */
    it("allMedia returns items even if there are no images", () => {
      const mediaStore = useMediaStore()
      mediaStore.results.audio = testResult(AUDIO)

      expect(mediaStore.allMedia).toEqual(audioItems)
    })
    it("resultCountsPerMediaType returns correct items for %s", () => {
      const mediaStore = useMediaStore()
      mediaStore.results.image = testResult(IMAGE)

      // image is first in the returned list
      expect(mediaStore.resultCountsPerMediaType).toEqual([
        [IMAGE, testResult(IMAGE).count],
        [AUDIO, initialResults.count],
      ])
    })

    it.each`
      searchType   | count
      ${ALL_MEDIA} | ${240}
      ${AUDIO}     | ${0}
      ${IMAGE}     | ${240}
    `("resultCount for $searchType returns $count", ({ searchType, count }) => {
      const mediaStore = useMediaStore()
      const searchStore = useSearchStore()
      searchStore.setSearchType(searchType)
      mediaStore.results.image = testResult(IMAGE)

      expect(mediaStore.resultCount).toEqual(count)
    })

    it.each`
      searchType | audioError | fetchState
      ${ALL_MEDIA} | ${{ code: NO_RESULT }} | ${{
  fetchingError: null,
  hasStarted: true,
  isFetching: true,
  isFinished: false,
}}
      ${ALL_MEDIA} | ${{ statusCode: 429 }} | ${{
  fetchingError: {
    requestKind: "search",
    statusCode: 429,
    searchType: ALL_MEDIA,
  },
  hasStarted: true,
  isFetching: true,
  isFinished: false,
}}
      ${AUDIO} | ${{ statusCode: 429 }} | ${{
  fetchingError: {
    requestKind: "search",
    statusCode: 429,
    searchType: AUDIO,
  },
  hasStarted: true,
  isFetching: false,
  isFinished: true,
}}
      ${IMAGE} | ${null} | ${{
  fetchingError: null,
  hasStarted: true,
  isFetching: true,
  isFinished: false,
}}
    `(
      "fetchState for $searchType returns $fetchState",
      ({ searchType, audioError, fetchState }) => {
        const mediaStore = useMediaStore()
        const searchStore = useSearchStore()
        searchStore.setSearchType(searchType)
        const audioFetchError = audioError
          ? { requestKind: "search", searchType: AUDIO, ...audioError }
          : null
        mediaStore._updateFetchState(AUDIO, "end", audioFetchError)
        mediaStore._updateFetchState(IMAGE, "start")

        expect(mediaStore.fetchState).toEqual(fetchState)
      }
    )

    it("returns NO_RESULT error if all media types have NO_RESULT errors", () => {
      const mediaStore = useMediaStore()
      const searchStore = useSearchStore()
      searchStore.setSearchType(ALL_MEDIA)
      mediaStore._updateFetchState(AUDIO, "end", {
        requestKind: "search",
        searchType: AUDIO,
        code: NO_RESULT,
      })
      mediaStore._updateFetchState(IMAGE, "end", {
        requestKind: "search",
        searchType: IMAGE,
        code: NO_RESULT,
      })

      expect(mediaStore.fetchState).toEqual({
        fetchingError: {
          requestKind: "search",
          code: NO_RESULT,
          searchType: ALL_MEDIA,
        },
        hasStarted: true,
        isFetching: false,
        isFinished: true,
      })
    })

    it("fetchState for ALL_MEDIA returns no error when media types have no errors", () => {
      const mediaStore = useMediaStore()
      const searchStore = useSearchStore()
      searchStore.setSearchType(ALL_MEDIA)
      mediaStore._updateFetchState(AUDIO, "end")
      mediaStore._updateFetchState(IMAGE, "end")

      expect(mediaStore.fetchState).toEqual({
        fetchingError: null,
        hasStarted: true,
        isFetching: false,
        isFinished: false,
      })
    })

    it("fetchState for ALL_MEDIA returns compound error if all types have errors", () => {
      const mediaStore = useMediaStore()
      const searchStore = useSearchStore()
      searchStore.setSearchType(ALL_MEDIA)

      mediaStore._updateFetchState(AUDIO, "end", {
        code: "NO_RESULT",
        message: "Error",
        requestKind: "search",
        searchType: "audio",
        statusCode: 500,
      })

      mediaStore._updateFetchState(IMAGE, "end", {
        code: "NO_RESULT",
        message: "Error",
        requestKind: "search",
        searchType: IMAGE,
        statusCode: 500,
      })

      expect(mediaStore.fetchState).toEqual({
        fetchingError: {
          code: "NO_RESULT",
          message: "Error",
          requestKind: "search",
          searchType: ALL_MEDIA,
          statusCode: 500,
        },
        hasStarted: true,
        isFetching: false,
        isFinished: true,
      })
    })
  })

  describe("actions", () => {
    beforeEach(() => {
      setActivePinia(createPinia())
    })

    it("setMedia updates state persisting images", () => {
      const mediaStore = useMediaStore()

      const img1 = imageItems[0]
      const img2 = imageItems[1]

      mediaStore.results.image.items = { [img1.id]: img1 }

      const params: SetMediaParams = {
        media: { [img2.id]: img2 as ImageDetail },
        mediaCount: 2,
        page: 2,
        pageCount: 1,
        shouldPersistMedia: true,
        mediaType: IMAGE,
      }
      mediaStore.setMedia(params)

      expect(mediaStore.results.image.items).toEqual({
        [img1.id]: img1,
        [img2.id]: img2,
      })
      expect(mediaStore.results.image.count).toBe(params.mediaCount)
      expect(mediaStore.results.image.page).toBe(params.page)
    })

    it("setMedia updates state not persisting images", () => {
      const mediaStore = useMediaStore()
      const image = { ...imageObject, id: "img0" }

      const img = imageObject

      mediaStore.results.image.items = {
        ...mediaStore.results.image.items,
        image,
      }
      mediaStore.results.image.count = 10

      const params: SetMediaParams = {
        media: { [img.id]: img },
        mediaCount: 2,
        mediaType: IMAGE,
        page: 2,
        pageCount: 1,
        shouldPersistMedia: false,
      }
      mediaStore.setMedia(params)

      expect(mediaStore.results.image).toEqual({
        items: { [img.id]: img },
        count: params.mediaCount,
        page: params.page,
        pageCount: params.pageCount,
      })
    })

    it("setMedia updates state with default count and page", () => {
      const mediaStore = useMediaStore()

      const img = imageItems[0]
      mediaStore.results.image.items = { [img.id]: img }
      const params: SetMediaParams = {
        media: { [img.id]: img },
        mediaType: IMAGE,
        shouldPersistMedia: false,
        pageCount: 1,
      }

      mediaStore.setMedia(params)

      expect(mediaStore.results.image.count).toEqual(0)
      expect(mediaStore.results.image.page).toEqual(1)
    })

    it("clearMedia resets the results", () => {
      const mediaStore = useMediaStore()
      const searchStore = useSearchStore()

      searchStore.setSearchType(ALL_MEDIA)

      mediaStore.results.image.items = {
        ...mediaStore.results.image.items,
        ...testResult(IMAGE).items,
      }
      mediaStore.results.audio.items = {
        ...mediaStore.results.audio.items,
        ...testResult(AUDIO).items,
      }

      mediaStore.clearMedia()

      supportedMediaTypes.forEach((mediaType) => {
        expect(mediaStore.results[mediaType]).toEqual(initialResults)
      })
    })

    it("setMediaProperties merges the existing media item together with the properties passed in allowing overwriting", () => {
      const hasLoaded = true
      const mediaStore = useMediaStore()

      mediaStore.results.audio = testResult(AUDIO)

      const existingMediaItem = deepClone(
        mediaStore.getItemById(AUDIO, uuids[0])
      )
      mediaStore.setMediaProperties(AUDIO, uuids[0], {
        hasLoaded,
      })

      expect(mediaStore.getItemById(AUDIO, uuids[0])).toMatchObject({
        ...existingMediaItem,
        hasLoaded,
      })
    })
  })
})
