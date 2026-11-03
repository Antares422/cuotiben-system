<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { errorMessage } from '../api/client'
import { createSubject, deleteSubject, deleteTag, listSubjects, listTags, updateSubject, updateTag } from '../api/mistakes'
import type { Subject, Tag } from '../api/types'

type Kind = 'subject' | 'tag'

const subjects = ref<Subject[]>([])
const tags = ref<Tag[]>([])
const loading = ref(true)
const error = ref('')
const newSubjectName = ref('')
const addError = ref('')
const addBusy = ref(false)
const editing = ref<{ kind: Kind; id: number; name: string } | null>(null)
const renameBusy = ref(false)
const rowError = ref<{ key: string; message: string } | null>(null)

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [s, t] = await Promise.all([listSubjects(), listTags()])
    subjects.value = s
    tags.value = t
  } catch (e) {
    error.value = errorMessage(e)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})

async function addSubject() {
  if (addBusy.value) return
  addBusy.value = true
  addError.value = ''
  try {
    const created = await createSubject(newSubjectName.value)
    subjects.value = [...subjects.value, created]
    newSubjectName.value = ''
  } catch (e) {
    addError.value = errorMessage(e)
  } finally {
    addBusy.value = false
  }
}

function startRename(kind: Kind, item: Subject | Tag) {
  rowError.value = null
  editing.value = { kind, id: item.id, name: item.name }
}

function cancelRename() {
  editing.value = null
}

async function saveRename() {
  if (!editing.value || renameBusy.value) return
  renameBusy.value = true
  rowError.value = null
  const { kind, id, name } = editing.value
  try {
    if (kind === 'subject') {
      const updated = await updateSubject(id, name)
      subjects.value = subjects.value.map((s) => (s.id === id ? updated : s))
    } else {
      const updated = await updateTag(id, name)
      tags.value = tags.value.map((t) => (t.id === id ? updated : t))
    }
    editing.value = null
  } catch (e) {
    // 失败保持原样：列表未被修改，编辑态留在原地
    rowError.value = { key: `${kind}:${id}`, message: errorMessage(e) }
  } finally {
    renameBusy.value = false
  }
}

async function removeSubject(subject: Subject) {
  rowError.value = null
  try {
    await deleteSubject(subject.id)
    subjects.value = subjects.value.filter((s) => s.id !== subject.id)
  } catch (e) {
    // 被拒时在原处展示原因
    rowError.value = { key: `subject:${subject.id}`, message: errorMessage(e) }
  }
}

async function removeTag(tag: Tag) {
  if (!window.confirm(`确定删除标签「${tag.name}」吗？带这个标签的错题会保留。`)) return
  rowError.value = null
  try {
    await deleteTag(tag.id)
    tags.value = tags.value.filter((t) => t.id !== tag.id)
  } catch (e) {
    rowError.value = { key: `tag:${tag.id}`, message: errorMessage(e) }
  }
}
</script>

<template>
  <header class="page-head">
    <h2>分类管理</h2>
  </header>

  <p v-if="loading" role="status" class="status" data-testid="loading">
    <span class="dots" aria-hidden="true"></span>加载中…
  </p>
  <div v-else-if="error" role="alert" class="error" data-testid="error">
    <p>{{ error }}</p>
    <button type="button" data-testid="retry" @click="load">重试</button>
  </div>

  <template v-else>
    <section class="manage-section" data-testid="subjects">
      <h3>学科</h3>
      <form class="manage-add" @submit.prevent="addSubject">
        <input
          v-model="newSubjectName"
          type="text"
          maxlength="50"
          placeholder="新增学科，如：物理"
          data-testid="new-subject-name"
        />
        <button type="submit" :disabled="addBusy" data-testid="subject-create">新增</button>
      </form>
      <p v-if="addError" role="alert" class="error" data-testid="subject-add-error">{{ addError }}</p>

      <ul class="manage-list">
        <li v-for="s in subjects" :key="s.id" class="manage-row" data-testid="subject-row">
          <template v-if="editing?.kind === 'subject' && editing.id === s.id">
            <input v-model="editing.name" type="text" class="rename-input" data-testid="rename-input" />
            <button type="button" :disabled="renameBusy" data-testid="rename-save" @click="saveRename">
              保存
            </button>
            <button type="button" class="secondary" data-testid="rename-cancel" @click="cancelRename">
              取消
            </button>
          </template>
          <template v-else>
            <span class="row-name">{{ s.name }}</span>
            <span class="row-count" data-testid="subject-count">{{ s.mistake_count ?? 0 }} 题</span>
            <button type="button" class="row-action" data-testid="subject-rename" @click="startRename('subject', s)">
              编辑
            </button>
            <button type="button" class="row-action danger" data-testid="subject-delete" @click="removeSubject(s)">
              删除
            </button>
          </template>
          <p
            v-if="rowError?.key === `subject:${s.id}`"
            role="alert"
            class="error"
            data-testid="subject-error"
          >
            {{ rowError.message }}
          </p>
        </li>
        <li v-if="subjects.length === 0" class="empty">还没有学科</li>
      </ul>
    </section>

    <section class="manage-section" data-testid="tags">
      <h3>标签</h3>
      <p v-if="tags.length === 0" class="empty" data-testid="tags-empty">还没有标签</p>
      <ul v-else class="manage-list">
        <li v-for="t in tags" :key="t.id" class="manage-row" data-testid="tag-row">
          <template v-if="editing?.kind === 'tag' && editing.id === t.id">
            <input v-model="editing.name" type="text" class="rename-input" data-testid="rename-input" />
            <button type="button" :disabled="renameBusy" data-testid="rename-save" @click="saveRename">
              保存
            </button>
            <button type="button" class="secondary" data-testid="rename-cancel" @click="cancelRename">
              取消
            </button>
          </template>
          <template v-else>
            <span class="row-name"># {{ t.name }}</span>
            <span class="row-count" data-testid="tag-count">{{ t.mistake_count }} 题</span>
            <button type="button" class="row-action" data-testid="tag-rename" @click="startRename('tag', t)">
              编辑
            </button>
            <button type="button" class="row-action danger" data-testid="tag-delete" @click="removeTag(t)">
              删除
            </button>
          </template>
          <p v-if="rowError?.key === `tag:${t.id}`" role="alert" class="error" data-testid="tag-error">
            {{ rowError.message }}
          </p>
        </li>
      </ul>
    </section>
  </template>
</template>
