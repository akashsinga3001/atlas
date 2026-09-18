<template>
  <AppShell>
    <!-- A <transition>-wrapped router-view was tried here for a page-fade on navigation, but
         combined with this app's lazy-loaded (async) route components it left the screen
         permanently stuck on the previous page after a real URL change — reproduced twice,
         with and without mode="out-in". Reverted: correctness over a decorative transition. -->
    <router-view />
  </AppShell>
</template>

<script>
import AppShell from "@/components/layout/AppShell.vue"
import { useCircuitBreakersStore } from "@/stores/circuitBreakers"
import { useKillSwitchStore } from "@/stores/killSwitch"

const POLL_INTERVAL_MS = 30_000

export default {
  name: "App",
  components: { AppShell },
  data() {
    return { pollHandle: null }
  },
  created() {
    // Kill switch / circuit breaker state drives the always-visible TopBar pill and Sidebar
    // status dot on every page, not just Overview/Risk — those two views also poll this data on
    // their own 30s timers, but only while mounted. Without a poll here too, navigating away from
    // both leaves this app-shell chrome frozen on whatever it last saw, looking solid and current
    // when it may be stale by however long the user stays on another page.
    useKillSwitchStore().fetch()
    useCircuitBreakersStore().fetch()
    this.pollHandle = setInterval(() => {
      useKillSwitchStore().fetch()
      useCircuitBreakersStore().fetch()
    }, POLL_INTERVAL_MS)
  },
  beforeUnmount() {
    if (this.pollHandle) clearInterval(this.pollHandle)
  },
}
</script>
