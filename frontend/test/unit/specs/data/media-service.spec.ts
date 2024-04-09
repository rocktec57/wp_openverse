import { mockCreateApiService } from "~~/test/unit/test-utils/api-service-mock"

import { initServices } from "~/stores/media/services"

const API_IMAGES_ENDPOINT = "images/"
const API_AUDIO_ENDPOINT = "audio/"
const BASE_URL = "https://www.mockapiservice.openverse.engineering/v1/"

beforeAll(() => {
  // eslint-disable-next-line @typescript-eslint/ban-ts-comment
  // @ts-ignore
  jest.useFakeTimers("modern")
  jest.setSystemTime(new Date("Tue, 17 Dec 2019 20:20:00 GMT"))
})

afterAll(() => {
  jest.useRealTimers()
})

describe("Media Service search and recordSearchTime", () => {
  it("should not send a SEARCH_RESPONSE_TIME analytics event if any required header is missing", async () => {
    mockCreateApiService((axiosMockAdapter) => {
      axiosMockAdapter.onGet().reply(200, {})
    })

    const res = await initServices.image().search({})

    expect(res.eventPayload).not.toBeDefined()
  })

  it("should not send a SEARCH_RESPONSE_TIME analytics event if the response was locally cached", async () => {
    mockCreateApiService((axiosMockAdapter) => {
      axiosMockAdapter.onGet().reply(() => {
        return [
          200,
          {},
          {
            date: "Tue, 17 Dec 2019 19:00:00 GMT",
            "cf-ray": "230b030023ae284c-SJC",
            "cf-cache-status": "HIT",
          },
        ]
      })
    })

    const res = await initServices.audio().search({})

    expect(res.eventPayload).not.toBeDefined()
  })

  it("should not send a SEARCH_RESPONSE_TIME analytics event if the cf-ray is malformed", async () => {
    mockCreateApiService((axiosMockAdapter) => {
      axiosMockAdapter.onGet().reply((config) => {
        // force config.url so the responseURL is set in the AxiosRequest
        config.url = BASE_URL + config.url
        return [
          200,
          {},
          {
            date: "Tue, 17 Dec 2019 20:30:00 GMT",
            "cf-ray": "230b030023ae284c",
            "cf-cache-status": "HIT",
          },
        ]
      })
    })

    const res = await initServices.audio().search({})

    expect(res.eventPayload).not.toBeDefined()
  })

  it("should send SEARCH_RESPONSE_TIME analytics with correct parameters", async () => {
    mockCreateApiService((axiosMockAdapter) => {
      axiosMockAdapter
        .onGet(API_IMAGES_ENDPOINT, { params: { q: "apple" } })
        .reply((config) => {
          config.url = BASE_URL + config.url + "?q=apple"
          return [
            200,
            {},
            {
              date: "Tue, 17 Dec 2019 20:20:02 GMT",
              "cf-ray": "230b030023ae2822-SJC",
              "cf-cache-status": "HIT",
            },
          ]
        })

      axiosMockAdapter
        .onGet(API_AUDIO_ENDPOINT, { params: { q: "table", peaks: "true" } })
        .reply((config) => {
          config.url = BASE_URL + config.url + "?q=table&peaks=true"
          return [
            200,
            {},
            {
              date: "Tue, 17 Dec 2019 20:20:03 GMT",
              "cf-ray": "240b030b23ae2822-LHR",
              "cf-cache-status": "MISS",
            },
          ]
        })
    })

    const IMAGE_QUERY_PARAMS = { q: "apple" }
    const imageRes = await initServices.image().search(IMAGE_QUERY_PARAMS)

    expect(imageRes.eventPayload).toEqual({
      cfCacheStatus: "HIT",
      cfRayIATA: "SJC",
      elapsedTime: 2,
      queryString: "?q=apple",
      mediaType: "image",
    })

    const AUDIO_QUERY_PARAMS = { q: "table" }
    const audioRes = await initServices.audio().search(AUDIO_QUERY_PARAMS)

    expect(audioRes.eventPayload).toEqual({
      cfCacheStatus: "MISS",
      cfRayIATA: "LHR",
      elapsedTime: 3,
      queryString: "?q=table&peaks=true",
      mediaType: "audio",
    })
  })
})
