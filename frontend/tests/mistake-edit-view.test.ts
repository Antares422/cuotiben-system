import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { routes } from '../src/router'
import MistakeEditView from '../src/views/MistakeEditView.vue'
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

const SUBJECTS = { items: [{ id: 1, name: '语文' }, { id: 2, name: '数学' }] }

async function mountEdit(id = '7') {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push(`/mistakes/${id}/edit`)
  await router.isReady()
  const wrapper = mount(MistakeEditView, { props: { id }, global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

function valueOf(wrapper: Awaited<ReturnType<typeof mountEdit>>['wrapper'], testId: string) {
  return (wrapper.find(`[data-testid="${testId}"]`).element as HTMLInputElement).value
}

afterEach(() => vi.unstubAllGlobals())

describe('MistakeEditView', () => {
  it('loads the original values into the form', async () => {
    installFakeBackend({
      'GET /api/mistakes/7': () => ({ data: MISTAKE }),
      'GET /api/subjects': () => ({ data: SUBJECTS }),
    })

    const { wrapper } = await mountEdit()

    expect(wrapper.find('[data-testid="loading"]').exists()).toBe(false)
    expect(valueOf(wrapper, 'content')).toBe('求 f(x)=x² 在 [0,3] 上的最值')
    expect(valueOf(wrapper, 'subject')).toBe('2')
    expect(valueOf(wrapper, 'answer')).toBe('最大 9，最小 0')
    expect(valueOf(wrapper, 'error-reason')).toBe('忘了检查端点')
    expect(valueOf(wrapper, 'tags')).toBe('函数，最值')
  })

  it('shows the error when the mistake cannot be loaded', async () => {
    installFakeBackend({
      'GET /api/mistakes/999': () => ({ status: 404, message: '错题不存在' }),
      'GET /api/subjects': () => ({ data: SUBJECTS }),
    })

    const { wrapper } = await mountEdit('999')

    expect(wrapper.find('[data-testid="error"]').text()).toContain('错题不存在')
    expect(wrapper.find('form').exists()).toBe(false)
  })

  it('saves the changes with PATCH and goes back to the detail page', async () => {
    const { calls } = installFakeBackend({
      'GET /api/mistakes/7': () => ({ data: MISTAKE }),
      'GET /api/subjects': () => ({ data: SUBJECTS }),
      'PATCH /api/mistakes/7': () => ({ data: { ...MISTAKE, content: '改后的题目' } }),
    })

    const { wrapper, router } = await mountEdit()
    await wrapper.find('[data-testid="content"]').setValue('改后的题目  ')
    await wrapper.find('[data-testid="subject"]').setValue(1)
    await wrapper.find('[data-testid="answer"]').setValue('')
    await wrapper.find('[data-testid="tags"]').setValue('函数，导数、')

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    const save = calls.find((c) => c.method === 'PATCH')
    expect(save?.url).toBe('/api/mistakes/7')
    expect(save?.body).toEqual({
      content: '改后的题目',
      subject_id: 1,
      answer: null,
      error_reason: '忘了检查端点',
      tags: ['函数', '导数'],
      image_id: 'abc',
    })
    expect(router.currentRoute.value.fullPath).toBe('/mistakes/7')
    // 详情接口未被重新拉取，更新内容以 PATCH 响应为准
  })

  it('blocks saving when the content is blank and does not call the server', async () => {
    const { calls } = installFakeBackend({
      'GET /api/mistakes/7': () => ({ data: MISTAKE }),
      'GET /api/subjects': () => ({ data: SUBJECTS }),
    })

    const { wrapper } = await mountEdit()
    await wrapper.find('[data-testid="content"]').setValue('   ')

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[data-testid="error"]').text()).toBe('题目内容不能为空')
    expect(calls.some((c) => c.method === 'PATCH')).toBe(false)
  })

  it('shows the server message when saving fails and keeps the filled form', async () => {
    installFakeBackend({
      'GET /api/mistakes/7': () => ({ data: MISTAKE }),
      'GET /api/subjects': () => ({ data: SUBJECTS }),
      'PATCH /api/mistakes/7': () => ({ status: 422, message: '学科不存在' }),
    })

    const { wrapper, router } = await mountEdit()
    await wrapper.find('[data-testid="content"]').setValue('改后的题目')

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[data-testid="error"]').text()).toBe('学科不存在')
    expect(valueOf(wrapper, 'content')).toBe('改后的题目')
    expect(router.currentRoute.value.fullPath).toBe('/mistakes/7/edit')
  })

  it('creates a new subject inline and keeps the rest of the form intact', async () => {
    const { calls } = installFakeBackend({
      'GET /api/mistakes/7': () => ({ data: MISTAKE }),
      'GET /api/subjects': () => ({ data: SUBJECTS }),
      'POST /api/subjects': () => ({ status: 201, data: { id: 3, name: '物理', mistake_count: 0 } }),
    })

    const { wrapper } = await mountEdit()
    await wrapper.find('[data-testid="content"]').setValue('手动改过的题目')
    await wrapper.find('[data-testid="subject"]').setValue('__new__')
    await wrapper.find('[data-testid="new-subject"]').setValue('物理')
    await wrapper.find('[data-testid="new-subject-confirm"]').trigger('click')
    await flushPromises()

    const create = calls.find((c) => c.method === 'POST' && c.url === '/api/subjects')
    expect(create?.body).toEqual({ name: '物理' })
    expect(valueOf(wrapper, 'subject')).toBe('3')
    expect(valueOf(wrapper, 'content')).toBe('手动改过的题目')
  })

  it('shows the server message when the new subject name is rejected', async () => {
    installFakeBackend({
      'GET /api/mistakes/7': () => ({ data: MISTAKE }),
      'GET /api/subjects': () => ({ data: SUBJECTS }),
      'POST /api/subjects': () => ({ status: 409, message: '学科已存在' }),
    })

    const { wrapper } = await mountEdit()
    await wrapper.find('[data-testid="subject"]').setValue('__new__')
    await wrapper.find('[data-testid="new-subject"]').setValue('数学')
    await wrapper.find('[data-testid="new-subject-confirm"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="new-subject-error"]').text()).toBe('学科已存在')
    // 原学科保持选中
    expect(valueOf(wrapper, 'subject')).toBe('2')
  })
})
