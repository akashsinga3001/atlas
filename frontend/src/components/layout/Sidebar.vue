<template>
  <aside
    class="flex h-screen shrink-0 flex-col overflow-hidden border-r py-4 transition-[width] duration-200 ease-out"
    :style="{ background: 'var(--color-sidebar-bg)', borderColor: 'var(--color-sidebar-border)', width: collapsed ? 'var(--sidebar-width-collapsed)' : 'var(--sidebar-width)' }"
  >
    <div class="flex items-center px-4" :class="collapsed ? 'justify-center' : 'justify-between'">
      <div class="flex items-center gap-2">
        <div class="flex h-6 w-6 shrink-0 items-center justify-center rounded-[var(--radius-sm)] bg-white">
          <Activity :size="13" class="text-black" />
        </div>
        <span v-if="!collapsed" class="font-display whitespace-nowrap text-[14px] font-semibold tracking-tight text-white">Atlas</span>
      </div>
      <button
        v-if="!collapsed"
        type="button"
        class="flex h-6 w-6 shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-white/50 transition-colors hover:bg-white/10 hover:text-white"
        title="Collapse sidebar"
        @click="toggleCollapsed"
      >
        <ChevronsLeft :size="14" />
      </button>
    </div>
    <button
      v-if="collapsed"
      type="button"
      class="mx-auto mt-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-[var(--radius-sm)] text-white/50 transition-colors hover:bg-white/10 hover:text-white"
      title="Expand sidebar"
      @click="toggleCollapsed"
    >
      <ChevronsRight :size="14" />
    </button>

    <nav class="sidebar-nav flex min-h-0 flex-1 flex-col overflow-y-auto overflow-x-hidden py-1" :class="collapsed ? 'mt-1 items-center px-2' : 'mt-5 pl-3 pr-1.5'">
      <div
        v-for="(group, i) in navGroups"
        :key="group.label"
        class="w-full"
        :class="i > 0 ? 'mt-3 border-t pt-3' : ''"
        :style="i > 0 ? { borderColor: 'rgba(255, 255, 255, 0.1)' } : {}"
      >
        <p v-if="!collapsed" class="whitespace-nowrap px-2.5 text-[11px] font-semibold uppercase tracking-wide" style="color: rgba(255, 255, 255, 0.35)">{{ group.label }}</p>
        <div class="mt-1.5 flex flex-col gap-0.5" :class="collapsed ? 'items-center' : ''">
          <router-link
            v-for="item in group.items"
            :key="item.to"
            :to="item.to"
            :title="collapsed ? item.label : ''"
            class="flex items-center gap-2 whitespace-nowrap rounded-[var(--radius-sm)] text-[12.5px] font-medium transition-all duration-150"
            :class="[collapsed ? 'h-8 w-8 justify-center' : 'px-2.5 py-1.5 hover:translate-x-0.5', isActive(item.to) ? 'nav-item-active' : '']"
            :style="isActive(item.to) ? 'color: #ffffff' : `color: var(--color-sidebar-text)`"
          >
            <component :is="item.icon" :size="collapsed ? 18 : 14" class="shrink-0" />
            <span v-if="!collapsed">{{ item.label }}</span>
          </router-link>
        </div>
      </div>
    </nav>

    <div class="sidebar-footer mt-4 flex flex-col gap-2" :class="collapsed ? 'items-center px-2' : 'px-3'">
      <div
        class="flex items-center gap-2.5 rounded-[var(--radius-sm)]"
        :class="collapsed ? 'h-8 w-8 justify-center' : 'px-3 py-2.5'"
        style="background: rgba(255, 255, 255, 0.06)"
        :title="collapsed ? (killSwitchStore.isActive ? 'Entries blocked' : 'Trading active') : ''"
      >
        <span class="relative flex h-2 w-2 shrink-0 items-center justify-center" :style="{ color: killSwitchStore.isActive ? 'var(--color-risk-hot)' : 'var(--color-risk-calm)' }">
          <span class="pulse-dot absolute h-2 w-2 rounded-full bg-current" />
          <span class="h-2 w-2 rounded-full bg-current" />
        </span>
        <span v-if="!collapsed" class="truncate text-[11.5px] font-medium" style="color: rgba(255, 255, 255, 0.7)">{{ killSwitchStore.isActive ? "Entries blocked" : "Trading active" }}</span>
      </div>
      <button
        type="button"
        class="flex items-center justify-center gap-1.5 rounded-[var(--radius-sm)] text-[11.5px] font-medium transition-colors hover:bg-white/10"
        :class="collapsed ? 'h-8 w-8' : 'px-2.5 py-1.5'"
        style="border: 1px solid rgba(255, 255, 255, 0.14); color: rgba(255, 255, 255, 0.7)"
        :title="collapsed ? (isDark ? 'Light mode' : 'Dark mode') : ''"
        @click="toggleTheme"
      >
        <component :is="isDark ? Sun : Moon" :size="collapsed ? 16 : 13" class="shrink-0" />
        <span v-if="!collapsed">{{ isDark ? "Light mode" : "Dark mode" }}</span>
      </button>
    </div>
  </aside>
