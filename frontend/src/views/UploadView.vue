<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { errorMessage } from '../api/client'
import { createMistake, listSubjects, uploadImage } from '../api/mistakes'
import type { Subject } from '../api/types'

const router = useRouter()

const subjects = ref<Subject[]>([])
const subjectId = ref<number | ''>('')
const content = ref('')
const answer = ref('')
const errorReason = ref('')
const tagsText = ref('')
const imageId = ref<string | null>(null)
const imageUrl = ref<string | null>(null)
const uploading = ref(false)
const saving = ref(false)
const notice = ref('')
const error = ref('')

onMounted(async () => {
  subjects.value = await listSubjects()
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
    const saved = await createMistake({
      content: content.value.trim(),
      subject_id: subjectId.value,
      answer: blankToNull(answer.value),
      error_reason: blankToNull(errorReason.value),
      tags: parseTags(tagsText.value),
      image_id: imageId.value,
    })
    router.push({ name: 'detail', params: { id: saved.id } })
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    saving.value = false
  }
}

async function onPhotoChosen(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  uploading.value = true
  error.value = ''
  try {
    const result = await uploadImage(file)
    imageId.value = result.image_id
    imageUrl.value = result.image_url
    content.value = result.ocr.text
    notice.value = result.ocr.status === 'ok' ? '' : (result.ocr.message ?? '')
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    uploading.value = false
  }
}
</script>

<template>
  <div>
    <label class="picker">
      <input
        type="file"
        accept="image/*"
        capture="environment"
        data-testid="photo"
        :disabled="uploading"
        @change="onPhotoChosen"
      />
      {{ imageUrl ? '换一张图片' : '拍照 / 选择错题图片' }}
    </label>
    <p v-if="uploading" role="status" class="status" data-testid="status">正在识别文字…</p>
    <p v-if="error" role="alert" class="error" data-testid="error">{{ error }}</p>
    <p v-if="notice" class="notice" data-testid="notice">{{ notice }}</p>
    <img v-if="imageUrl" :src="imageUrl" alt="题目原图" class="preview" data-testid="preview" />

    <form @submit.prevent="onSave">
      <label for="content">题目内容 <span class="req">*</span></label>
      <textarea id="content" v-model="content" rows="5" data-testid="content" />

      <label for="subject">学科 <span class="req">*</span></label>
      <select id="subject" v-model="subjectId" data-testid="subject">
        <option value="">请选择学科</option>
        <option v-for="s in subjects" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>

      <label for="answer">正确答案</label>
      <textarea id="answer" v-model="answer" rows="2" data-testid="answer" />

      <label for="error-reason">错误原因</label>
      <textarea id="error-reason" v-model="errorReason" rows="2" data-testid="error-reason" />

      <label for="tags">知识点标签（用逗号或空格分隔）</label>
      <input id="tags" v-model="tagsText" type="text" data-testid="tags" />

      <div class="actions">
        <button type="submit" :disabled="saving" data-testid="save">
          {{ saving ? '保存中…' : '保存错题' }}
        </button>
      </div>
    </form>
  </div>
</template>
