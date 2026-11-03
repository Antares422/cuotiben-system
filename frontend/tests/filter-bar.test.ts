import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import FilterBar from '../src/components/FilterBar.vue'
import type { FilterState } from '../src/filters'
import type { Subject, Tag } from '../src/api/types'

const SUBJECTS: Subject[] = [
  { id: 1, name: '数学', mistake_count: 3 },
  { id: 2, name: '英语', mistake_count: 1 },
]
const TAGS: Tag[] = [
  { id: 1, name: '函数', mistake_count: 2 },
  { id: 2, name: '几何', mistake_count: 0 },
]

function mountBar(modelValue: FilterState = { tags: [] }) {
  return mount(FilterBar, { props: { subjects: SUBJECTS, tags: TAGS, modelValue } })
}

describe('FilterBar', () => {
  it('renders the subject select, tag choices, mastery range and keyword input', () => {
    const wrapper = mountBar()

    const subjectOptions = wrapper.findAll('[data-testid="filter-subject"] option').map((o) => o.text())
    expect(subjectOptions).toEqual(['全部学科', '数学', '英语'])
    const tagChoices = wrapper.findAll('[data-testid="filter-tag"]').map((t) => t.text())
    expect(tagChoices).toEqual(['# 函数', '# 几何'])
    for (const testId of ['mastery-min', 'mastery-max']) {
      const options = wrapper.findAll(`[data-testid="${testId}"] option`).map((o) => o.text())
      expect(options).toEqual(['不限', '一级', '二级', '三级', '四级', '五级'])
    }
    expect(wrapper.find('[data-testid="filter-q"]').exists()).toBe(true)
  })

  it('emits the new state when the subject changes', async () => {
    const wrapper = mountBar()

    await wrapper.find('[data-testid="filter-subject"]').setValue('1')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([
      { subject_id: 1, tags: [] },
    ])
  })

  it('emits toggled tags, each click adding or removing one tag', async () => {
    const wrapper = mountBar()

    await wrapper.findAll('[data-testid="filter-tag"]')[0].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([{ tags: ['函数'] }])

    // 父组件回传新状态后再选第二个标签
    await wrapper.setProps({ modelValue: { tags: ['函数'] } })
    await wrapper.findAll('[data-testid="filter-tag"]')[1].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[1]).toEqual([{ tags: ['函数', '几何'] }])

    await wrapper.setProps({ modelValue: { tags: ['函数', '几何'] } })
    await wrapper.findAll('[data-testid="filter-tag"]')[0].trigger('click')
    expect(wrapper.emitted('update:modelValue')?.[2]).toEqual([{ tags: ['几何'] }])
  })

  it('emits the mastery range when either bound changes', async () => {
    const wrapper = mountBar()

    await wrapper.find('[data-testid="mastery-min"]').setValue('2')
    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([{ tags: [], mastery_min: 2 }])

    await wrapper.find('[data-testid="mastery-max"]').setValue('4')
    expect(wrapper.emitted('update:modelValue')?.[1]).toEqual([{ tags: [], mastery_max: 4 }])

    await wrapper.find('[data-testid="mastery-min"]').setValue('')
    expect(wrapper.emitted('update:modelValue')?.[2]).toEqual([{ tags: [] }])
  })

  it('emits the trimmed keyword on submit', async () => {
    const wrapper = mountBar()

    await wrapper.find('[data-testid="filter-q"]').setValue('  二次函数  ')
    await wrapper.find('form.filter-search').trigger('submit')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([{ tags: [], q: '二次函数' }])
  })

  it('shows the current filters as the initial control values', () => {
    const wrapper = mountBar({ tags: ['几何'], subject_id: 2, mastery_min: 3, q: 'abc' })

    expect((wrapper.find('[data-testid="filter-subject"]').element as HTMLSelectElement).value).toBe('2')
    expect((wrapper.find('[data-testid="mastery-min"]').element as HTMLSelectElement).value).toBe('3')
    expect((wrapper.find('[data-testid="filter-q"]').element as HTMLInputElement).value).toBe('abc')
    const chosen = wrapper
      .findAll('[data-testid="filter-tag"].on')
      .map((t) => t.text())
    expect(chosen).toEqual(['# 几何'])
  })

  it('emits an empty state when "clear all" is clicked', async () => {
    const wrapper = mountBar({ tags: ['几何'], q: 'abc' })

    await wrapper.find('[data-testid="filter-clear"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual([{ tags: [] }])
  })

  it('hides the clear button while no filter is active', () => {
    expect(mountBar().find('[data-testid="filter-clear"]').exists()).toBe(false)
    expect(mountBar({ tags: ['几何'] }).find('[data-testid="filter-clear"]').exists()).toBe(true)
  })

  it('collapses and expands the panel on mobile', async () => {
    const wrapper = mountBar()
    const toggle = () => wrapper.find('[data-testid="filter-toggle"]')
    const panelDisplay = () => (wrapper.find('[data-testid="filter-panel"]').element as HTMLElement).style.display

    expect(toggle().attributes('aria-expanded')).toBe('true')

    await toggle().trigger('click')
    expect(toggle().attributes('aria-expanded')).toBe('false')
    expect(panelDisplay()).toBe('none')

    await toggle().trigger('click')
    expect(toggle().attributes('aria-expanded')).toBe('true')
    expect(panelDisplay()).not.toBe('none')
  })
})
