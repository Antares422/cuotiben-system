<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errorMessage } from '../api/client'
import { createSubject, listSubjects } from '../api/mistakes'
import type { Subject } from '../api/types'

const NEW = '__new__'

const props = defineProps<{ modelValue: number | '' }>()
const emit = defineEmits<{ (e: 'update:modelValue', value: number | ''): void }>()

const selectEl = ref<HTMLSelectElement>()
const subjects = ref<Subject[]>([])
const loadError = ref('')
const adding = ref(false)
const newName = ref('')
const addError = ref('')
const busy = ref(false)

onMounted(async () => {
  try {
    subjects.value = await listSubjects()
  } catch (e) {
    loadError.value = errorMessage(e)
  }
})

function onSelect(event: Event) {
  const value = (event.target as HTMLSelectElement).value
  if (value === NEW) {
    adding.value = true
    newName.value = ''
    addError.value = ''
    return
  }
  adding.value = false
  emit('update:modelValue', value === '' ? '' : Number(value))
}

async function confirmAdd() {
  if (busy.value) return
  busy.value = true
  addError.value = ''
  try {
    const created = await createSubject(newName.value)
    subjects.value = [...subjects.value, created]
    adding.value = false
    emit('update:modelValue', created.id)
  } catch (e) {
    addError.value = errorMessage(e)
    // 创建失败：下拉回到原来选中的学科
    if (selectEl.value) selectEl.value.value = String(props.modelValue)
  } finally {
    busy.value = false
  }
}

function cancelAdd() {
  adding.value = false
  addError.value = ''
  if (selectEl.value) selectEl.value.value = String(props.modelValue)
}
</script>

<template>
  <div class="subject-select">
    <select ref="selectEl" data-testid="subject" :value="modelValue" @change="onSelect">
      <option value="">请选择学科</option>
      <option v-for="s in subjects" :key="s.id" :value="s.id">{{ s.name }}</option>
      <option :value="NEW">＋ 新增学科</option>
    </select>

    <p v-if="loadError" role="alert" class="error" data-testid="error">{{ loadError }}</p>

    <div v-if="adding" class="subject-add" data-testid="subject-add">
      <input
        v-model="newName"
        type="text"
        maxlength="50"
        placeholder="新学科名称"
        data-testid="new-subject"
      />
      <div class="subject-add-actions">
        <button type="button" :disabled="busy" data-testid="new-subject-confirm" @click="confirmAdd">
          确定
        </button>
        <button type="button" class="secondary" data-testid="new-subject-cancel" @click="cancelAdd">
          取消
        </button>
      </div>
      <p v-if="addError" role="alert" class="error" data-testid="new-subject-error">{{ addError }}</p>
    </div>
  </div>
</template>
