<script setup lang="ts">
import TabLink from './components/TabLink.vue'
</script>

<template>
  <header class="cover">
    <RouterLink to="/" class="brand" aria-label="错题本首页">
      <svg viewBox="0 0 40 40" class="logo" aria-hidden="true">
        <rect x="7" y="4" width="26" height="32" rx="3" fill="#fffdf6" />
        <path d="M13 4v32" stroke="#e8a09a" stroke-width="1.6" />
        <path d="M17 14h12M17 21h12M17 28h8" stroke="#9fb7d0" stroke-width="1.6" stroke-linecap="round" />
        <path
          d="M19 9c7-3 13 1 12 7s-9 8-14 4"
          fill="none" stroke="#d0312d" stroke-width="2.2" stroke-linecap="round"
        />
      </svg>
      <span>错题本</span>
    </RouterLink>
  </header>

  <main class="page">
    <RouterView v-slot="{ Component }">
      <Transition name="page" mode="out-in">
        <component :is="Component" />
      </Transition>
    </RouterView>
  </main>

  <nav class="tabs" aria-label="主导航">
    <TabLink to="/">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M4 8h4l1.5-2.5h5L16 8h4v11H4z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
        <circle cx="12" cy="13" r="3.2" fill="none" stroke="currentColor" stroke-width="1.8" />
      </svg>
      录入
    </TabLink>
    <TabLink to="/mistakes">
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M6 3h12v18H6z" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round" />
        <path d="M10 8h5M10 12h5M10 16h3" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
      </svg>
      错题本
    </TabLink>
  </nav>
</template>
