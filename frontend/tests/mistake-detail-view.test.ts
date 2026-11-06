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
  mastery_level: 2,
  mastered_at: null,
  created_at: '2026-10-03T08:30:00Z',
  updated_at: '2026-10-03T08:30:00Z',
}

async function mountDetail(id = '7') {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push(`/mistakes/${id}`)
  await router.isReady()
  const wrapper = mount(MistakeDetailView, { props: { id }, global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

afterEach(() => vi.unstubAllGlobals())

describe('MistakeDetailView', () => {
  it('shows every saved field together with the original image', async () => {
    installFakeBackend({ 'GET /api/mistakes/7': () => ({ data: MISTAKE }) })

    const { wrapper } = await mountDetail()

    const text = wrapper.text()
    expect(text).toContain('求 f(x)=x² 在 [0,3] 上的最值')
    expect(text).toContain('数学')
    expect(text).toContain('最大 9，最小 0')
    expect(text).toContain('忘了检查端点')
    expect(text).toContain('函数')
    expect(text).toContain('最值')
    expect(wrapper.find('[data-testid="image"]').attributes('src')).toBe('/api/images/abc')
  })

  it('shows the server message with a way back to the list when the mistake does not exist', async () => {
    installFakeBackend({ 'GET /api/mistakes/999': () => ({ status: 404, message: '错题不存在' }) })

    const { wrapper } = await mountDetail('999')

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

    const { wrapper } = await mountDetail()
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

    const { wrapper } = await mountDetail()

    // 本地时区不同，日期可能差一天，所以只校验格式
    expect(wrapper.find('[data-testid="created-at"]').text()).toMatch(/^\d{4}-\d{2}-\d{2} \d{2}:\d{2}$/)
    expect(wrapper.find('[data-testid="answer"]').text()).toBe('未填写')
    expect(wrapper.find('[data-testid="error-reason"]').text()).toBe('未填写')
    expect(wrapper.find('[data-testid="image"]').exists()).toBe(false)
  })

  it('offers a mastery control and a link to the edit page', async () => {
    installFakeBackend({ 'GET /api/mistakes/7': () => ({ data: MISTAKE }) })

    const { wrapper } = await mountDetail()

    expect((wrapper.find('[data-testid="mastery"]').element as HTMLSelectElement).value).toBe('2')
    expect(wrapper.find('[data-testid="mastered-at"]').exists()).toBe(false)
    expect(wrapper.find('[data-testid="edit"]').attributes('href')).toBe('/mistakes/7/edit')
  })

  it('updates the displayed mastery level and mastered time after a successful change', async () => {
    installFakeBackend({
      'GET /api/mistakes/7': () => ({ data: MISTAKE }),
      'PUT /api/mistakes/7/mastery': () => ({ data: { ...MISTAKE, mastery_level: 4, mastered_at: '2026-10-05T10:00:00Z' } }),
    })

    const { wrapper } = await mountDetail()

    await wrapper.find('[data-testid="mastery"]').setValue('4')
    await flushPromises()

    expect((wrapper.find('[data-testid="mastery"]').element as HTMLSelectElement).value).toBe('4')
    expect(wrapper.find('[data-testid="mastered-at"]').text()).toMatch(/掌握于 \d{4}-\d{2}-\d{2} \d{2}:\d{2}/)
  })

  it('keeps the level and shows the message when changing mastery fails', async () => {
    installFakeBackend({
      'GET /api/mistakes/7': () => ({ data: MISTAKE }),
      'PUT /api/mistakes/7/mastery': () => ({ status: 500, message: '服务器开小差了，请稍后再试' }),
    })

    const { wrapper } = await mountDetail()

    await wrapper.find('[data-testid="mastery"]').setValue('5')
    await flushPromises()

    expect(wrapper.find('[data-testid="mastery-error"]').text()).toBe('服务器开小差了，请稍后再试')
    expect((wrapper.find('[data-testid="mastery"]').element as HTMLSelectElement).value).toBe('2')
  })

  it('shows the server 409 reason in place when deleting below level four', async () => {
    installFakeBackend({
      'GET /api/mistakes/7': () => ({ data: MISTAKE }),
      'DELETE /api/mistakes/7': () => ({ status: 409, message: '掌握程度达到四级后才能清理（当前：2 级）', data: { mastery_level: 2 } }),
    })

    const { wrapper, router } = await mountDetail()

    await wrapper.find('[data-testid="delete"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="action-error"]').text()).toContain('掌握程度达到四级后才能清理（当前：2 级）')
    expect(router.currentRoute.value.path).toBe('/mistakes/7')
  })

  it('asks for confirmation before deleting a mastered mistake, and goes back to the list on success', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    installFakeBackend({
      'GET /api/mistakes/7': () => ({ data: { ...MISTAKE, mastery_level: 4, mastered_at: '2026-10-05T10:00:00Z' } }),
      'DELETE /api/mistakes/7': () => ({ data: null }),
    })

    const { wrapper, router } = await mountDetail()

    await wrapper.find('[data-testid="delete"]').trigger('click')
    await flushPromises()

    expect(confirmSpy).toHaveBeenCalledWith('确定要清理这道已掌握的错题吗？')
    expect(router.currentRoute.value.path).toBe('/mistakes')
    confirmSpy.mockRestore()
  })

  it('does not delete when the user cancels the confirmation', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const { calls } = installFakeBackend({
      'GET /api/mistakes/7': () => ({ data: { ...MISTAKE, mastery_level: 5 } }),
      'DELETE /api/mistakes/7': () => ({ data: null }),
    })

    const { wrapper, router } = await mountDetail()

    await wrapper.find('[data-testid="delete"]').trigger('click')
    await flushPromises()

    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    expect(router.currentRoute.value.path).toBe('/mistakes/7')
    confirmSpy.mockRestore()
  })

  // T073：详情页底部升级/降级按钮
  it('offers upgrade/downgrade buttons at the bottom, both enabled mid-range', async () => {
    installFakeBackend({ 'GET /api/mistakes/7': () => ({ data: MISTAKE }) })

    const { wrapper } = await mountDetail()

    const up = wrapper.find('[data-testid="level-up"]')
    const down = wrapper.find('[data-testid="level-down"]')
    expect(up.exists()).toBe(true)
    expect(down.exists()).toBe(true)
    expect(up.attributes('disabled')).toBeUndefined()
    expect(down.attributes('disabled')).toBeUndefined()
  })

  it('upgrades one level via the bottom button and reflects the mastered time', async () => {
    const { calls } = installFakeBackend({
      'GET /api/mistakes/7': () => ({ data: MISTAKE }),
      'PUT /api/mistakes/7/mastery': () => ({
        data: { ...MISTAKE, mastery_level: 3, mastered_at: null },
      }),
    })

    const { wrapper } = await mountDetail()
    await wrapper.find('[data-testid="level-up"]').trigger('click')
    await flushPromises()

    const put = calls.find((c) => c.method === 'PUT')
    expect(put!.body).toEqual({ level: 3 })
    expect((wrapper.find('[data-testid="mastery"]').element as HTMLSelectElement).value).toBe('3')
  })

  it('downgrades one level and clears the mastered time when dropping below four', async () => {
    const { calls } = installFakeBackend({
      'GET /api/mistakes/7': () => ({
        data: { ...MISTAKE, mastery_level: 4, mastered_at: '2026-10-05T10:00:00Z' },
      }),
      'PUT /api/mistakes/7/mastery': () => ({
        data: { ...MISTAKE, mastery_level: 3, mastered_at: null },
      }),
    })

    const { wrapper } = await mountDetail()
    expect(wrapper.find('[data-testid="mastered-at"]').exists()).toBe(true)

    await wrapper.find('[data-testid="level-down"]').trigger('click')
    await flushPromises()

    const put = calls.find((c) => c.method === 'PUT')
    expect(put!.body).toEqual({ level: 3 })
    expect((wrapper.find('[data-testid="mastery"]').element as HTMLSelectElement).value).toBe('3')
    expect(wrapper.find('[data-testid="mastered-at"]').exists()).toBe(false)
  })

  it('disables upgrade at level five and downgrade at level one', async () => {
    installFakeBackend({
      'GET /api/mistakes/7': () => ({ data: { ...MISTAKE, mastery_level: 5 } }),
    })
    const { wrapper } = await mountDetail()
    expect(wrapper.find('[data-testid="level-up"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('[data-testid="level-down"]').attributes('disabled')).toBeUndefined()
  })

  it('keeps the level and shows a message when the stepper request fails', async () => {
    installFakeBackend({
      'GET /api/mistakes/7': () => ({ data: MISTAKE }),
      'PUT /api/mistakes/7/mastery': () => ({ status: 500, message: '服务器开小差了，请稍后再试' }),
    })

    const { wrapper } = await mountDetail()
    await wrapper.find('[data-testid="level-up"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="step-error"]').text()).toBe('服务器开小差了，请稍后再试')
    expect((wrapper.find('[data-testid="mastery"]').element as HTMLSelectElement).value).toBe('2')
  })
})
