<template>
  <div class="flex h-screen overflow-hidden bg-[var(--color-bg)]">
    <Suspense>
      <AmbientBackground />
    </Suspense>
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
import { defineAsyncComponent } from "vue"
import Sidebar from "./Sidebar.vue"
import TopBar from "./TopBar.vue"

// Loaded as its own chunk, after the app shell — three.js is a purely decorative addition and
// shouldn't hold up the critical-path bundle for a dense data application.
const AmbientBackground = defineAsyncComponent(() => import("./AmbientBackground.vue"))

export default {
  name: "AppShell",
  components: { AmbientBackground, Sidebar, TopBar },
}
</script>
