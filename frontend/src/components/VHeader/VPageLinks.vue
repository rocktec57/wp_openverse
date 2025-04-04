<script setup lang="ts">
import { computed } from "vue"

import usePages from "~/composables/use-pages"

import VItemGroup from "~/components/VItemGroup/VItemGroup.vue"
import VItem from "~/components/VItemGroup/VItem.vue"
import VIcon from "~/components/VIcon/VIcon.vue"
import VLink from "~/components/VLink.vue"

const props = withDefaults(
  defineProps<{
    /**
     * In `dark` mode (in the modal), the links are white and the background is dark charcoal.
     * In `light` mode, the links are dark charcoal and the background is transparent.
     */
    mode?: "light" | "dark"
    /**
     * Pass the tailwind classes to style the nav links.
     */
    navLinkClasses?: string
    variant?: "links" | "itemgroup"
    isInModal?: boolean
  }>(),
  {
    mode: "light",
    navLinkClasses: "",
    variant: "links",
    isInModal: false,
  }
)
const emit = defineEmits<{
  close: []
}>()

const { all: allPages, current: currentPage } = usePages()

// The modal isn't closed if we click on the current page link,
// so we need to close it manually.
const onClick = () => emit("close")

const isLinkExternal = (item: (typeof allPages)[number]) =>
  !item.link.startsWith("/")

const externalIconSize = computed(() => (props.isInModal ? 6 : 4))
</script>

<template>
  <VItemGroup
    v-if="variant === 'itemgroup'"
    class="my-2 min-w-50 gap-y-2"
    :bordered="false"
    :show-check="false"
  >
    <VItem
      v-for="(page, i) of allPages"
      :key="i"
      as="VLink"
      :is-first="i === 0"
      :selected="currentPage === page.id"
      :href="page.link"
      class="w-full"
      @click="onClick"
    >
      <div class="flex w-full flex-row justify-between">
        <span class="pe-2">{{ $t(page.name) }}</span>
        <VIcon
          v-if="isLinkExternal(page)"
          name="external-link"
          :size="4"
          class="self-center"
          rtl-flip
        />
      </div>
    </VItem>
  </VItemGroup>
  <ul v-else>
    <li v-for="page in allPages" :key="page.id">
      <VLink
        class="flex flex-row rounded-sm hover:underline disabled:text-disabled"
        :class="[
          { 'font-semibold': currentPage === page.id },
          { 'text-default': mode === 'light' },
          navLinkClasses,
        ]"
        :href="page.link"
        @click="onClick"
        >{{ $t(page.name)
        }}<VIcon
          v-if="isLinkExternal(page)"
          name="external-link"
          :size="externalIconSize"
          class="ms-2 self-center"
          rtl-flip
      /></VLink>
    </li>
  </ul>
</template>
