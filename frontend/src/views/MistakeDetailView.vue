<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errorMessage } from '../api/client'
import { getMistake } from '../api/mistakes'
import { formatDateTime } from '../format'
import { subjectColor } from '../subject-color'
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
  <p v-if="loading" role="status" class="status" data-testid="loading">
    <span class="dots" aria-hidden="true"></span>加载中…
  </p>
  <div v-else-if="error" role="alert" class="error" data-testid="error">
    <p>{{ error }}</p>
    <RouterLink to="/mistakes" data-testid="back">返回错题本</RouterLink>
  </div>
  <article v-else-if="mistake" class="detail" :style="{ '--accent': subjectColor(mistake.subject.id) }">
    <header class="detail-head">
      <RouterLink to="/mistakes" class="back">← 错题本</RouterLink>
      <span class="stamp" :class="mistake.mastered ? 'done' : 'todo'">
        {{ mistake.mastered ? '已掌握' : '未掌握' }}
      </span>
    </header>

    <figure v-if="mistake.image_url" class="polaroid">
      <img :src="mistake.image_url" alt="题目原图" data-testid="image" />
    </figure>

    <p class="meta">
      <span class="chip subject">{{ mistake.subject.name }}</span>
      <span v-for="tag in mistake.tags" :key="tag" class="chip tag"># {{ tag }}</span>
    </p>

    <section class="sheet">
      <h3>题目</h3>
      <p class="text ruled-text" data-testid="content">{{ mistake.content }}</p>
    </section>

    <section class="note answer">
      <h3>正确答案</h3>
      <p class="text" :class="{ empty: !mistake.answer }" data-testid="answer">
        {{ mistake.answer ?? '未填写' }}
      </p>
    </section>

    <section class="note reason">
      <h3>错误原因</h3>
      <p class="text pen" :class="{ empty: !mistake.error_reason }" data-testid="error-reason">
        {{ mistake.error_reason ?? '未填写' }}
      </p>
    </section>

    <p class="time">
      录入于 <time data-testid="created-at">{{ formatDateTime(mistake.created_at) }}</time>
    </p>
  </article>
</template>
