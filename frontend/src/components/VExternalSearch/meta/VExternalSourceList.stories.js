import { h } from "vue"

import { useFeatureFlagStore } from "~/stores/feature-flag"
import { useSearchStore } from "~/stores/search"

import VExternalSourceList from "~/components/VExternalSearch/VExternalSourceList.vue"

const meta = {
  title: "Components/VExternalSourceList",
  component: VExternalSourceList,
}

export default meta

const Template = (args) => ({
  components: { VExternalSourceList },
  setup() {
    const featureFlagStore = useFeatureFlagStore()
    featureFlagStore.toggleFeature("additional_search_types", "on")
    const searchStore = useSearchStore()
    searchStore.setSearchType(args.type)
    return () => h(VExternalSourceList, { "search-term": "cat" })
  },
})

export const Images = {
  render: Template.bind({}),
  name: "Images",
  args: { type: "image" },
}

export const Audio = {
  render: Template.bind({}),
  name: "Audio",
  args: { type: "audio" },
}

export const Video = {
  render: Template.bind({}),
  name: "Video",
  args: { type: "video" },
}

export const Model_3D = {
  render: Template.bind({}),
  name: "3D models",
  args: { type: "model-3d" },
}
