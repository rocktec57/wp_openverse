import { defineStore } from "pinia"

import axios from "axios"

import type { FetchState } from "~/types/fetch-state"
import type {
  AudioDetail,
  DetailFromMediaType,
  ImageDetail,
} from "~/types/media"
import { isDetail, isMediaDetail } from "~/types/media"

import type { SupportedMediaType } from "~/constants/media"

import { initServices } from "~/stores/media/services"
import { useMediaStore } from "~/stores/media/index"
import { useProviderStore } from "~/stores/provider"
import { log } from "~/utils/console"

import type { NuxtError } from "@nuxt/types"

export type MediaItemState = {
  mediaType: SupportedMediaType | null
  mediaId: string | null
  mediaItem: DetailFromMediaType<SupportedMediaType> | null
  fetchState: FetchState<NuxtError>
}

export const useSingleResultStore = defineStore("single-result", {
  state: (): MediaItemState => ({
    mediaType: null,
    mediaId: null,
    mediaItem: null,
    fetchState: { isFetching: false, fetchingError: null },
  }),

  getters: {
    audio(state): AudioDetail | null {
      if (isDetail.audio(state.mediaItem)) {
        return state.mediaItem
      }
      return null
    },
    image(state): ImageDetail | null {
      if (isDetail.image(state.mediaItem)) {
        return state.mediaItem
      }
      return null
    },
  },

  actions: {
    _endFetching(error?: NuxtError) {
      this.fetchState.isFetching = false
      this.fetchState.fetchingError = error || null
    },
    _startFetching() {
      this.fetchState.isFetching = true
      this.fetchState.fetchingError = null
    },

    _updateFetchState(action: "start" | "end", option?: NuxtError) {
      action === "start" ? this._startFetching() : this._endFetching(option)
    },

    _addProviderName<T extends SupportedMediaType>(
      mediaItem: DetailFromMediaType<T>
    ): DetailFromMediaType<T> {
      const providerStore = useProviderStore()

      mediaItem.providerName = providerStore.getProviderName(
        mediaItem.provider,
        mediaItem.frontendMediaType
      )
      if (mediaItem.source) {
        mediaItem.sourceName = providerStore.getProviderName(
          mediaItem.source,
          mediaItem.frontendMediaType
        )
      }
      return mediaItem
    },
    reset() {
      this.mediaItem = null
      this.mediaType = null
      this.mediaId = null
      this.fetchState.isFetching = false
      this.fetchState.fetchingError = null
    },

    /**
     * Set the media item with the display name of its provider
     * and its type. Reset the other media type item.
     * If the media item is null, reset both media items.
     */
    setMediaItem(mediaItem: AudioDetail | ImageDetail | null) {
      if (mediaItem) {
        this.mediaItem = this._addProviderName(mediaItem)
        this.mediaType = mediaItem.frontendMediaType
        this.mediaId = mediaItem.id
      } else {
        this.mediaItem = null
        this.mediaType = null
        this.mediaId = null
      }
    },

    /**
     * If the item is already in the media store, reuse it.
     * Otherwise, set the media type and id, fetch the media
     * itself later.
     */
    setMediaById(type: SupportedMediaType, id: string) {
      if (this.mediaId === id && isMediaDetail(this.mediaItem, type)) return
      const existingItem = useMediaStore().getItemById(type, id)
      if (existingItem) {
        this.setMediaItem(existingItem)
      } else {
        this.mediaId = id
        this.mediaType = type
      }
    },

    getExistingItem<T extends SupportedMediaType>(
      type: T,
      id: string
    ): DetailFromMediaType<T> | null {
      if (this.mediaId === id && isMediaDetail<T>(this.mediaItem, type)) {
        return this.mediaItem
      }
      const existingItem = useMediaStore().getItemById(type, id)
      if (existingItem) {
        return existingItem as DetailFromMediaType<T>
      }
      return null
    },

    /**
     * Check if the `id` matches the `mediaId` and the media item
     * is already fetched. If middleware only set the `id` and
     * did not set the media, fetch the media item.
     *
     * Fetch the related media if necessary.
     */
    async fetch<T extends SupportedMediaType>(type: T, id: string) {
      const existingItem = this.getExistingItem(type, id)

      return existingItem
        ? existingItem
        : ((await this.fetchMediaItem<T>(type, id)) as DetailFromMediaType<T>)
    },

    /**
     * Fetch the media item from the API.
     * On error, send the error to Sentry and return null.
     */
    async fetchMediaItem<MediaType extends SupportedMediaType>(
      type: MediaType,
      id: string
    ) {
      try {
        this._updateFetchState("start")
        const accessToken = this.$nuxt.$openverseApiToken
        const service = initServices[type](accessToken)
        const item = this._addProviderName(await service.getMediaDetail(id))

        this.setMediaItem(item)
        this._updateFetchState("end")

        return item as DetailFromMediaType<MediaType>
      } catch (error) {
        this.reset()
        const statusCode = getErrorStatusCode(error)
        const message = `Error fetching single ${type} item with id ${id}`

        this._updateFetchState("end", { statusCode, message })

        log(`${message}. Sending error to Sentry: ${JSON.stringify(error)}`)
        this.$nuxt.$sentry.captureException(error)

        return null
      }
    },
  },
})

const getErrorStatusCode = (error: unknown) =>
  axios.isAxiosError(error) && error.response?.status
    ? error.response.status
    : 404
