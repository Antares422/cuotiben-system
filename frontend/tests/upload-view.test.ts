import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { routes } from '../src/router'
import UploadView from '../src/views/UploadView.vue'
import { installFakeBackend } from './helpers/fake-backend'

type Routes = Parameters<typeof installFakeBackend>[0]

const SUBJECTS = { items: [{ id: 1, name: '语文' }, { id: 2, name: '数学' }] }

async function mountUpload() {
  const router = createRouter({ history: createMemoryHistory(), routes })
  router.push('/')
  await router.isReady()
  const wrapper = mount(UploadView, { global: { plugins: [router] } })
  await flushPromises()
  return { wrapper, router }
}

function backend(extra: Routes = {}) {
  return installFakeBackend({ 'GET /api/subjects': () => ({ data: SUBJECTS }), ...extra })
}

function uploadOk(ocr: object) {
  return () => ({
    status: 201,
    data: { image_id: 'abc', image_url: '/api/images/abc', ocr },
  })
}

async function choosePhoto(wrapper: Awaited<ReturnType<typeof mountUpload>>['wrapper']) {
  const input = wrapper.find('[data-testid="photo"]')
  const file = new File(['bytes'], 'q.png', { type: 'image/png' })
  Object.defineProperty(input.element, 'files', { value: [file], configurable: true })
  await input.trigger('change')
  await flushPromises()
}

function valueOf(wrapper: Awaited<ReturnType<typeof mountUpload>>['wrapper'], testId: string) {
  return (wrapper.find(`[data-testid="${testId}"]`).element as HTMLInputElement).value
}

afterEach(() => vi.unstubAllGlobals())

