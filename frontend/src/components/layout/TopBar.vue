<template>
  <header class="glass relative z-20 flex h-[var(--topbar-height)] shrink-0 items-center justify-between border-b px-6" style="box-shadow: 0 1px 0 var(--color-border), 0 4px 12px -8px rgba(16, 19, 24, 0.15)">
    <div class="flex min-w-0 flex-col justify-center gap-0.5">
      <h1 class="font-display truncate text-[15.5px] font-semibold leading-none tracking-tight text-[var(--color-text-primary)]">{{ pageHeaderStore.title }}</h1>
      <p v-if="pageHeaderStore.subtitle" class="truncate text-[11.5px] leading-none text-[var(--color-text-tertiary)]">{{ pageHeaderStore.subtitle }}</p>
    </div>

    <div class="flex shrink-0 items-center gap-2.5">
      <div class="relative">
        <Search :size="13" class="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--color-text-tertiary)]" />
        <input
          v-model="query"
          type="text"
          placeholder="Search strategies…"
          class="h-8 w-56 rounded-[var(--radius-sm)] border border-[var(--color-border)] bg-[var(--color-surface-alt)] pl-8 pr-3 text-[12px] text-[var(--color-text-primary)] outline-none transition-all duration-150 placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent)] focus:bg-[var(--color-surface)] focus:ring-4 focus:ring-[var(--color-accent-bg)]"
          @focus="showResults = true"
          @blur="onBlur"
        />
        <div
          v-if="showResults && query && results.length"
          class="absolute right-0 top-10 z-30 w-64 overflow-hidden rounded-[var(--radius-base)] border border-[var(--color-border)] bg-[var(--color-overlay)]"
          style="box-shadow: var(--shadow-overlay)"
        >
          <router-link
            v-for="r in results"
            :key="r.to"
            :to="r.to"
            class="flex items-center justify-between px-3 py-2 text-[12.5px] text-[var(--color-text-primary)] transition-colors hover:bg-[var(--color-surface-hover)]"
            @mousedown.prevent="navigate(r.to)"
          >
            <span>{{ r.label }}</span>
            <span class="label-caps">{{ r.type }}</span>
          </router-link>
        </div>
      </div>

      <div class="mx-0.5 h-5 w-px" style="background: var(--color-border)" />

      <router-link
        to="/risk"
        class="flex h-8 items-center gap-1.5 rounded-[var(--radius-sm)] border px-3 text-[12px] font-medium transition-all duration-150"
        :class="killSwitchStore.isActive ? 'border-[var(--color-error-border)] bg-[var(--color-error-bg)] text-[var(--color-error)]' : 'border-[var(--color-border)] text-[var(--color-text-secondary)] hover:border-[var(--color-border-strong)] hover:text-[var(--color-text-primary)]'"
      >
        <span class="relative flex h-1.5 w-1.5 items-center justify-center" :style="{ color: killSwitchStore.isActive ? 'var(--color-risk-hot)' : 'var(--color-risk-calm)' }">
          <span v-if="!killSwitchStore.isActive" class="pulse-dot absolute h-1.5 w-1.5 rounded-full bg-current" />
          <span class="h-1.5 w-1.5 rounded-full bg-current" />
        </span>
        {{ killSwitchStore.isActive ? "Entries blocked" : "Live" }}
      </router-link>

      <div class="relative">
        <button
          type="button"
          class="relative flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] text-[var(--color-text-secondary)] transition-all duration-150 hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]"
          @click="showNotifications = !showNotifications"
        >
          <Bell :size="15" />
          <span v-if="attentionItems.length > 0" class="absolute right-1.5 top-1.5 h-1.5 w-1.5 rounded-full ring-2 ring-[var(--color-surface)]" style="background: var(--color-error)" />
        </button>
        <div v-if="showNotifications" class="absolute right-0 top-10 z-30 w-72 overflow-hidden rounded-[var(--radius-base)] border border-[var(--color-border)] bg-[var(--color-overlay)]" style="box-shadow: var(--shadow-overlay)" @click.self="showNotifications = false">
          <p class="label-caps px-3 py-2.5">Alerts</p>
          <div v-if="!attentionItems.length" class="px-3 pb-3 text-[12px] text-[var(--color-text-tertiary)]">Nothing needs attention right now.</div>
          <div v-else class="flex flex-col divide-y divide-[var(--color-border)]">
            <div v-for="item in attentionItems" :key="item.id" class="px-3 py-2.5 text-[12px]" :class="item.tone === 'error' ? 'text-[var(--color-error)]' : 'text-[var(--color-warning)]'">
              {{ item.message }}
            </div>
          </div>
        </div>
      </div>
    </div>
  </header>
</template>

<script>
import { Bell, Search } from "@lucide/vue"
import { useDashboardStore } from "@/stores/dashboard"
import { useKillSwitchStore } from "@/stores/killSwitch"
import { usePageHeaderStore } from "@/stores/pageHeader"
import { useStrategiesStore } from "@/stores/strategies"

export default {
  name: "TopBar",
  components: { Bell, Search },
  data() {
    return { query: "", showResults: false, showNotifications: false }
  },
  computed: {
    killSwitchStore() {
      return useKillSwitchStore()
    },
    pageHeaderStore() {
      return usePageHeaderStore()
    },
    strategiesStore() {
      return useStrategiesStore()
    },
    attentionItems() {
      return useDashboardStore().attentionItems
    },
    results() {
      if (!this.query.trim()) return []
      const q = this.query.trim().toLowerCase()
      return (this.strategiesStore.resource.data ?? [])
        .filter((s) => s.name.toLowerCase().includes(q) || s.code.toLowerCase().includes(q))
        .map((s) => ({ to: `/strategies/${s.id}`, label: s.name, type: "Strategy" }))
        .slice(0, 6)
    },
  },
  created() {
    if (this.strategiesStore.resource.status === "idle") this.strategiesStore.fetch()
  },
  methods: {
    onBlur() {
      setTimeout(() => {
        this.showResults = false
      }, 120)
    },
    navigate(to) {
      this.query = ""
      this.$router.push(to)
    },
  },
}
</script>
