<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { errorMessage } from '../api/client'
import { listMistakes, listSubjects, listTags } from '../api/mistakes'
import type { Mistake, Subject, Tag } from '../api/types'
import FilterBar from '../components/FilterBar.vue'
import MasteryControl from '../components/MasteryControl.vue'
import { filtersFromQuery, hasActiveFilters, queryFromFilters, type FilterState } from '../filters'
import { formatDateTime } from '../format'
import { subjectColor } from '../subject-color'

const route = useRoute()
const router = useRouter()

const filters = ref<FilterState>(filtersFromQuery(route.query))
const subjects = ref<Subject[]>([])
const tags = ref<Tag[]>([])
const items = ref<Mistake[]>([])
const total = ref(0)
const overallTotal = ref(0)
const nextPage = ref(1)
const loading = ref(true)
const error = ref('')
const notice = ref('')

async function load(reset = true) {
  if (reset) {
    items.value = []
    nextPage.value = 1
  }
  loading.value = true
  error.value = ''
  try {
    const page = await listMistakes({ page: nextPage.value, page_size: 20, ...filters.value })
    items.value = reset ? page.items : [...items.value, ...page.items]
    total.value = page.total
    overallTotal.value = page.overall_total
    nextPage.value = page.page + 1
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

async function applyFilters(next: FilterState) {
  filters.value = next
  await router.replace({ query: queryFromFilters(next) })
  await load()
}

/** 学科、标签列表加载完成后，剔除已经失效的筛选条件（FR-010）。 */
async function loadMeta() {
  try {
    const [s, t] = await Promise.all([listSubjects(), listTags()])
    subjects.value = s
    tags.value = t
  } catch (e) {
    notice.value = errorMessage(e)
    return
  }
  const next: FilterState = { ...filters.value, tags: [...filters.value.tags] }
  const removed: string[] = []
  if (next.subject_id != null && !subjects.value.some((s) => s.id === next.subject_id)) {
    delete next.subject_id
    removed.push('学科')
  }
  const keptTags = next.tags.filter((name) => tags.value.some((t) => t.name === name))
  if (keptTags.length !== next.tags.length) {
    next.tags = keptTags
    removed.push('标签')
  }
  if (removed.length > 0) {
    notice.value = `部分筛选条件已失效（${removed.join('、')}），已自动清除`
    await applyFilters(next)
  }
}

function onMasteryUpdated(updated: Mistake) {
  const f = filters.value
  const outOfRange =
    (f.mastery_min != null && updated.mastery_level < f.mastery_min) ||
    (f.mastery_max != null && updated.mastery_level > f.mastery_max)
  if (outOfRange) {
    // 调级后不再符合筛选条件：立即消失，总数减一
    items.value = items.value.filter((m) => m.id !== updated.id)
    total.value = Math.max(0, total.value - 1)
  } else {
    const index = items.value.findIndex((m) => m.id === updated.id)
    if (index >= 0) items.value[index] = updated
  }
}

function goCleanup() {
  void applyFilters({ ...filters.value, mastery_min: 4, mastery_max: undefined })
}

onMounted(() => {
  void loadMeta()
  void load()
})
</script>

<template>
  <div>
    <header class="page-head">
      <h2>我的错题</h2>
      <p v-if="total > 0" class="count" data-testid="count">共 {{ total }} 道错题</p>
    </header>

    <button
      v-if="overallTotal > 100"
      type="button"
      class="capacity"
      data-testid="capacity"
      @click="goCleanup"
    >
      已超过 100 题，建议清理已熟练的题
    </button>

    <FilterBar v-model="filters" :subjects="subjects" :tags="tags" @update:model-value="applyFilters" />

    <p v-if="notice" class="notice" data-testid="notice">{{ notice }}</p>

    <p v-if="loading && items.length === 0" role="status" class="status" data-testid="loading">
      <span class="dots" aria-hidden="true"></span>加载中…
    </p>
    <div v-else-if="error" role="alert" class="error" data-testid="error">
      <p>{{ error }}</p>
      <!-- 列表为空时才需要单独的重试；已有内容时，"加载更多"按钮就是重试入口 -->
      <button v-if="items.length === 0" type="button" data-testid="retry" @click="load()">
        重试
      </button>
    </div>
    <div v-else-if="items.length === 0 && hasActiveFilters(filters)" class="empty" data-testid="no-results">
      <p>没有符合条件的错题</p>
      <button type="button" class="secondary" data-testid="clear-filters" @click="applyFilters({ tags: [] })">
        清除全部条件
      </button>
    </div>
    <div v-else-if="items.length === 0" class="empty" data-testid="empty">
      <svg viewBox="0 0 120 120" class="empty-art" aria-hidden="true">
        <rect x="26" y="14" width="68" height="92" rx="6" fill="#fffdf6" stroke="#1f2a44" stroke-width="3" />
        <path d="M26 34h68M26 54h68M26 74h68M26 94h68" stroke="#c9dbe9" stroke-width="2" />
        <path d="M44 14v92" stroke="#e8a09a" stroke-width="2" />
        <circle cx="26" cy="30" r="3.5" fill="#1f2a44" />
        <circle cx="26" cy="60" r="3.5" fill="#1f2a44" />
        <circle cx="26" cy="90" r="3.5" fill="#1f2a44" />
        <path d="M58 44q8-8 16 0t16 0" stroke="#d0312d" stroke-width="3" fill="none" stroke-linecap="round" />
      </svg>
      <p>本子还是空的，<RouterLink to="/">去录入第一道</RouterLink>吧</p>
    </div>

    <ul class="list">
      <li
        v-for="(m, index) in items"
        :key="m.id"
        class="card"
        :style="{ '--accent': subjectColor(m.subject.id), '--i': index % 12 }"
        data-testid="item"
      >
        <RouterLink class="title" :to="{ name: 'detail', params: { id: m.id } }">
          {{ m.content }}
        </RouterLink>
        <p class="meta">
          <span class="chip subject">{{ m.subject.name }}</span>
          <span v-for="tag in m.tags" :key="tag" class="chip tag"># {{ tag }}</span>
        </p>
        <p class="foot">
          <time>{{ formatDateTime(m.created_at) }}</time>
          <MasteryControl :mistake="m" @update="onMasteryUpdated" />
        </p>
      </li>
    </ul>

    <button
      v-if="items.length < total"
      type="button"
      class="secondary more"
      data-testid="more"
      @click="load(false)"
    >
      加载更多
    </button>
  </div>
</template>
