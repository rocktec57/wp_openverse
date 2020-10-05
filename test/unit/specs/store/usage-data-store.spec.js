import store from '~/store-modules/usage-data-store'

describe('Usage Data Store Store', () => {
  describe('actions', () => {
    let usageDataServiceMock = null
    const data = { foo: 'bar' }

    beforeEach(() => {
      usageDataServiceMock = {
        sendSearchQueryEvent: jest.fn(() => Promise.resolve()),
        sendResultClickedEvent: jest.fn(() => Promise.resolve()),
        sendDetailPageEvent: jest.fn(() => Promise.resolve()),
        sendSearchRatingEvent: jest.fn(() => Promise.resolve()),
      }
    })

    it('SEND_SEARCH_QUERY_EVENT sends search query event', () => {
      store.actions(usageDataServiceMock).SEND_SEARCH_QUERY_EVENT({}, data)

      expect(usageDataServiceMock.sendSearchQueryEvent).toHaveBeenCalledWith(
        data
      )
    })

    it('SEND_RESULT_CLICKED_EVENT sends result clicked event', () => {
      store.actions(usageDataServiceMock).SEND_RESULT_CLICKED_EVENT({}, data)

      expect(usageDataServiceMock.sendResultClickedEvent).toHaveBeenCalledWith(
        data
      )
    })

    it('SEND_DETAIL_PAGE_EVENT sends detail page event', () => {
      store.actions(usageDataServiceMock).SEND_DETAIL_PAGE_EVENT({}, data)

      expect(usageDataServiceMock.sendDetailPageEvent).toHaveBeenCalledWith(
        data
      )
    })

    it('SEND_SEARCH_RATING_EVENT sends result clicked event', () => {
      store.actions(usageDataServiceMock).SEND_SEARCH_RATING_EVENT({}, data)

      expect(usageDataServiceMock.sendSearchRatingEvent).toHaveBeenCalledWith(
        data
      )
    })
  })
})
