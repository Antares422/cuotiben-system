import { flushPromises, mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import App from '../src/App.vue'
import { routes } from '../src/router'

async function mountAppAt(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push(path)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

describe('App', () => {
  it('offers navigation to the upload page and the mistake list', async () => {
    const wrapper = await mountAppAt('/mistakes')

    const hrefs = wrapper.findAll('nav a').map((a) => a.attributes('href'))

    expect(hrefs).toEqual(['/', '/mistakes'])
    expect(wrapper.find('nav a[aria-current="page"]').text()).toBe('错题本')
  })

  it('keeps the mistake list tab highlighted on a mistake detail page', async () => {
    const wrapper = await mountAppAt('/mistakes/7')

    expect(wrapper.findAll('nav a[aria-current="page"]').map((a) => a.text())).toEqual(['错题本'])
  })

  it('highlights only the upload tab on the upload page', async () => {
    const wrapper = await mountAppAt('/')

    expect(wrapper.findAll('nav a[aria-current="page"]').map((a) => a.text())).toEqual(['录入'])
  })
})
