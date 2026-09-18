<template>
  <BaseCard title="Sector Exposure" :icon="Layers" :padded="false">
    <template #header-actions>
      <StaleBadge :last-updated-at="resource.lastUpdatedAt" :has-error="resource.status === 'error'" />
    </template>
    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="$emit('retry')" />
    <EmptyState v-else-if="!resource.data || !resource.data.sectors.length" title="No open positions yet" description="Sector exposure will appear here once a strategy enters a position." />
    <div v-else class="flex h-full flex-col gap-3 px-4 pb-4">
      <!-- Concentration risk — a donut's center label only ever answered "largest sector"; this
           adds "largest single name," a distinct risk question a donut never surfaced. -->
      <div class="grid shrink-0 grid-cols-2 gap-2 text-center">
        <div class="rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] py-2">
          <p class="truncate px-1 text-[13px] font-semibold text-[var(--color-text-primary)]">{{ largestSectorPct }}</p>
          <p class="label-caps mt-0.5">{{ largestSectorName }}</p>
        </div>
        <div class="rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] py-2">
          <p class="truncate px-1 text-[13px] font-semibold text-[var(--color-text-primary)]">{{ largestPositionPct }}</p>
          <p class="label-caps mt-0.5">{{ largestPositionName }}</p>
        </div>
      </div>

      <!-- Ranked bars, not a donut: each row is flex-1, so the list fills the card's full
           stretched height whether there are 3 sectors or 9 — a donut+legend only ever used the
           top portion and left the rest of a tall sidebar blank. Bar width is relative to the
           largest sector (not an absolute 0-100 scale), so the top bar is always full-width
           instead of every bar being a tiny sliver. -->
      <div class="flex flex-1 flex-col divide-y divide-[var(--color-border)]">
        <div v-for="sector in resource.data.sectors" :key="sector.sector" class="flex flex-1 items-center gap-3 py-1.5">
          <div class="w-[104px] shrink-0">
            <p class="truncate text-[11.5px] text-[var(--color-text-secondary)]">{{ sector.sector }}</p>
            <p class="text-[10px] text-[var(--color-text-tertiary)]">{{ sector.position_count }} position{{ sector.position_count === 1 ? "" : "s" }}</p>
          </div>
          <div class="h-2 flex-1 overflow-hidden rounded-full bg-[var(--color-surface-alt)]">
            <div class="h-full rounded-full" :style="{ width: `${barWidth(sector.pct_of_nav)}%`, background: colorFor(sector.sector) }" />
          </div>
          <span class="font-mono-nums w-10 shrink-0 text-right text-[11.5px] text-[var(--color-text-tertiary)]">{{ pct(sector.pct_of_nav) }}</span>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<script>
import { Layers } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import { assignCategoricalColors } from "@/utils/categoricalColor"

export default {
  name: "SectorExposureCard",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, StaleBadge },
  props: {
    resource: {
      type: Object,
      required: true,
    },
  },
  emits: ["retry"],
  data() {
    return { Layers, isDark: document.documentElement.getAttribute("data-theme") === "dark" }
  },
  computed: {
    colorMap() {
      const sectors = this.resource.data?.sectors ?? []
      return assignCategoricalColors(
        sectors.map((s) => s.sector),
        this.isDark ? "dark" : "light",
      )
    },
    maxSectorPct() {
      return Math.max(...(this.resource.data?.sectors ?? []).map((s) => s.pct_of_nav ?? 0), 0)
    },
    largestSectorName() {
      return this.resource.data?.largest_sector?.sector ?? "Largest Sector"
    },
    largestSectorPct() {
      return this.pct(this.resource.data?.largest_sector?.pct_of_nav)
    },
    largestPositionName() {
      return this.resource.data?.largest_position?.ticker ?? "Largest Position"
    },
    largestPositionPct() {
      return this.pct(this.resource.data?.largest_position?.pct_of_nav)
    },
  },
  methods: {
    colorFor(sector) {
      return this.colorMap.get(sector)
    },
    pct(value) {
      return value !== null && value !== undefined ? `${value}%` : "—"
    },
    barWidth(value) {
      if (!value || !this.maxSectorPct) return 0
      return Math.max((value / this.maxSectorPct) * 100, 4)
    },
  },
}
</script>
