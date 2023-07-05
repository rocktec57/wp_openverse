import type {
  MediaType,
  SearchType,
  SupportedSearchType,
} from "~/constants/media"
import type { ReportReason } from "~/constants/content-report"
import type { NonMatureFilterCategory } from "~/constants/filters"

export type AudioInteraction = "play" | "pause" | "seek"
export type AudioInteractionData = Exclude<
  Events["AUDIO_INTERACTION"],
  "component"
>
export type AudioComponent =
  | "VRelatedAudio"
  | "VGlobalAudioTrack"
  | "AudioSearch"
  | "AudioDetailPage"
  | "VAllResultsGrid"
/**
 * Compound type of all custom events sent from the site; Index with `EventName`
 * to get the type of the payload for a specific event.
 *
 * Conventions:
 * - Names should be in SCREAMING_SNAKE_CASE.
 * - Names should be imperative for events associated with user action.
 * - Names should be in past tense for events not associated with user action.
 * - Documentation must be the step to emit the event, followed by a line break.
 * - Questions that are answered by the event must be listed as bullet points.
 */
export type Events = {
  /**
   * Description: A search performed by the user
   * Questions:
   *   - How many searches do we serve per day/month/year?
   *   - What are the most popular searches in Openverse?
   *   - Which media types are the most popular?
   *   - Do most users search from the homepage, or internal searchbar?
   */
  SUBMIT_SEARCH: {
    /** The media type being searched */
    searchType: SearchType
    /** The search term */
    query: string
  }
  /**
   * Description: The user clicks on one of the images in the gallery on the homepage.
   * Questions:
   * - Do users know homepage images are links?
   * - Do users find these images interesting?
   * - Which set is most interesting for the users?
   */
  CLICK_HOME_GALLERY_IMAGE: {
    /** the set to which the image belongs */
    set: string
    /** The unique ID of the media */
    id: string
  }
  /**
   * Description: The user opens the menu which lists pages.
   * Questions:
   *   - How often is this menu used?
   *   - Is this menu visible enough?
   */
  OPEN_PAGES_MENU: Record<string, never>
  /**
   * Description: The user right clicks a single image result, most likely to download it.
   * Questions:
   *   - Do users right-click images often? Does this suggest downloading them directly,
   *     when not paired with a `GET_MEDIA` event?
   */
  RIGHT_CLICK_IMAGE: {
    id: string
  }
  /**
   * Click on the 'back to search' link on a single result
   *
   * - Are these links used much? Are they necessary?
   */
  BACK_TO_SEARCH: {
    /** The unique ID of the media */
    id: string
    /** The content type being searched (can include All content) */
    searchType: SearchType
  }
  /**
   * Description: Whenever the user scrolls to the end of the results page.
   * Useful to evaluate how often users load more results or click
   * on the external sources dropdown.
   *
   * This event is mainly used as part of a funnel leading to a
   * `LOAD_MORE` or `VIEW_EXTERNAL_SOURCES` event.
   *
   * Questions:
   *   - Do users use external search after reaching the result end?
   *   - Do users find a result before reaching the end of the results?
   */
  REACH_RESULT_END: {
    /** The media type being searched */
    searchType: SupportedSearchType
    /** The search term */
    query: string
    /** The current page of results the user is on. */
    resultPage: number
  }
  /**
   * Description: The user clicks the CTA button to the external source to use the image
   * Questions:
   *   - How often do users go to the source after viewing a result?
   */
  GET_MEDIA: {
    /** the unique ID of the media */
    id: string
    /** The slug (not the prettified name) of the provider */
    provider: string
    /** The media type being searched */
    mediaType: MediaType
  }
  /**
   * Description: The user clicks one of the buttons to copy the media attribution
   * Questions:
   *   - How often do users use our attribution tool?
   *   - Which format is the most popular?
   */
  COPY_ATTRIBUTION: {
    /** The unique ID of the media */
    id: string
    /** The format of the copied attribution */
    format: "plain" | "rich" | "html"
    /** The media type being searched */
    mediaType: MediaType
  }
  /**
   * Description: The user reports a piece of media through our form
   * Questions:
   *   - How often do we get reports?
   *   - Which types of reports are more common?
   *   - Do we see an uptick in reports when a certain provider
   *     is added/updated/refreshed?
   * Note: Because the DMCA report is sent via a Google form, we send
   * this event when the form is opened, and not when the report form
   * is actually sent.
   */
  REPORT_MEDIA: {
    /** the unique ID of the media */
    id: string
    /** the slug (not the prettified name) of the provider */
    provider: string
    /** the media type being searched */
    mediaType: MediaType
    /** the reason for the report */
    reason: ReportReason
  }
  /**
   * Description: When the user chooses an external source from the dropdown of external sources
   * Questions:
   *   - Which external sources are most popular? This could drive inclusion in Openverse.
   *   - Are certain media types more popular externally?
   */
  SELECT_EXTERNAL_SOURCE: {
    /** The name of the external source */
    name: string
    /** The media type being searched */
    mediaType: MediaType
    /** The search term */
    query: string
    /** The component that triggered the event */
    component: "VNoResults" | "VExternalSourceList"
  }
  /**
   * Description: Whenever a user changes the content type
   * Questions:
   *   - Which content types are most popular?
   *   - Is there interest in the non-supported content types?
   *   - Do users switch content types? Where in their journeys?
   */
  CHANGE_CONTENT_TYPE: {
    /** The previously-set media type */
    previous: SearchType
    /** The new media type */
    next: SearchType
    /** The name of the Vue component used to switch content types. */
    component: string
  }
  /**
   * Description: The visibility of the filter sidebar on desktop is toggled
   * Questions:
   *   - Do a majority users prefer the sidebar visible or hidden?
   */
  TOGGLE_FILTER_SIDEBAR: {
    /** The media type being searched */
    searchType: SearchType
    /** The state of the filter sidebar after the user interaction. */
    toState: "opened" | "closed"
  }
  /**
   * Description: The user clicks to a link outside of Openverse.
   * Questions:
   *   - What types of external content do users seek?
   *   - Are there external resources we should make more visible?
   *   - Is there content we might want to add to Openverse directly?
   */
  EXTERNAL_LINK_CLICK: {
    /** The url of the external link */
    url: string
  }
  /**
   * Description: The user visits a creator's link in the single result UI
   * Questions:
   *   - Are creator links clicked much? Does Openverse increase visibility
   *     of included creator's profiles?
   */
  VISIT_CREATOR_LINK: {
    /** The unique ID of the media */
    id: string
    /** The permalink to the creator's profile */
    url: string
  }
  /**
   * Description: The user visits a CC license description page on CC.org
   * Questions:
   *   - How often are external licenses viewed?
   */
  VISIT_LICENSE_PAGE: {
    /** The slug of the license the user clicked on */
    license: string
  }
  /**
   * Description: Whenever the user selects a result from the search results page.
   * Questions:
   *   - Which results are most popular for given searches?
   *   - How often do searches lead to clicking a result?
   *   - Are there popular searches that do not result in result selection?
   */
  SELECT_SEARCH_RESULT: {
    /** The unique ID of the media */
    id: string
    /** If the result is a related result, provide the ID of the 'original' result */
    relatedTo: string | null
    /** The media type being searched */
    mediaType: SearchType
    /** The slug (not the prettified name) of the provider */
    provider: string
    /** The search term */
    query: string
  }
  /**
   * Description: When a user opens the external sources popover.
   * Questions:
   *   - How often do users use this feature?
   *   - Under what conditions to users use this feature? No results?
   *     Many results, but none they actually select?
   */
  VIEW_EXTERNAL_SOURCES: {
    /** The media type being searched */
    searchType: SearchType
    /** The search term */
    query: string
    /** Pagination depth */
    resultPage: number
  }
  /*
   * Description: Whenever the user clicks the load more button
   * Questions:
   *   - On what page do users typically find a result?
   *   - How often and how many pages of results do users load?
   *   - Can we experiment with the types of results / result rankings
   *     on certain pages, pages that users don't usually choose a result
   *     from anyway?
   */
  LOAD_MORE_RESULTS: {
    /** The media type being searched */
    searchType: SearchType
    /** The search term */
    query: string
    /** The current page of results the user is on,
     * *before* loading more results.. */
    resultPage: number
  }
  /*
   * Description: Whenever the user sets a filter. Filter category and key are the values used in code, not the user-facing filter labels.
   * Questions:
   *  - Do most users filter their searches?
   *  - What % of users use filtering?
   *  - Which filters are most popular? Least popular?
   *  - Are any filters so commonly applied they should become defaults?
   */
  APPLY_FILTER: {
    /** The filter category, e.g. `license`  */
    category: NonMatureFilterCategory
    /** The filter key, e.g. `by` */
    key: string
    /** Whether the filter is checked or unchecked */
    checked: boolean
    /** The media type being searched, can include All content */
    searchType: SearchType
    /** The search term */
    query: string
  }

  /** Description: The user plays, pauses, or seeks an audio track.
   *
   * Questions:
   *   - Do users interact with media frequently?
   *   - Is it more common to playback audio on single results
   *     or search pages?
   *   - How many audio plays do we get?
   */
  AUDIO_INTERACTION: {
    /** The unique ID of the media */
    id: string
    event: AudioInteraction
    /** The slug (not the prettified name) of the provider */
    provider: string
    /** The name of the Vue component used on the interaction, e.g. the global or main player. */
    component: AudioComponent
  }
}

/**
 * the name of a custom event sent from the site
 */
export type EventName = keyof Events
