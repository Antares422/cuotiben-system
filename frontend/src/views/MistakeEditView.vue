<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage } from '../api/client'
import { getMistake, updateMistake } from '../api/mistakes'
import SubjectSelect from '../components/SubjectSelect.vue'

const props = defineProps<{ id: string }>()

const router = useRouter()

const subjectId = ref<number | ''>('')
const content = ref('')
const answer = ref('')
const errorReason = ref('')
const tagsText = ref('')
const imageId = ref<string | null>(null)
const loading = ref(true)
const saving = ref(false)
const loadError = ref('')
const error = ref('')

onMounted(async () => {
  try {
    const mistake = await getMistake(Number(props.id))
    subjectId.value = mistake.subject.id
    content.value = mistake.content
    answer.value = mistake.answer ?? ''
    errorReason.value = mistake.error_reason ?? ''
    tagsText.value = mistake.tags.join('，')
    imageId.value = mistake.image_id
  } catch (e) {
    loadError.value = errorMessage(e)
  } finally {
    loading.value = false
  }
})

/** 标签可以用中英文逗号、顿号或空格分隔；去掉空白并去重。 */
function parseTags(text: string): string[] {
  return [...new Set(text.split(/[,，、\s]+/).filter(Boolean))]
}

function blankToNull(text: string): string | null {
  return text.trim() === '' ? null : text.trim()
}

async function onSave() {
  if (saving.value) return
  error.value = ''
  if (!content.value.trim()) {
    error.value = '题目内容不能为空'
    return
  }
  if (subjectId.value === '') {
    error.value = '请选择学科'
    return
  }
  saving.value = true
  try {
    const saved = await updateMistake(Number(props.id), {
      content: content.value.trim(),
      subject_id: subjectId.value,
      answer: blankToNull(answer.value),
      error_reason: blankToNull(errorReason.value),
      tags: parseTags(tagsText.value),
      image_id: imageId.value,
    })
    router.push({ name: 'detail', params: { id: saved.id } })
  } catch (e) {
    // 失败时表单内容保持已填状态
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <p v-if="loading" role="status" class="status" data-testid="loading">
    <span class="dots" aria-hidden="true"></span>加载中…
  </p>
  <div v-else-if="loadError" role="alert" class="error" data-testid="error">
    <p>{{ loadError }}</p>
    <RouterLink to="/mistakes">返回错题本</RouterLink>
  </div>
  <div v-else>
    <header class="page-head">
      <h2>编辑错题</h2>
    </header>

    <p v-if="error" role="alert" class="error" data-testid="error">{{ error }}</p>

    <form class="sheet" @submit.prevent="onSave">
      <label for="content" class="field">题目内容 <i class="req" title="必填"></i></label>
      <textarea id="content" v-model="content" rows="5" class="ruled" data-testid="content" />

      <label class="field">学科 <i class="req" title="必填"></i></label>
      <SubjectSelect v-model="subjectId" />

      <label for="answer" class="field">正确答案</label>
      <textarea id="answer" v-model="answer" rows="2" class="ruled" data-testid="answer" />

      <label for="error-reason" class="field">错误原因</label>
      <textarea
        id="error-reason"
        v-model="errorReason"
        rows="2"
        class="ruled pen"
        placeholder="用一句话写下当时为什么错"
        data-testid="error-reason"
      />

      <label for="tags" class="field">知识点标签 <small>用逗号或空格分隔</small></label>
      <input id="tags" v-model="tagsText" type="text" data-testid="tags" />

      <div class="actions">
        <button type="submit" :disabled="saving" data-testid="save">
          {{ saving ? '保存中…' : '保存修改' }}
        </button>
      </div>
    </form>
  </div>
</template>
