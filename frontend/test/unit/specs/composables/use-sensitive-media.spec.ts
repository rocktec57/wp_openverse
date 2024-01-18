import { useSensitiveMedia } from "~/composables/use-sensitive-media"
import { useAnalytics } from "~/composables/use-analytics"
import type { Sensitivity } from "~/constants/content-safety"

let mockUseUiStore = {
  shouldBlurSensitive: true,
  revealedSensitiveResults: [],
}

jest.mock("~/composables/use-analytics")

jest.mock("~/stores/ui", () => ({
  useUiStore: () => mockUseUiStore,
}))

describe("useSensitiveMedia composable", () => {
  const sendCustomEventMock = jest.fn()

  let mockMedia: {
    id: string
    sensitivity: Sensitivity[]
    isSensitive: boolean
  }

  beforeEach(() => {
    mockMedia = {
      id: "mock-id",
      sensitivity: [],
      isSensitive: false,
    }
    mockUseUiStore = {
      shouldBlurSensitive: true,
      revealedSensitiveResults: [],
    }

    sendCustomEventMock.mockClear()
    const mockedUseAnalytics = useAnalytics as jest.Mock<
      ReturnType<typeof useAnalytics>
    >
    mockedUseAnalytics.mockImplementation(() => ({
      sendCustomEvent: sendCustomEventMock,
    }))
  })

  it("should return non-sensitive when media is null", () => {
    const { visibility } = useSensitiveMedia(null)
    expect(visibility.value).toBe("non-sensitive")
  })

  it("should return non-sensitive when media is not sensitive", () => {
    const { visibility } = useSensitiveMedia(mockMedia)
    expect(visibility.value).toBe("non-sensitive")
  })

  it("should return sensitive-hidden when media is sensitive and shouldBlurSensitive is true", () => {
    mockMedia.isSensitive = true

    const { visibility } = useSensitiveMedia(mockMedia)
    expect(visibility.value).toBe("sensitive-hidden")
  })

  it("should return sensitive-shown when media is sensitive and shouldBlurSensitive is false", () => {
    mockMedia.isSensitive = true
    mockUseUiStore.shouldBlurSensitive = false

    const { visibility } = useSensitiveMedia(mockMedia)
    expect(visibility.value).toBe("sensitive-shown")
  })

  it("should reveal sensitive media", () => {
    mockMedia.isSensitive = true

    const { reveal, visibility } = useSensitiveMedia(mockMedia)
    reveal()

    expect(visibility.value).toBe("sensitive-shown")
  })

  it("should hide sensitive media", () => {
    mockMedia.isSensitive = true

    const { reveal, hide, visibility } = useSensitiveMedia(mockMedia)
    reveal()
    hide()

    expect(visibility.value).toBe("sensitive-hidden")
  })

  it("should correctly report if a media is hidden", () => {
    mockMedia.isSensitive = true

    const { reveal, hide, isHidden } = useSensitiveMedia(mockMedia)
    reveal()
    hide()

    expect(isHidden.value).toBe(true)
  })

  it("should correctly report if a media can be hidden", () => {
    mockMedia.isSensitive = true
    mockUseUiStore.shouldBlurSensitive = false

    const { reveal, canBeHidden } = useSensitiveMedia(mockMedia)
    reveal()

    expect(canBeHidden.value).toBe(false)
  })
})
