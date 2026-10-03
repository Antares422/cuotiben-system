<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errorMessage } from '../api/client'
import { listMistakes } from '../api/mistakes'
import { formatDateTime } from '../format'
import type { Mistake } from '../api/types'

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
    <p v-if="loading && items.length === 0" role="status" class="status" data-testid="loading">
      加载中…
    </p>
    <div v-else-if="error" role="alert" class="error" data-testid="error">
      <p>{{ error }}</p>
      <!-- 列表为空时才需要单独的重试；已有内容时，"加载更多"按钮就是重试入口 -->
      <button v-if="items.length === 0" type="button" data-testid="retry" @click="load">
        重试
      </button>
    </div>
    <p v-else-if="items.length === 0" class="empty" data-testid="empty">
      还没有错题，<RouterLink to="/">去录入第一道</RouterLink>吧
    </p>
    <ul class="list">
      <li v-for="m in items" :key="m.id" class="card" data-testid="item">
        <RouterLink class="title" :to="{ name: 'detail', params: { id: m.id } }">
          {{ m.content }}
        </RouterLink>
        <p class="meta">
          <span class="chip">{{ m.subject.name }}</span>
          <span v-for="tag in m.tags" :key="tag" class="chip tag">{{ tag }}</span>
          <span class="chip" :class="m.mastered ? 'done' : 'todo'">
            {{ m.mastered ? '已掌握' : '未掌握' }}
          </span>
          <time class="time">{{ formatDateTime(m.created_at) }}</time>
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
