<template>
  <header class="topbar">
    <h1>错题本</h1>
    <nav>
      <RouterLink to="/">录入</RouterLink>
      <RouterLink to="/mistakes">错题本</RouterLink>
    </nav>
  </header>
  <main class="page">
    <RouterView />
  </main>
</template>
