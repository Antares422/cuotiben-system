<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errorMessage } from '../api/client'
import { getMistake } from '../api/mistakes'
import { formatDateTime } from '../format'
import type { Mistake } from '../api/types'

const props = defineProps<{ id: string }>()

const mistake = ref<Mistake | null>(null)
const loading = ref(true)
const error = ref('')

onMounted(async () => {
  try {
    mistake.value = await getMistake(Number(props.id))
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
})
</script>

<template>
  <p v-if="loading" role="status" data-testid="loading">加载中…</p>
  <div v-else-if="error" role="alert" class="error" data-testid="error">
    <p>{{ error }}</p>
    <RouterLink to="/mistakes" data-testid="back">返回错题本</RouterLink>
  </div>
  <article v-else-if="mistake" class="detail">
    <img v-if="mistake.image_url" :src="mistake.image_url" alt="题目原图" data-testid="image" />
    <p class="meta">
      <span class="chip">{{ mistake.subject.name }}</span>
      <span class="chip" :class="{ done: mistake.mastered }">
        {{ mistake.mastered ? '已掌握' : '未掌握' }}
      </span>
      <span v-for="tag in mistake.tags" :key="tag" class="chip tag">{{ tag }}</span>
    </p>
    <h2>题目</h2>
    <p class="text" data-testid="content">{{ mistake.content }}</p>
    <h2>正确答案</h2>
    <p class="text" data-testid="answer">{{ mistake.answer ?? '未填写' }}</p>
    <h2>错误原因</h2>
    <p class="text" data-testid="error-reason">{{ mistake.error_reason ?? '未填写' }}</p>
    <p class="time">
      录入于 <time data-testid="created-at">{{ formatDateTime(mistake.created_at) }}</time>
    </p>
  </article>
</template>
