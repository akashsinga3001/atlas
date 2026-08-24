<template>
  <header class="sticky top-0 z-40 flex h-16 shrink-0 items-center justify-between border-b border-[var(--color-border)] bg-[var(--color-bg)]/80 px-6 backdrop-blur-md">
    <div class="flex items-center gap-8">
      <div class="flex items-center gap-2">
        <div class="icon-badge flex h-7 w-7 items-center justify-center rounded-[var(--radius-sm)]">
          <Activity :size="15" class="text-[var(--color-accent)]" />
        </div>
        <span class="text-sm font-semibold tracking-tight text-[var(--color-text-primary)]">Atlas</span>
      </div>
      <nav class="flex items-center gap-1">
        <router-link
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="flex items-center gap-1.5 rounded-[var(--radius-sm)] px-3 py-1.5 text-[13px] font-medium text-[var(--color-text-secondary)] transition-colors hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
          active-class="!bg-[var(--color-accent-bg)] !text-[var(--color-accent-hover)]"
        >
          <component :is="item.icon" :size="15" />
          {{ item.label }}
        </router-link>
      </nav>
    </div>
    <KillSwitchPill />
  </header>
</template>

<script>
import { Activity, LayoutDashboard, Layers, Settings2, TrendingUp, Wallet } from "@lucide/vue"
import KillSwitchPill from "./KillSwitchPill.vue"

export default {
  name: "TopNav",
  components: { Activity, KillSwitchPill },
  data() {
    return {
      navItems: [
        { to: "/", label: "Dashboard", icon: LayoutDashboard },
        { to: "/strategies", label: "Strategies", icon: Layers },
        { to: "/positions", label: "Positions", icon: Wallet },
        { to: "/performance", label: "Performance", icon: TrendingUp },
        { to: "/operations", label: "Operations", icon: Settings2 },
      ],
    }
  },
}
</script>
