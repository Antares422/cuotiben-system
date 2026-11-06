<script setup lang="ts">
import { ref } from 'vue'
import { errorMessage } from '../api/client'
import { setMastery } from '../api/mistakes'
import type { Mistake } from '../api/types'
import { formatDateTime } from '../format'

const props = defineProps<{ mistake: Pick<Mistake, 'id' | 'mastery_level' | 'mastered_at'> }>()
const emit = defineEmits<{ (e: 'update', value: Mistake): void }>()

const LEVELS = ['一级', '二级', '三级', '四级', '五级']

const busy = ref(false)
const error = ref('')

async function onChange(event: Event) {
  // 忙碌守卫：快速连续点击/改选只提交一次
  if (busy.value) return
  const level = Number((event.target as HTMLSelectElement).value)
  if (!Number.isInteger(level) || level < 1 || level > 5 || level === props.mistake.mastery_level) return
  busy.value = true
  error.value = ''
  try {
    const updated = await setMastery(props.mistake.id, level)
    emit('update', updated)
  } catch (e) {
    // 失败保持原状：不 emit，选择框绑定的仍是原等级
    error.value = errorMessage(e)
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <!-- @click.stop：在列表卡片里点击控件不能触发卡片跳转 -->
  <div class="mastery" @click.stop>
    <label class="mastery-label">
      掌握程度
      <select
        class="mastery-select"
        data-testid="mastery"
        :value="mistake.mastery_level"
        :disabled="busy"
        :aria-busy="busy"
        @change="onChange"
      >
        <option v-for="(label, i) in LEVELS" :key="label" :value="i + 1">{{ label }}</option>
      </select>
    </label>
    <p v-if="mistake.mastery_level >= 4 && mistake.mastered_at" class="mastered-at" data-testid="mastered-at">
      掌握于 <time>{{ formatDateTime(mistake.mastered_at) }}</time>
    </p>
    <p v-if="error" role="alert" class="error" data-testid="mastery-error">{{ error }}</p>
  </div>
</template>
