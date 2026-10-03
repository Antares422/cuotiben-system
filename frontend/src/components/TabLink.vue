<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'

// "/mistakes/7" 这样的子页面也应当让 "/mistakes" 这个 tab 保持高亮；而 "/" 只匹配首页本身
const props = defineProps<{ to: string }>()
const route = useRoute()
const current = computed(() =>
  props.to === '/' ? route.path === '/' : route.path === props.to || route.path.startsWith(`${props.to}/`),
)
</script>

<template>
  <RouterLink v-slot="{ href, navigate }" :to="to" custom>
    <a :href="href" :aria-current="current ? 'page' : undefined" @click="navigate">
      <slot />
    </a>
  </RouterLink>
</template>
