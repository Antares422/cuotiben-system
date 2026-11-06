<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage } from '../api/client'
import { deleteMistake, getMistake, setMastery } from '../api/mistakes'
import { formatDateTime } from '../format'
import { subjectColor } from '../subject-color'
import MasteryControl from '../components/MasteryControl.vue'
import type { Mistake } from '../api/types'

const props = defineProps<{ id: string }>()

const router = useRouter()

const mistake = ref<Mistake | null>(null)
const loading = ref(true)
const error = ref('')
const actionError = ref('')
const deleting = ref(false)
const stepping = ref(false)
const stepError = ref('')

onMounted(async () => {
  try {
    mistake.value = await getMistake(Number(props.id))
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
})

function onMasteryUpdated(updated: Mistake) {
  mistake.value = updated
}

// T073：详情页底部的升级/降级按钮，规则与掌握程度选择一致（达四级记掌握时间）
async function onStep(delta: number) {
  if (!mistake.value || stepping.value) return
  const level = mistake.value.mastery_level + delta
  if (level < 1 || level > 5) return
  stepping.value = true
  stepError.value = ''
  try {
    mistake.value = await setMastery(mistake.value.id, level)
  } catch (e) {
    stepError.value = errorMessage(e)
  } finally {
    stepping.value = false
  }
}

async function onDelete() {
  if (!mistake.value || deleting.value) return
  // 四级及以上才是"已掌握"，清理前二次确认；低于四级直接请求，展示服务端的 409 原因
  if (mistake.value.mastery_level >= 4 && !window.confirm('确定要清理这道已掌握的错题吗？')) return
  deleting.value = true
  actionError.value = ''
  try {
    await deleteMistake(mistake.value.id)
    router.push({ name: 'list' })
  } catch (e) {
    actionError.value = errorMessage(e)
  } finally {
    deleting.value = false
  }
}
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
      <span class="detail-actions">
        <RouterLink
          :to="{ name: 'edit', params: { id: mistake.id } }"
          class="edit-link"
          data-testid="edit"
        >
          编辑
        </RouterLink>
        <button
          type="button"
          class="delete-button"
          :disabled="deleting"
          data-testid="delete"
          @click="onDelete"
        >
          {{ deleting ? '清理中…' : '删除' }}
        </button>
      </span>
    </header>

    <figure v-if="mistake.image_url" class="polaroid">
      <img :src="mistake.image_url" alt="题目原图" data-testid="image" />
    </figure>

    <p class="meta">
      <span class="chip subject">{{ mistake.subject.name }}</span>
      <span v-for="tag in mistake.tags" :key="tag" class="chip tag"># {{ tag }}</span>
    </p>

    <MasteryControl :mistake="mistake" @update="onMasteryUpdated" />
    <p v-if="actionError" role="alert" class="error" data-testid="action-error">{{ actionError }}</p>

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

    <section class="stepper" data-testid="stepper">
      <button
        type="button"
        class="step-button"
        data-testid="level-down"
        :disabled="stepping || mistake.mastery_level <= 1"
        @click="onStep(-1)"
      >
        − 降级一级
      </button>
      <button
        type="button"
        class="step-button primary"
        data-testid="level-up"
        :disabled="stepping || mistake.mastery_level >= 5"
        @click="onStep(1)"
      >
        升级一级 ＋
      </button>
    </section>
    <p v-if="stepError" role="alert" class="error" data-testid="step-error">{{ stepError }}</p>
  </article>
</template>
