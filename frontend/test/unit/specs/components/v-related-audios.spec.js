import { screen } from "@testing-library/vue"

import { render } from "~~/test/unit/test-utils/render"
import { getAudioObj } from "~~/test/unit/fixtures/audio"

import VRelatedAudio from "~/components/VAudioDetails/VRelatedAudio.vue"

const audioResults = [getAudioObj(), getAudioObj()]

describe("RelatedAudios", () => {
  it("should render content when finished loading related audios", async () => {
    await render(VRelatedAudio, {
      propsData: {
        media: audioResults,
        fetchState: { isFetching: false, isError: false },
      },
      stubs: { LoadingIcon: true, VAudioThumbnail: true },
    })

    screen.getByText(/related audio/i)

    expect(screen.queryAllByLabelText("Play")).toHaveLength(
      // Two for each as the "row" layout rendered by VRelatedAudio
      // renders a "large" and "small" version that are visually hidden by a parent
      // depending on the breakpoint (but critically still rendered in the
      // DOM)
      audioResults.length * 2
    )
  })
})
