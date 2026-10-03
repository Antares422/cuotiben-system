import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { routes } from '../src/router'
import MistakeDetailView from '../src/views/MistakeDetailView.vue'
import { installFakeBackend } from './helpers/fake-backend'

const MISTAKE = {
  id: 7,
  content: '求 f(x)=x² 在 [0,3] 上的最值',
  answer: '最大 9，最小 0',
  error_reason: '忘了检查端点',
  subject: { id: 2, name: '数学' },
  tags: ['函数', '最值'],
  image_id: 'abc',
  image_url: '/api/images/abc',
  mastered: false,
  created_at: '2026-10-03T08:30:00Z',
  updated_at: '2026-10-03T08:30:00Z',
}

async function mountDetail(id = '7') {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push(`/mistakes/${id}`)
  await router.isReady()
  const wrapper = mount(MistakeDetailView, { props: { id }, global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

afterEach(() => vi.unstubAllGlobals())

describe('MistakeDetailView', () => {
  it('shows every saved field together with the original image', async () => {
    installFakeBackend({ 'GET /api/mistakes/7': () => ({ data: MISTAKE }) })

    const wrapper = await mountDetail()

    const text = wrapper.text()
    expect(text).toContain('求 f(x)=x² 在 [0,3] 上的最值')
    expect(text).toContain('数学')
    expect(text).toContain('最大 9，最小 0')
    expect(text).toContain('忘了检查端点')
    expect(text).toContain('函数')
    expect(text).toContain('最值')
    expect(text).toContain('未掌握')
    expect(wrapper.find('[data-testid="image"]').attributes('src')).toBe('/api/images/abc')
  })

  it('shows the server message with a way back to the list when the mistake does not exist', async () => {
    installFakeBackend({ 'GET /api/mistakes/999': () => ({ status: 404, message: '错题不存在' }) })

    const wrapper = await mountDetail('999')

    expect(wrapper.find('[data-testid="error"]').text()).toContain('错题不存在')
    expect(wrapper.find('[data-testid="back"]').attributes('href')).toBe('/mistakes')
  })

  it('shows a loading status until the mistake arrives', async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    installFakeBackend({
      'GET /api/mistakes/7': async () => {
        await gate
        return { data: MISTAKE }
      },
    })

    const wrapper = await mountDetail()
    expect(wrapper.find('[data-testid="loading"]').text()).toBe('加载中…')

    release()
    await flushPromises()
    expect(wrapper.find('[data-testid="loading"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('求 f(x)=x² 在 [0,3] 上的最值')
  })

  it('shows the saved time and placeholders for optional fields that were left empty', async () => {
    installFakeBackend({
      'GET /api/mistakes/7': () => ({
        data: { ...MISTAKE, answer: null, error_reason: null, image_id: null, image_url: null, tags: [] },
      }),
    })

    const wrapper = await mountDetail()

    // 本地时区不同，日期可能差一天，所以只校验格式
    expect(wrapper.find('[data-testid="created-at"]').text()).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
    expect(wrapper.find('[data-testid="answer"]').text()).toBe('未填写')
    expect(wrapper.find('[data-testid="error-reason"]').text()).toBe('未填写')
    expect(wrapper.find('[data-testid="image"]').exists()).toBe(false)
  })
})
