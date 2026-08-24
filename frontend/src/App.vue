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
import { useKillSwitchStore } from "@/stores/killSwitch"

export default {
  name: "App",
  components: { AppShell },
  created() {
    useKillSwitchStore().fetch()
  },
}
</script>
