import { Context } from "@nuxt/types"
import { AxiosError, AxiosHeaders } from "axios"

import type { RequestKind } from "~/types/fetch-state"

import errorsPlugin from "~/plugins/errors"

import { SupportedSearchType, supportedSearchTypes } from "~/constants/media"

const getNotFoundError = () =>
  new AxiosError(
    "Beep boop, something went wrong :(",
    AxiosError.ERR_BAD_REQUEST,
    undefined,
    undefined,
    {
      statusText: "",
      data: "",
      headers: {},
      config: { headers: new AxiosHeaders() },
      status: 404,
    }
  )

const getNetworkError = () =>
  new AxiosError(
    "Wowee, this is really bad!",
    AxiosError.ERR_NETWORK,
    undefined,
    undefined,
    undefined
  )

describe("Errors plugin", () => {
  const mockContext = {
    $sendCustomEvent: jest.fn(),
    $sentry: {
      captureException: jest.fn(),
    },
  } as unknown as Context
  const mockInject = jest.fn()

  const getPluginInstance = () =>
    mockInject.mock.calls[0][1] as Context["$processFetchingError"]

  beforeEach(() => {
    jest.resetAllMocks()
  })

  it("should inject the processFetchingError function", async () => {
    await errorsPlugin(mockContext, mockInject)

    expect(mockInject).toHaveBeenCalledWith(
      "processFetchingError",
      expect.any(Function)
    )
  })

  it("should ignore 404s for single result requests", async () => {
    await errorsPlugin(mockContext, mockInject)

    const plugin = getPluginInstance()

    const error = getNotFoundError()
    const fetchingError = plugin(error, "all", "single-result", {})

    expect(fetchingError).toMatchObject({
      message: error.message,
      code: error.code,
      statusCode: error.response!.status,
    })

    expect(mockContext.$sentry.captureException).not.toHaveBeenCalled()
    expect(mockContext.$sendCustomEvent).not.toHaveBeenCalled()
  })

  it.each(["provider", "related", "search"] as RequestKind[])(
    "should not ignore 404s for other request types",
    async (requestKind) => {
      await errorsPlugin(mockContext, mockInject)

      const plugin = getPluginInstance()

      const error = getNotFoundError()

      const fetchingError = plugin(error, "all", requestKind, {})

      expect(fetchingError).toMatchObject({
        message: error.message,
        code: error.code,
        statusCode: error.response!.status,
      })

      expect(mockContext.$sentry.captureException).toHaveBeenCalledWith(error, {
        extra: { fetchingError },
      })
      expect(mockContext.$sendCustomEvent).not.toHaveBeenCalled()
    }
  )

  const requestKinds = [
    "provider",
    "related",
    "single-result",
    "search",
  ] as RequestKind[]
  const combinations = requestKinds.reduce(
    (acc, requestKind) => [
      ...acc,
      ...supportedSearchTypes.map(
        (searchType) =>
          [requestKind, searchType] as [RequestKind, SupportedSearchType]
      ),
    ],
    [] as [RequestKind, SupportedSearchType][]
  )

  const processClientForBlock = (value: boolean) => {
    let originalValue: boolean

    beforeAll(() => {
      originalValue = process.client
      process.client = value
    })

    afterAll(() => {
      process.client = originalValue
    })
  }

  describe("client-side network errors", () => {
    processClientForBlock(true)

    it.each(combinations)(
      "should send %s %s client-side network errors to plausible instead of sentry",
      async (requestKind, searchType) => {
        await errorsPlugin(mockContext, mockInject)

        const plugin = getPluginInstance()

        const error = getNetworkError()

        const fetchingError = plugin(error, searchType, requestKind, {})

        expect(fetchingError).toMatchObject({
          message: error.message,
          code: error.code,
        })

        expect(mockContext.$sentry.captureException).not.toHaveBeenCalled()
        expect(mockContext.$sendCustomEvent).toHaveBeenCalledWith(
          "NETWORK_ERROR",
          {
            requestKind,
            searchType,
          }
        )
      }
    )
  })

  describe("server-side network errors", () => {
    processClientForBlock(false)

    it.each(combinations)(
      "should send %s %s client-side network errors to plausible instead of sentry",
      async (requestKind, searchType) => {
        await errorsPlugin(mockContext, mockInject)

        const plugin = getPluginInstance()

        const error = getNetworkError()

        const fetchingError = plugin(error, searchType, requestKind, {})

        expect(fetchingError).toMatchObject({
          message: error.message,
          code: error.code,
        })

        expect(mockContext.$sendCustomEvent).not.toHaveBeenCalled()
        expect(mockContext.$sentry.captureException).toHaveBeenCalledWith(
          error,
          {
            extra: { fetchingError },
          }
        )
      }
    )
  })
})