describe('UploadView', () => {
  beforeEach(() => {
    installFakeBackend({ 'GET /api/subjects': () => ({ data: SUBJECTS }) })
  })

  it('loads the subjects into the subject select', async () => {
    const { wrapper } = await mountUpload()

    const options = wrapper.findAll('[data-testid="subject"] option').map((o) => o.text())

    expect(options).toEqual(['请选择学科', '语文', '数学'])
  })

  it('uploads the chosen photo and fills the content with the OCR draft', async () => {
    const { calls } = backend({
      'POST /api/uploads': uploadOk({ status: 'ok', text: '识别出的题目', message: null }),
    })
    const { wrapper } = await mountUpload()

    await choosePhoto(wrapper)

    expect(calls.some((c) => c.method === 'POST' && c.url === '/api/uploads')).toBe(true)
    expect(valueOf(wrapper, 'content')).toBe('识别出的题目')
    expect(wrapper.find('[data-testid="preview"]').attributes('src')).toBe('/api/images/abc')
  })

  it('shows a recognizing status while the upload is in flight and hides it afterwards', async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    backend({
      'POST /api/uploads': async () => {
        await gate
        return uploadOk({ status: 'ok', text: '题', message: null })()
      },
    })
    const { wrapper } = await mountUpload()

    await choosePhoto(wrapper)
    expect(wrapper.find('[data-testid="status"]').text()).toBe('正在识别文字…')

    release()
    await flushPromises()
    expect(wrapper.find('[data-testid="status"]').exists()).toBe(false)
  })

  it.each([
    ['failed', '文字识别失败，请手动输入'],
    ['empty', '未识别到文字，请手动输入'],
  ])('shows the OCR message when recognition is %s and keeps the form editable', async (status, message) => {
    backend({ 'POST /api/uploads': uploadOk({ status, text: '', message }) })
    const { wrapper } = await mountUpload()

    await choosePhoto(wrapper)

    expect(wrapper.find('[data-testid="notice"]').text()).toBe(message)
    const content = wrapper.find('[data-testid="content"]')
    expect(content.attributes('disabled')).toBeUndefined()
    await content.setValue('手动输入的题目')
    expect(valueOf(wrapper, 'content')).toBe('手动输入的题目')
    // 图片已经保存，仍然可以预览
    expect(wrapper.find('[data-testid="preview"]').exists()).toBe(true)
  })

  it('shows the server message when the upload is rejected and keeps the form usable', async () => {
    backend({ 'POST /api/uploads': () => ({ status: 413, message: '图片不能超过 10 MB' }) })
    const { wrapper } = await mountUpload()

    await choosePhoto(wrapper)

    expect(wrapper.find('[data-testid="error"]').text()).toBe('图片不能超过 10 MB')
    expect(wrapper.find('[data-testid="status"]').exists()).toBe(false)
    await wrapper.find('[data-testid="content"]').setValue('手动输入')
    expect(valueOf(wrapper, 'content')).toBe('手动输入')
  })

  it('blocks saving when the content is blank and does not call the server', async () => {
    const { calls } = backend()
    const { wrapper } = await mountUpload()
    await wrapper.find('[data-testid="subject"]').setValue(1)
    await wrapper.find('[data-testid="content"]').setValue('   ')

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[data-testid="error"]').text()).toBe('题目内容不能为空')
    expect(calls.some((c) => c.url === '/api/mistakes')).toBe(false)
  })

  it('blocks saving when no subject is chosen and does not call the server', async () => {
    const { calls } = backend()
    const { wrapper } = await mountUpload()
    await wrapper.find('[data-testid="content"]').setValue('一道题')

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[data-testid="error"]').text()).toBe('请选择学科')
    expect(calls.some((c) => c.url === '/api/mistakes')).toBe(false)
  })

  it('saves the mistake with every field and goes to its detail page', async () => {
    const { calls } = backend({
      'POST /api/uploads': uploadOk({ status: 'ok', text: '识别出的题目', message: null }),
      'POST /api/mistakes': () => ({ status: 201, data: { id: 42 } }),
    })
    const { wrapper, router } = await mountUpload()
    await choosePhoto(wrapper)
    await wrapper.find('[data-testid="subject"]').setValue(2)
    await wrapper.find('[data-testid="answer"]').setValue('B')
    await wrapper.find('[data-testid="error-reason"]').setValue('粗心')
    await wrapper.find('[data-testid="tags"]').setValue('函数，单调性  最值,函数、')

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    const save = calls.find((c) => c.method === 'POST' && c.url === '/api/mistakes')
    expect(save?.body).toEqual({
      content: '识别出的题目',
      subject_id: 2,
      answer: 'B',
      error_reason: '粗心',
      tags: ['函数', '单调性', '最值'],
      image_id: 'abc',
    })
    expect(router.currentRoute.value.fullPath).toBe('/mistakes/42')
  })

  it('shows the server message when saving fails and stays on the form', async () => {
    backend({ 'POST /api/mistakes': () => ({ status: 422, message: '学科不存在' }) })
    const { wrapper, router } = await mountUpload()
    await wrapper.find('[data-testid="subject"]').setValue(1)
    await wrapper.find('[data-testid="content"]').setValue('一道题')

    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[data-testid="error"]').text()).toBe('学科不存在')
    expect(router.currentRoute.value.fullPath).toBe('/')
    expect(wrapper.find('[data-testid="save"]').attributes('disabled')).toBeUndefined()
  })

  it('disables the save button and ignores a second submit while saving', async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    const { calls } = backend({
      'POST /api/mistakes': async () => {
        await gate
        return { status: 201, data: { id: 5 } }
      },
    })
    const { wrapper, router } = await mountUpload()
    await wrapper.find('[data-testid="subject"]').setValue(1)
    await wrapper.find('[data-testid="content"]').setValue('一道题')

    await wrapper.find('form').trigger('submit')
    await wrapper.find('form').trigger('submit')

    expect(wrapper.find('[data-testid="save"]').attributes('disabled')).toBeDefined()
    expect(calls.filter((c) => c.method === 'POST' && c.url === '/api/mistakes')).toHaveLength(1)

    release()
    await flushPromises()
    expect(router.currentRoute.value.fullPath).toBe('/mistakes/5')
  })

  it('marks the current step: take photo, then review, then save', async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    backend({
      'POST /api/uploads': uploadOk({ status: 'ok', text: '识别出的题目', message: null }),
      'POST /api/mistakes': async () => {
        await gate
        return { status: 201, data: { id: 1 } }
      },
    })
    const { wrapper } = await mountUpload()
    const current = () => wrapper.find('[data-testid="steps"] [aria-current="step"]').text()

    expect(current()).toBe('拍照')

    await choosePhoto(wrapper)
    expect(current()).toBe('核对')

    await wrapper.find('[data-testid="subject"]').setValue(1)
    await wrapper.find('form').trigger('submit')
    expect(current()).toBe('保存')

    release()
    await flushPromises()
  })

  it('moves to the review step when the user types the question by hand', async () => {
    backend()
    const { wrapper } = await mountUpload()

    await wrapper.find('[data-testid="content"]').setValue('手动输入的题目')

    expect(wrapper.find('[data-testid="steps"] [aria-current="step"]').text()).toBe('核对')
  })

  it('tells the user when the subject list cannot be loaded instead of failing silently', async () => {
    backend({ 'GET /api/subjects': () => ({ status: 500, message: '服务器开小差了，请稍后再试' }) })

    const { wrapper } = await mountUpload()

    expect(wrapper.find('[data-testid="error"]').text()).toBe('服务器开小差了，请稍后再试')
    // 页面其余部分仍然可用
    expect(wrapper.find('[data-testid="content"]').exists()).toBe(true)
  })
})
