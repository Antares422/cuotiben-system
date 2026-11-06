import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { routes } from '../src/router'
import ManageView from '../src/views/ManageView.vue'
import { installFakeBackend } from './helpers/fake-backend'

const SUBJECTS = {
  items: [
    { id: 1, name: '语文', mistake_count: 2 },
    { id: 2, name: '数学', mistake_count: 0 },
  ],
}
const TAGS = {
  items: [
    { id: 1, name: '函数', mistake_count: 3 },
    { id: 2, name: '几何', mistake_count: 0 },
  ],
}

function backend(extra: Parameters<typeof installFakeBackend>[0] = {}) {
  return installFakeBackend({
    'GET /api/subjects': () => ({ data: SUBJECTS }),
    'GET /api/tags': () => ({ data: TAGS }),
    ...extra,
  })
}

async function mountManage() {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push('/manage')
  await router.isReady()
  const wrapper = mount(ManageView, { global: { plugins: [router] } })
  await flushPromises()
  return wrapper
}

afterEach(() => vi.unstubAllGlobals())

describe('ManageView', () => {
  it('lists subjects and tags with their usage counts', async () => {
    backend()

    const wrapper = await mountManage()

    const subjectRows = wrapper.findAll('[data-testid="subject-row"]')
    expect(subjectRows).toHaveLength(2)
    expect(subjectRows[0].text()).toContain('语文')
    expect(subjectRows[0].text()).toContain('2 题')
    expect(subjectRows[1].text()).toContain('数学')
    expect(subjectRows[1].text()).toContain('0 题')
    const tagRows = wrapper.findAll('[data-testid="tag-row"]')
    expect(tagRows).toHaveLength(2)
    expect(tagRows[0].text()).toContain('函数')
    expect(tagRows[0].text()).toContain('3 题')
    expect(tagRows[1].text()).toContain('几何')
  })

  it('shows an empty hint when there are no tags yet', async () => {
    backend({ 'GET /api/tags': () => ({ data: { items: [] } }) })

    const wrapper = await mountManage()

    expect(wrapper.find('[data-testid="tags-empty"]').text()).toContain('还没有标签')
    expect(wrapper.findAll('[data-testid="tag-row"]')).toHaveLength(0)
  })

  it('creates a subject and shows it right away', async () => {
    const { calls } = backend({
      'POST /api/subjects': () => ({ status: 201, data: { id: 3, name: '物理', mistake_count: 0 } }),
    })

    const wrapper = await mountManage()
    await wrapper.find('[data-testid="new-subject-name"]').setValue('物理')
    await wrapper.find('form.manage-add').trigger('submit')
    await flushPromises()

    const create = calls.find((c) => c.method === 'POST' && c.url === '/api/subjects')
    expect(create?.body).toEqual({ name: '物理' })
    const rows = wrapper.findAll('[data-testid="subject-row"]')
    expect(rows).toHaveLength(3)
    expect(rows[2].text()).toContain('物理')
    expect((wrapper.find('[data-testid="new-subject-name"]').element as HTMLInputElement).value).toBe('')
  })

  it('shows the server message when creating a duplicate or blank subject', async () => {
    backend({ 'POST /api/subjects': () => ({ status: 409, message: '学科已存在' }) })

    const wrapper = await mountManage()
    await wrapper.find('[data-testid="new-subject-name"]').setValue('语文')
    await wrapper.find('form.manage-add').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[data-testid="subject-add-error"]').text()).toBe('学科已存在')
    expect(wrapper.findAll('[data-testid="subject-row"]')).toHaveLength(2)
  })

  it('renames a subject inline and updates the list', async () => {
    const { calls } = backend({
      'PATCH /api/subjects/1': () => ({ data: { id: 1, name: '高中语文', mistake_count: 2 } }),
    })

    const wrapper = await mountManage()
    await wrapper.findAll('[data-testid="subject-rename"]')[0].trigger('click')
    await wrapper.find('[data-testid="rename-input"]').setValue('高中语文')
    await wrapper.find('[data-testid="rename-save"]').trigger('click')
    await flushPromises()

    const rename = calls.find((c) => c.method === 'PATCH' && c.url === '/api/subjects/1')
    expect(rename?.body).toEqual({ name: '高中语文' })
    expect(wrapper.findAll('[data-testid="subject-row"]')[0].text()).toContain('高中语文')
  })

  it('renames a tag inline', async () => {
    const { calls } = backend({
      'PATCH /api/tags/1': () => ({ data: { id: 1, name: '函数与方程', mistake_count: 3 } }),
    })

    const wrapper = await mountManage()
    await wrapper.findAll('[data-testid="tag-rename"]')[0].trigger('click')
    await wrapper.find('[data-testid="rename-input"]').setValue('函数与方程')
    await wrapper.find('[data-testid="rename-save"]').trigger('click')
    await flushPromises()

    const rename = calls.find((c) => c.method === 'PATCH' && c.url === '/api/tags/1')
    expect(rename?.body).toEqual({ name: '函数与方程' })
    expect(wrapper.findAll('[data-testid="tag-row"]')[0].text()).toContain('函数与方程')
  })

  it('keeps the old name and shows the server message when renaming fails', async () => {
    backend({ 'PATCH /api/subjects/1': () => ({ status: 409, message: '学科已存在' }) })

    const wrapper = await mountManage()
    await wrapper.findAll('[data-testid="subject-rename"]')[0].trigger('click')
    await wrapper.find('[data-testid="rename-input"]').setValue('数学')
    await wrapper.find('[data-testid="rename-save"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="subject-error"]').text()).toBe('学科已存在')
    // 失败保持原样：仍停留在编辑态，学科列表未被修改
    expect((wrapper.find('[data-testid="rename-input"]').element as HTMLInputElement).value).toBe('数学')
    expect(wrapper.findAll('[data-testid="subject-row"]')).toHaveLength(2)
  })

  it('deletes an empty subject and removes its row', async () => {
    const { calls } = backend({ 'DELETE /api/subjects/2': () => ({ data: null }) })

    const wrapper = await mountManage()
    await wrapper.findAll('[data-testid="subject-delete"]')[1].trigger('click')
    await flushPromises()

    expect(calls.some((c) => c.method === 'DELETE' && c.url === '/api/subjects/2')).toBe(true)
    const rows = wrapper.findAll('[data-testid="subject-row"]')
    expect(rows).toHaveLength(1)
    expect(rows[0].text()).toContain('语文')
  })

  it('shows the rejection reason in place when deleting a subject in use', async () => {
    backend({
      'DELETE /api/subjects/1': () => ({
        status: 409,
        message: '该学科下还有 2 道错题，请先处理这些错题',
        data: { mistake_count: 2 },
      }),
    })

    const wrapper = await mountManage()
    await wrapper.findAll('[data-testid="subject-delete"]')[0].trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="subject-error"]').text()).toContain('该学科下还有 2 道错题')
    expect(wrapper.findAll('[data-testid="subject-row"]')).toHaveLength(2)
  })

  it('asks for confirmation before deleting a tag, and removes it after success', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const { calls } = backend({ 'DELETE /api/tags/1': () => ({ data: null }) })

    const wrapper = await mountManage()
    await wrapper.findAll('[data-testid="tag-delete"]')[0].trigger('click')
    await flushPromises()

    expect(confirmSpy).toHaveBeenCalled()
    expect(calls.some((c) => c.method === 'DELETE' && c.url === '/api/tags/1')).toBe(true)
    expect(wrapper.findAll('[data-testid="tag-row"]')).toHaveLength(1)
    confirmSpy.mockRestore()
  })

  it('does not delete the tag when the user cancels', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    const { calls } = backend()

    const wrapper = await mountManage()
    await wrapper.findAll('[data-testid="tag-delete"]')[0].trigger('click')
    await flushPromises()

    expect(calls.some((c) => c.method === 'DELETE')).toBe(false)
    expect(wrapper.findAll('[data-testid="tag-row"]')).toHaveLength(2)
    confirmSpy.mockRestore()
  })

  it('shows the error state when the lists cannot be loaded, with a retry', async () => {
    let attempts = 0
    backend({
      'GET /api/subjects': () => {
        attempts += 1
        return attempts === 1
          ? { status: 500, message: '服务器开小差了，请稍后再试' }
          : { data: SUBJECTS }
      },
    })

    const wrapper = await mountManage()
    expect(wrapper.find('[data-testid="error"]').text()).toContain('服务器开小差了，请稍后再试')

    await wrapper.find('[data-testid="retry"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[data-testid="error"]').exists()).toBe(false)
    expect(wrapper.findAll('[data-testid="subject-row"]')).toHaveLength(2)
  })
})
