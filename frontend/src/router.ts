import type { RouteRecordRaw } from 'vue-router'
import MistakeDetailView from './views/MistakeDetailView.vue'
import MistakeListView from './views/MistakeListView.vue'
import UploadView from './views/UploadView.vue'

export const routes: RouteRecordRaw[] = [
  { path: '/', name: 'upload', component: UploadView },
  { path: '/mistakes', name: 'list', component: MistakeListView },
  { path: '/mistakes/:id', name: 'detail', component: MistakeDetailView, props: true },
]
