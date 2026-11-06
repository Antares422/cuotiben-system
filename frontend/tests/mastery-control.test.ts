import { flushPromises, mount } from '@vue/test-utils'
import { afterEach, describe, expect, it, vi } from 'vitest'
import MasteryControl from '../src/components/MasteryControl.vue'
import { installFakeBackend } from './helpers/fake-backend'
import type { Mistake } from '../src/api/types'

function mistake(extra: Partial<Mistake> = {}): Mistake {
  return {
    id: 7,
    content: '题',
    answer: null,
    error_reason: null,
    subject: { id: 2, name: '数学' },
    tags: [],
    image_id: null,
    image_url: null,
    mastery_level: 2,
    mastered_at: null,
    created_at: '2026-10-03T08:30:00Z',
    updated_at: '2026-10-03T08:30:00Z',
    ...extra,
  }
}

function mountControl(m: Mistake) {
  return mount(MasteryControl, { props: { mistake: m } })
}

function selectValue(wrapper: ReturnType<typeof mountControl>) {
  return (wrapper.find('[data-testid="mastery"]').element as HTMLSelectElement).value
}

afterEach(() => vi.unstubAllGlobals())

describe('MasteryControl', () => {
  it('shows five levels and submits the chosen one', async () => {
    const { calls } = installFakeBackend({
      'PUT /api/mistakes/7/mastery': () => ({ data: mistake({ mastery_level: 3 }) }),
    })
    const wrapper = mountControl(mistake())

    expect(wrapper.findAll('[data-testid="mastery"] option')).toHaveLength(5)
    await wrapper.find('[data-testid="mastery"]').setValue('3')
    await flushPromises()

    expect(calls).toHaveLength(1)
    expect(calls[0].url).toBe('/api/mistakes/7/mastery')
    expect(calls[0].body).toEqual({ level: 3 })
  })

  it('emits the updated mistake on success', async () => {
    const updated = mistake({ mastery_level: 5, mastered_at: '2026-10-05T10:00:00Z' })
    installFakeBackend({ 'PUT /api/mistakes/7/mastery': () => ({ data: updated }) })
    const wrapper = mountControl(mistake())

    await wrapper.find('[data-testid="mastery"]').setValue('5')
    await flushPromises()

    expect(wrapper.emitted('update')?.[0]).toEqual([updated])
  })

  it('shows the mastered time only when the level reaches four', () => {
    const wrapper = mountControl(mistake({ mastery_level: 4, mastered_at: '2026-10-05T10:00:00Z' }))
    // 展示的是浏览器本地时区，只校验格式
    expect(wrapper.find('[data-testid="mastered-at"]').text()).toMatch(/掌握于 \d{4}-\d{2}-\d{2} \d{2}:\d{2}/)

    const low = mountControl(mistake({ mastery_level: 3, mastered_at: null }))
    expect(low.find('[data-testid="mastered-at"]').exists()).toBe(false)
  })

  it('is busy and disabled while submitting', async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    installFakeBackend({
      'PUT /api/mistakes/7/mastery': async () => {
        await gate
        return { data: mistake({ mastery_level: 3 }) }
      },
    })
    const wrapper = mountControl(mistake())

    await wrapper.find('[data-testid="mastery"]').setValue('3')

    expect(wrapper.find('[data-testid="mastery"]').attributes('disabled')).toBeDefined()

    release()
    await flushPromises()
    expect(wrapper.find('[data-testid="mastery"]').attributes('disabled')).toBeUndefined()
  })

  it('keeps the original level and shows the message when saving fails', async () => {
    installFakeBackend({
      'PUT /api/mistakes/7/mastery': () => ({ status: 500, message: '服务器开小差了，请稍后再试' }),
    })
    const wrapper = mountControl(mistake({ mastery_level: 2 }))

    await wrapper.find('[data-testid="mastery"]').setValue('4')
    await flushPromises()

    expect(wrapper.find('[data-testid="mastery-error"]').text()).toBe('服务器开小差了，请稍后再试')
    expect(selectValue(wrapper)).toBe('2')
    expect(wrapper.emitted('update')).toBeUndefined()
  })

  // T029 变异检验：去掉忙碌守卫，这个测试必须失败
  it('submits only once for rapid consecutive changes', async () => {
    let release!: () => void
    const gate = new Promise<void>((resolve) => (release = resolve))
    const { calls } = installFakeBackend({
      'PUT /api/mistakes/7/mastery': async () => {
        await gate
        return { data: mistake({ mastery_level: 3 }) }
      },
    })
    const wrapper = mountControl(mistake())

    const select = wrapper.find('[data-testid="mastery"]')
    // 直接派发事件：绕过 disabled 属性，模拟提交尚未完成时的连续改选
    const fireChange = (value: string) => {
      const el = select.element as HTMLSelectElement
      el.value = value
      el.dispatchEvent(new Event('change'))
    }
    fireChange('3')
    fireChange('4')

    expect(calls).toHaveLength(1)

    release()
    await flushPromises()
    expect(calls).toHaveLength(1)
  })
})
