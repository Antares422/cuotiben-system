<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
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

const STEPS = ['拍照', '核对', '保存']
// 拍了照或自己敲了题目，就进入"核对"；点了保存，就进入"保存"
const step = computed(() => {
  if (saving.value) return 2
  return imageId.value || content.value.trim() ? 1 : 0
})

onMounted(async () => {
  try {
    subjects.value = await listSubjects()
  } catch (e) {
    error.value = errorMessage(e)
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
    <ol class="steps" data-testid="steps">
      <li
        v-for="(label, index) in STEPS"
        :key="label"
        :class="{ done: index < step }"
        :aria-current="index === step ? 'step' : undefined"
      >
        {{ label }}
      </li>
    </ol>

    <label class="picker" :class="{ busy: uploading, has: imageUrl }">
      <input
        type="file"
        accept="image/*"
        capture="environment"
        data-testid="photo"
        :disabled="uploading"
        @change="onPhotoChosen"
      />
      <svg viewBox="0 0 48 48" class="cam" aria-hidden="true">
        <path
          d="M8 15h8l3-5h10l3 5h8a2 2 0 0 1 2 2v20a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2V17a2 2 0 0 1 2-2z"
          fill="none" stroke="currentColor" stroke-width="2.6" stroke-linejoin="round"
        />
        <circle cx="24" cy="26" r="7" fill="none" stroke="currentColor" stroke-width="2.6" />
      </svg>
      <strong>{{ imageUrl ? '换一张图片' : '拍下这道错题' }}</strong>
      <small>{{ imageUrl ? '重新识别会覆盖下面的题目内容' : '自动识别文字，识别不准可以直接改' }}</small>
    </label>

    <p v-if="error" role="alert" class="error" data-testid="error">{{ error }}</p>
    <p v-if="notice" class="notice" data-testid="notice">{{ notice }}</p>

    <figure v-if="imageUrl" class="polaroid" :class="{ scanning: uploading }">
      <img :src="imageUrl" alt="题目原图" data-testid="preview" />
    </figure>
    <p v-if="uploading" role="status" class="status" data-testid="status">
      <span class="dots" aria-hidden="true"></span>正在识别文字…
    </p>

    <form class="sheet" @submit.prevent="onSave">
      <label for="content" class="field">题目内容 <i class="req" title="必填"></i></label>
      <textarea id="content" v-model="content" rows="5" class="ruled" data-testid="content" />

      <label for="subject" class="field">学科 <i class="req" title="必填"></i></label>
      <select id="subject" v-model="subjectId" data-testid="subject">
        <option value="">请选择学科</option>
        <option v-for="s in subjects" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>

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
          {{ saving ? '保存中…' : '保存错题' }}
        </button>
      </div>
    </form>
  </div>
</template>
