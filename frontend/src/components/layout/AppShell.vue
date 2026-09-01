<template>
  <div class="flex h-screen overflow-hidden">
    <Sidebar />
    <div class="flex min-w-0 flex-1 flex-col overflow-hidden">
      <TopBar />
      <main class="flex-1 overflow-y-auto px-6 py-5">
        <slot />
      </main>
    </div>
  </div>
</template>

<script>
import Sidebar from "./Sidebar.vue"
import TopBar from "./TopBar.vue"

export default {
  name: "AppShell",
  components: { Sidebar, TopBar },
}
</script>
