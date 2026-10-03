import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import App from '../src/App.vue'
import { routes } from '../src/router'

describe('App', () => {
  it('offers navigation to the upload page and the mistake list', async () => {
    const router = createRouter({ history: createMemoryHistory(), routes })
    router.push('/mistakes')
    await router.isReady()
    const wrapper = mount(App, { global: { plugins: [router] } })
    await flushPromises()

    const hrefs = wrapper.findAll('nav a').map((a) => a.attributes('href'))

    expect(hrefs).toEqual(['/', '/mistakes'])
    expect(wrapper.find('nav a[aria-current="page"]').text()).toBe('错题本')
  })
})
