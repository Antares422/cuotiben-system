<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errorMessage } from '../api/client'
import { listMistakes } from '../api/mistakes'
import type { Mistake } from '../api/types'
import { formatDateTime } from '../format'
import { subjectColor } from '../subject-color'

const items = ref<Mistake[]>([])
const total = ref(0)
const nextPage = ref(1)
const loading = ref(true)
const error = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    const page = await listMistakes(nextPage.value)
    items.value = [...items.value, ...page.items]
    total.value = page.total
    nextPage.value = page.page + 1
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div>
    <header class="page-head">
      <h2>我的错题</h2>
      <p v-if="total > 0" class="count" data-testid="count">共 {{ total }} 道错题</p>
    </header>

    <p v-if="loading && items.length === 0" role="status" class="status" data-testid="loading">
      <span class="dots" aria-hidden="true"></span>加载中…
    </p>
    <div v-else-if="error" role="alert" class="error" data-testid="error">
      <p>{{ error }}</p>
      <!-- 列表为空时才需要单独的重试；已有内容时，"加载更多"按钮就是重试入口 -->
      <button v-if="items.length === 0" type="button" data-testid="retry" @click="load">
        重试
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
          <span class="stamp" :class="m.mastered ? 'done' : 'todo'">
            {{ m.mastered ? '已掌握' : '未掌握' }}
          </span>
        </p>
      </li>
    </ul>

    <button
      v-if="items.length < total"
      type="button"
      class="secondary more"
      data-testid="more"
      @click="load"
    >
      加载更多
    </button>
  </div>
</template>
