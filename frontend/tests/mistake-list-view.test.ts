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
    mastery_level: 1,
    mastered_at: null,
    created_at: '2026-10-03T08:30:00Z',
    updated_at: '2026-10-03T08:30:00Z',
    ...extra,
  }
}

function page(items: object[], total = items.length, pageNo = 1, overallTotal = total) {
  return { data: { items, total, page: pageNo, page_size: 20, overall_total: overallTotal } }
}

const META = {
  'GET /api/subjects': () => ({ data: { items: [{ id: 1, name: '语文' }, { id: 2, name: '数学' }] } }),
  'GET /api/tags': () => ({ data: { items: [{ id: 1, name: '函数', mistake_count: 1 }] } }),
}

async function mountList(path = '/mistakes') {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push(path)
  await router.isReady()
  const wrapper = mount(MistakeListView, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

function mistakeCalls(calls: { url: string }[]) {
  return calls.filter((c) => c.url.startsWith('/api/mistakes'))
}

function lastUrl(calls: { url: string }[]) {
  return new URL(mistakeCalls(calls).at(-1)!.url, 'http://test')
}

afterEach(() => vi.unstubAllGlobals())

describe('MistakeListView', () => {
  it('shows each mistake with subject, tags and mastery level, linking to its detail page', async () => {
    installFakeBackend({
      ...META,
      'GET /api/mistakes': () =>
        page([
          mistake(2, { tags: ['函数', '最值'], mastery_level: 4, mastered_at: '2026-10-05T10:00:00Z' }),
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
    expect(items[0].find('[data-testid="mastered-at"]').text()).toContain('掌握于')
    expect((items[0].find('[data-testid="mastery"]').element as HTMLSelectElement).value).toBe('4')
    expect(items[1].text()).toContain('英语')
    expect((items[1].find('[data-testid="mastery"]').element as HTMLSelectElement).value).toBe('1')
    expect(items[1].find('[data-testid="mastered-at"]').exists()).toBe(false)
    expect(items[0].find('a').attributes('href')).toBe('/mistakes/2')
  })

  it('shows an empty state that links to the upload page when there are no mistakes', async () => {
    installFakeBackend({ ...META, 'GET /api/mistakes': () => page([]) })

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
      ...META,
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
      ...META,
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
      ...META,
      'GET /api/mistakes': ({ url }) =>
        url.includes('page=2') ? page([mistake(1)], 3, 2) : page([mistake(3), mistake(2)], 3, 1),
    })

    const { wrapper } = await mountList()
    expect(wrapper.findAll('[data-testid="item"]')).toHaveLength(2)

    await wrapper.find('[data-testid="more"]').trigger('click')
    await flushPromises()

    expect(mistakeCalls(calls).map((c) => c.url)).toEqual([
      '/api/mistakes?page=1&page_size=20',
      '/api/mistakes?page=2&page_size=20',
    ])
    const ids = wrapper.findAll('[data-testid="item"] a').map((a) => a.attributes('href'))
    expect(ids).toEqual(['/mistakes/3', '/mistakes/2', '/mistakes/1'])
    expect(wrapper.find('[data-testid="more"]').exists()).toBe(false)
  })

  it('keeps the loaded items and shows the error when loading more fails', async () => {
    installFakeBackend({
      ...META,
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
    installFakeBackend({ ...META, 'GET /api/mistakes': () => page([mistake(2), mistake(1)], 35) })

    const { wrapper } = await mountList()

    expect(wrapper.find('[data-testid="count"]').text()).toBe('共 35 道错题')
  })

  it('shows no count when there is nothing yet', async () => {
    installFakeBackend({ ...META, 'GET /api/mistakes': () => page([]) })

    const { wrapper } = await mountList()

    expect(wrapper.find('[data-testid="count"]').exists()).toBe(false)
  })

  it('requests with the new filters, resets to the first page and updates the address', async () => {
    const { calls } = installFakeBackend({
      ...META,
      'GET /api/mistakes': () => page([mistake(1)]),
    })
    const { wrapper, router } = await mountList()
    expect(mistakeCalls(calls)).toHaveLength(1)

    await wrapper.find('[data-testid="filter-subject"]').setValue('2')
    await flushPromises()

    const url = lastUrl(calls)
    expect(url.searchParams.get('subject_id')).toBe('2')
    expect(url.searchParams.get('page')).toBe('1')
    expect(mistakeCalls(calls)).toHaveLength(2)
    expect(router.currentRoute.value.query).toEqual({ subject_id: '2' })
  })

  it('sends repeated tag parameters for each chosen tag', async () => {
    const { calls } = installFakeBackend({ ...META, 'GET /api/mistakes': () => page([]) })
    const { wrapper } = await mountList()

    await wrapper.findAll('[data-testid="filter-tag"]')[0].trigger('click')
    await flushPromises()

    expect(lastUrl(calls).searchParams.getAll('tag')).toEqual(['函数'])
  })

  it('restores the filters from the address when the page loads', async () => {
    const { calls } = installFakeBackend({ ...META, 'GET /api/mistakes': () => page([]) })

    const { wrapper } = await mountList('/mistakes?tag=%E5%87%BD%E6%95%B0&mastery_min=2&q=abc')

    const url = lastUrl(calls)
    expect(url.searchParams.getAll('tag')).toEqual(['函数'])
    expect(url.searchParams.get('mastery_min')).toBe('2')
    expect(url.searchParams.get('q')).toBe('abc')
    expect((wrapper.find('[data-testid="mastery-min"]').element as HTMLSelectElement).value).toBe('2')
    expect((wrapper.find('[data-testid="filter-q"]').element as HTMLInputElement).value).toBe('abc')
  })

  it('shows a dedicated empty state with a clear entry when filters match nothing', async () => {
    const { calls } = installFakeBackend({
      ...META,
      'GET /api/mistakes': ({ url }) => (url.includes('q=') ? page([]) : page([], 0)),
    })

    const { wrapper } = await mountList('/mistakes?q=xyz')

    const noResults = wrapper.find('[data-testid="no-results"]')
    expect(noResults.text()).toContain('没有符合条件的错题')
    expect(wrapper.find('[data-testid="empty"]').exists()).toBe(false)

    await wrapper.find('[data-testid="clear-filters"]').trigger('click')
    await flushPromises()

    expect(lastUrl(calls).searchParams.get('q')).toBeNull()
    expect(wrapper.find('[data-testid="empty"]').text()).toContain('本子还是空的')
  })

  it('drops stale subject and tag filters and tells the user', async () => {
    const { calls } = installFakeBackend({
      ...META,
      'GET /api/mistakes': () => page([]),
    })

    const { wrapper, router } = await mountList('/mistakes?subject_id=99&tag=%E6%97%A7%E6%A0%87%E7%AD%BE')

    expect(wrapper.find('[data-testid="notice"]').text()).toContain('已失效')
    expect(lastUrl(calls).searchParams.get('subject_id')).toBeNull()
    expect(lastUrl(calls).searchParams.getAll('tag')).toEqual([])
    expect(router.currentRoute.value.query).toEqual({})
  })

  it('shows the capacity banner when overall_total exceeds 100 and jumps to level-4 filter', async () => {
    const { calls } = installFakeBackend({
      ...META,
      'GET /api/mistakes': () => page([mistake(1)], 1, 1, 101),
    })

    const { wrapper, router } = await mountList()

    const banner = wrapper.find('[data-testid="capacity"]')
    expect(banner.text()).toContain('已超过 100 题，建议清理已熟练的题')

    await banner.trigger('click')
    await flushPromises()

    expect(lastUrl(calls).searchParams.get('mastery_min')).toBe('4')
    expect(router.currentRoute.value.query.mastery_min).toBe('4')
  })

  it('shows no capacity banner when overall_total stays within 100', async () => {
    installFakeBackend({ ...META, 'GET /api/mistakes': () => page([mistake(1)], 1, 1, 100) })

    const { wrapper } = await mountList()

    expect(wrapper.find('[data-testid="capacity"]').exists()).toBe(false)
  })

  it('removes a mistake right away when its new level leaves the mastery range filter', async () => {
    installFakeBackend({
      ...META,
      'GET /api/mistakes': () => page([mistake(1, { mastery_level: 2 }), mistake(2, { mastery_level: 3 })], 2),
      'PUT /api/mistakes/1/mastery': () => ({ data: mistake(1, { mastery_level: 1 }) }),
    })

    const { wrapper, router } = await mountList('/mistakes?mastery_min=2')
    expect(wrapper.findAll('[data-testid="item"]')).toHaveLength(2)

    await wrapper.findAll('[data-testid="mastery"]')[0].setValue('1')
    await flushPromises()

    expect(wrapper.findAll('[data-testid="item"]')).toHaveLength(1)
    expect(wrapper.find('[data-testid="count"]').text()).toBe('共 1 道错题')
    // 点击控件没有跳转去详情
    expect(router.currentRoute.value.path).toBe('/mistakes')
  })

  it('keeps the mistake and updates it when the new level still matches the filter', async () => {
    installFakeBackend({
      ...META,
      'GET /api/mistakes': () => page([mistake(1, { mastery_level: 2 })], 1),
      'PUT /api/mistakes/1/mastery': () => ({ data: mistake(1, { mastery_level: 3 }) }),
    })

    const { wrapper } = await mountList('/mistakes?mastery_min=2')

    await wrapper.findAll('[data-testid="mastery"]')[0].setValue('3')
    await flushPromises()

    expect(wrapper.findAll('[data-testid="item"]')).toHaveLength(1)
    expect((wrapper.find('[data-testid="mastery"]').element as HTMLSelectElement).value).toBe('3')
  })
})
