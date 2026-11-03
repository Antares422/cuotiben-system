<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import type { Subject, Tag } from '../api/types'
import { hasActiveFilters, type FilterState } from '../filters'

const props = defineProps<{
  subjects: Subject[]
  tags: Tag[]
  modelValue: FilterState
}>()

const emit = defineEmits<{ (e: 'update:modelValue', value: FilterState): void }>()

const LEVELS = ['一级', '二级', '三级', '四级', '五级']

const expanded = ref(true)
const keyword = ref(props.modelValue.q ?? '')

watch(
  () => props.modelValue.q,
  (q) => {
    keyword.value = q ?? ''
  },
)

const anyActive = computed(() => hasActiveFilters(props.modelValue))

function change(patch: Partial<FilterState>) {
  emit('update:modelValue', { ...props.modelValue, ...patch })
}

function onSubject(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  change(value === '' ? { subject_id: undefined } : { subject_id: Number(value) })
}

function toggleTag(name: string) {
  const tags = props.modelValue.tags.includes(name)
    ? props.modelValue.tags.filter((t) => t !== name)
    : [...props.modelValue.tags, name]
  change({ tags })
}

function onMastery(bound: 'mastery_min' | 'mastery_max', event: Event) {
  const value = (event.target as HTMLSelectElement).value
  change(value === '' ? { [bound]: undefined } : { [bound]: Number(value) })
}

function submitKeyword() {
  const q = keyword.value.trim()
  change({ q: q === '' ? undefined : q })
}

function clearAll() {
  keyword.value = ''
  emit('update:modelValue', { tags: [] })
}
</script>

<template>
  <section class="filter-bar">
    <button
      type="button"
      class="filter-toggle"
      :aria-expanded="expanded"
      data-testid="filter-toggle"
      @click="expanded = !expanded"
    >
      筛选条件
      <span aria-hidden="true">{{ expanded ? '▲' : '▼' }}</span>
    </button>

    <div v-show="expanded" class="filter-panel" data-testid="filter-panel">
      <label class="filter-field">
        学科
        <select data-testid="filter-subject" :value="modelValue.subject_id ?? ''" @change="onSubject">
          <option value="">全部学科</option>
          <option v-for="s in subjects" :key="s.id" :value="s.id">{{ s.name }}</option>
        </select>
      </label>

      <div class="filter-field">
        标签 <small>多选，取交集</small>
        <div class="filter-tags">
          <button
            v-for="tag in tags"
            :key="tag.id"
            type="button"
            class="tag-chip"
            :class="{ on: modelValue.tags.includes(tag.name) }"
            :aria-pressed="modelValue.tags.includes(tag.name)"
            data-testid="filter-tag"
            @click="toggleTag(tag.name)"
          >
            # {{ tag.name }}
          </button>
          <p v-if="tags.length === 0" class="filter-hint">还没有标签</p>
        </div>
      </div>

      <div class="filter-field filter-range">
        掌握程度
        <div class="range-row">
          <select
            data-testid="mastery-min"
            :value="modelValue.mastery_min ?? ''"
            aria-label="最低掌握程度"
            @change="onMastery('mastery_min', $event)"
          >
            <option value="">不限</option>
            <option v-for="(label, i) in LEVELS" :key="label" :value="i + 1">{{ label }}</option>
          </select>
          <span aria-hidden="true">～</span>
          <select
            data-testid="mastery-max"
            :value="modelValue.mastery_max ?? ''"
            aria-label="最高掌握程度"
            @change="onMastery('mastery_max', $event)"
          >
            <option value="">不限</option>
            <option v-for="(label, i) in LEVELS" :key="label" :value="i + 1">{{ label }}</option>
          </select>
        </div>
      </div>

      <form class="filter-field filter-search" @submit.prevent="submitKeyword">
        <input
          v-model="keyword"
          type="text"
          maxlength="100"
          placeholder="搜内容、答案或错因"
          data-testid="filter-q"
        />
        <button type="submit" data-testid="filter-search">搜索</button>
      </form>

      <button v-if="anyActive" type="button" class="filter-clear" data-testid="filter-clear" @click="clearAll">
        清除全部
      </button>
    </div>
  </section>
</template>
