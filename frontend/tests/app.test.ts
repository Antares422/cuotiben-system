import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import App from '../src/App.vue'
import { routes } from '../src/router'
import { installFakeBackend } from './helpers/fake-backend'

async function mountAppAt(path: string) {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push(path)
  await router.isReady()
  const wrapper = mount(App, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

afterEach(() => vi.unstubAllGlobals())

describe('App', () => {
  it('offers navigation to the upload, mistake list and manage pages', async () => {
    installFakeBackend({
      'GET /api/mistakes': () => ({ data: { items: [], total: 0, page: 1, page_size: 20, overall_total: 0 } }),
      'GET /api/subjects': () => ({ data: { items: [] } }),
      'GET /api/tags': () => ({ data: { items: [] } }),
    })
    const wrapper = await mountAppAt('/mistakes')

    const hrefs = wrapper.findAll('nav a').map((a) => a.attributes('href'))

    expect(hrefs).toEqual(['/', '/mistakes', '/manage'])
    expect(wrapper.find('nav a[aria-current="page"]').text()).toBe('错题本')
  })

  it('keeps the mistake list tab highlighted on a mistake detail page', async () => {
    installFakeBackend({
      'GET /api/mistakes/7': () => ({
        data: {
          id: 7,
          content: '题',
          answer: null,
          error_reason: null,
          subject: { id: 1, name: '语文' },
          tags: [],
          image_id: null,
          image_url: null,
          mastery_level: 1,
          mastered_at: null,
          created_at: '2026-10-03T08:30:00Z',
          updated_at: '2026-10-03T08:30:00Z',
        },
      }),
    })
    const wrapper = await mountAppAt('/mistakes/7')

    expect(wrapper.findAll('nav a[aria-current="page"]').map((a) => a.text())).toEqual(['错题本'])
  })

  it('highlights only the upload tab on the upload page', async () => {
    installFakeBackend({ 'GET /api/subjects': () => ({ data: { items: [] } }) })
    const wrapper = await mountAppAt('/')

    expect(wrapper.findAll('nav a[aria-current="page"]').map((a) => a.text())).toEqual(['录入'])
  })

  it('highlights only the manage tab on the manage page', async () => {
    installFakeBackend({
      'GET /api/subjects': () => ({ data: { items: [] } }),
      'GET /api/tags': () => ({ data: { items: [] } }),
    })
    const wrapper = await mountAppAt('/manage')

    expect(wrapper.findAll('nav a[aria-current="page"]').map((a) => a.text())).toEqual(['管理'])
  })
})