</template>

<script>
import { Activity, BarChart3, Boxes, ChevronsLeft, ChevronsRight, Cpu, Landmark, LayoutGrid, LineChart, ListChecks, Moon, Radar, Shield, Sun, TrendingUp } from "@lucide/vue"
import { useKillSwitchStore } from "@/stores/killSwitch"

export default {
  name: "Sidebar",
  components: { Activity, ChevronsLeft, ChevronsRight },
  data() {
    return {
      Moon,
      Sun,
      isDark: document.documentElement.getAttribute("data-theme") === "dark",
      collapsed: localStorage.getItem("atlas-sidebar-collapsed") === "true",
      navGroups: [
        { label: "Overview", items: [{ to: "/", label: "Overview", icon: LayoutGrid }] },
        {
          label: "Trading",
          items: [
            { to: "/trades", label: "Trades", icon: TrendingUp },
            { to: "/options", label: "Options", icon: Boxes },
            { to: "/signals", label: "Signals", icon: Radar },
          ],
        },
        { label: "Strategies", items: [{ to: "/strategies", label: "Strategies", icon: ListChecks }] },
        {
          label: "Portfolio",
          items: [
            { to: "/portfolio", label: "Portfolio", icon: LineChart },
            { to: "/fund", label: "Fund", icon: Landmark },
          ],
        },
        { label: "Market", items: [{ to: "/market", label: "Market", icon: BarChart3 }] },
        { label: "Risk", items: [{ to: "/risk", label: "Risk Controls", icon: Shield }] },
        {
          label: "Operations",
          items: [
            { to: "/operations/jobs", label: "Jobs", icon: Cpu },
            { to: "/operations/schedules", label: "Schedules", icon: Activity },
          ],
        },
        { label: "Data", items: [{ to: "/data-pipeline", label: "Data Pipeline", icon: Boxes }] },
      ],
    }
  },
  computed: {
    killSwitchStore() {
      return useKillSwitchStore()
    },
  },
  methods: {
    isActive(to) {
      return to === "/" ? this.$route.path === "/" : this.$route.path.startsWith(to)
    },
    toggleCollapsed() {
      this.collapsed = !this.collapsed
      localStorage.setItem("atlas-sidebar-collapsed", String(this.collapsed))
    },
    toggleTheme() {
      this.isDark = !this.isDark
      const theme = this.isDark ? "dark" : "light"
      document.documentElement.setAttribute("data-theme", theme)
      localStorage.setItem("atlas-theme", theme)
    },
  },
}
</script>

<style scoped>
nav a:hover {
  background: rgba(255, 255, 255, 0.08);
  color: #ffffff !important;
}

/* The selected nav item as a physical control: a lit edge indicator (the left accent) and a
   soft inner top highlight, instead of a flat color fill — the same top-left light source as
   the rest of the app, just against the sidebar's own always-dark surface. */
.nav-item-active {
  background: rgba(255, 255, 255, 0.1);
  box-shadow: inset 2px 0 0 #ffffff, inset 0 1px 0 rgba(255, 255, 255, 0.08);
}
.nav-item-active:hover {
  background: rgba(255, 255, 255, 0.14);
}

/* Both reserve the scrollbar's track width whether or not it's actually rendered, and both
   need it — .sidebar-nav alone left its content box ~8px narrower than .sidebar-footer's,
   so their centered icons (nav items vs. status/theme toggle) sat a few pixels out of
   alignment even with identical padding. Applying it to both keeps their content boxes the
   same width, and keeps nav's own icons from shifting left only when a scrollbar appears. */
.sidebar-nav,
.sidebar-footer {
  scrollbar-gutter: stable;
}

/* scrollbar-gutter only reserves space on a box whose overflow isn't visible — .sidebar-footer
   never actually scrolls, so it needs overflow:hidden (not auto) just to make the reservation
   apply, matching .sidebar-nav's real scrollable gutter without ever showing a scrollbar here. */
.sidebar-footer {
  overflow-y: hidden;
}
</style>
