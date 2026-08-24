<template>
  <div class="flex h-screen flex-col overflow-hidden bg-[var(--color-bg)]">
    <TopNav />
    <RiskGauge />
    <main class="flex-1 overflow-y-auto px-8 py-8">
      <slot />
    </main>
  </div>
</template>

<script>
import RiskGauge from "./RiskGauge.vue"
import TopNav from "./TopNav.vue"

export default {
  name: "AppShell",
  components: { TopNav, RiskGauge },
}
</script>
