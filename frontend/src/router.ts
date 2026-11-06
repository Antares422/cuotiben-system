import type { RouteRecordRaw } from 'vue-router'
import ManageView from './views/ManageView.vue'
import MistakeDetailView from './views/MistakeDetailView.vue'
import MistakeEditView from './views/MistakeEditView.vue'
import MistakeListView from './views/MistakeListView.vue'
import UploadView from './views/UploadView.vue'

export const routes: RouteRecordRaw[] = [
  { path: '/', name: 'upload', component: UploadView },
  { path: '/mistakes', name: 'list', component: MistakeListView },
  { path: '/mistakes/:id', name: 'detail', component: MistakeDetailView, props: true },
  { path: '/mistakes/:id/edit', name: 'edit', component: MistakeEditView, props: true },
  { path: '/manage', name: 'manage', component: ManageView },
]
