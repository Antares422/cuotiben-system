import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { routes } from '../src/router'
import MistakeListView from '../src/views/MistakeListView.vue'
import { installFakeBackend } from './helpers/fake-backend'

function mistake(id: number, extra: object = {}) {
  return {
    id,
    content: `第${id}题内容`,
    answer: null,
    error_reason: null,
    subject: { id: 2, name: '数学' },
    tags: [] as string[],
    image_id: null,
    image_url: null,
    mastered: false,
    created_at: '2026-10-03T08:30:00Z',
    updated_at: '2026-10-03T08:30:00Z',
    ...extra,
  }
}

function page(items: object[], total = items.length, pageNo = 1) {
  return { data: { items, total, page: pageNo, page_size: 20 } }
}

async function mountList() {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push('/mistakes')
  await router.isReady()
  const wrapper = mount(MistakeListView, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

afterEach(() => vi.unstubAllGlobals())

describe('MistakeListView', () => {
  it('shows each mistake with subject, tags and mastery status, linking to its detail page', async () => {
    installFakeBackend({
      'GET /api/mistakes': () =>
        page([
          mistake(2, { tags: ['函数', '最值'], mastered: true }),
          mistake(1, { subject: { id: 3, name: '英语' } }),
        ]),
    })

    const { wrapper } = await mountList()

    const items = wrapper.findAll('[data-testid="item"]')
    expect(items).toHaveLength(2)
    expect(items[0].text()).toContain('第2题内容')
    expect(items[0].text()).toContain('数学')
    expect(items[0].text()).toContain('函数')
    expect(items[0].text()).toContain('最值')
    expect(items[0].text()).toContain('已掌握')
    expect(items[1].text()).toContain('英语')
    expect(items[1].text()).toContain('未掌握')
    expect(items[0].find('a').attributes('href')).toBe('/mistakes/2')
  })

  it('shows an empty state that links to the upload page when there are no mistakes', async () => {
    installFakeBackend({ 'GET /api/mistakes': () => page([]) })

    const { wrapper } = await mountList()

    const empty = wrapper.find('[data-testid="empty"]')
    expect(empty.text()).toContain('本子还是空的')
    expect(empty.find('a').attributes('href')).toBe('/')
    expect(wrapper.find('[data-testid="item"]').exists()).toBe(false)
  })

  it('shows a loading status instead of the empty state while the list is loading', async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    installFakeBackend({
      'GET /api/mistakes': async () => {
        await gate
        return page([mistake(1)])
      },
    })

    const { wrapper } = await mountList()

    expect(wrapper.find('[data-testid="loading"]').text()).toBe('加载中…')
    expect(wrapper.find('[data-testid="empty"]').exists()).toBe(false)

    release()
    await flushPromises()
    expect(wrapper.find('[data-testid="loading"]').exists()).toBe(false)
    expect(wrapper.findAll('[data-testid="item"]')).toHaveLength(1)
  })

  it('shows the error with a retry button, and retrying loads the list', async () => {
    let attempts = 0
    installFakeBackend({
      'GET /api/mistakes': () => {
        attempts += 1
        return attempts === 1 ? { status: 500, message: '服务器开小差了，请稍后再试' } : page([mistake(1)])
      },
    })

    const { wrapper } = await mountList()
    expect(wrapper.find('[data-testid="error"]').text()).toContain('服务器开小差了，请稍后再试')
    expect(wrapper.find('[data-testid="empty"]').exists()).toBe(false)

    await wrapper.find('[data-testid="retry"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="error"]').exists()).toBe(false)
    expect(wrapper.findAll('[data-testid="item"]')).toHaveLength(1)
  })

  it('loads the next page on demand and hides the button once everything is loaded', async () => {
    const { calls } = installFakeBackend({
      'GET /api/mistakes': ({ url }) =>
        url.includes('page=2') ? page([mistake(1)], 3, 2) : page([mistake(3), mistake(2)], 3, 1),
    })

    const { wrapper } = await mountList()
    expect(wrapper.findAll('[data-testid="item"]')).toHaveLength(2)

    await wrapper.find('[data-testid="more"]').trigger('click')
    await flushPromises()

    expect(calls.map((c) => c.url)).toEqual([
      '/api/mistakes?page=1&page_size=20',
      '/api/mistakes?page=2&page_size=20',
    ])
    const ids = wrapper.findAll('[data-testid="item"] a').map((a) => a.attributes('href'))
    expect(ids).toEqual(['/mistakes/3', '/mistakes/2', '/mistakes/1'])
    expect(wrapper.find('[data-testid="more"]').exists()).toBe(false)
  })

  it('keeps the loaded items and shows the error when loading more fails', async () => {
    installFakeBackend({
      'GET /api/mistakes': ({ url }) =>
        url.includes('page=2')
          ? { status: 500, message: '服务器开小差了，请稍后再试' }
          : page([mistake(2), mistake(1)], 3, 1),
    })

    const { wrapper } = await mountList()
    await wrapper.find('[data-testid="more"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="error"]').text()).toContain('服务器开小差了，请稍后再试')
    expect(wrapper.findAll('[data-testid="item"]')).toHaveLength(2)
    expect(wrapper.find('[data-testid="more"]').exists()).toBe(true)
  })

  it('shows the total number of mistakes, not just the loaded ones', async () => {
    installFakeBackend({ 'GET /api/mistakes': () => page([mistake(2), mistake(1)], 35) })

    const { wrapper } = await mountList()

    expect(wrapper.find('[data-testid="count"]').text()).toBe('共 35 道错题')
  })

  it('shows no count when there is nothing yet', async () => {
    installFakeBackend({ 'GET /api/mistakes': () => page([]) })

    const { wrapper } = await mountList()

    expect(wrapper.find('[data-testid="count"]').exists()).toBe(false)
  })
})
