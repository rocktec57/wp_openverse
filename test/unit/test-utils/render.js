/* eslint-disable no-param-reassign */
import Vuex from 'vuex';
import VueI18n from 'vue-i18n';
import { shallowMount, createLocalVue } from '@vue/test-utils';
import sampleStore from '../sampleStore/';

const localVue = createLocalVue();
localVue.use(Vuex);
localVue.use(VueI18n);
const messages = require('@/locales/en.json');

const i18n = new VueI18n({
  locale: 'en',
  fallbackLocale: 'en',
  messages,
});

const render = (Component, options = { localVue, i18n }) => {
  if (!options.store) {
    const store = new Vuex.Store(sampleStore)
    options.store = store
  }

  return shallowMount(Component, options)
}

export default render
