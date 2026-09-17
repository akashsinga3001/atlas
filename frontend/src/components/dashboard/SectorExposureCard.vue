<template>
  <BaseCard title="Sector Exposure" :icon="Layers" :padded="false">
    <template #header-actions>
      <StaleBadge :last-updated-at="resource.lastUpdatedAt" :has-error="resource.status === 'error'" />
    </template>
    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="$emit('retry')" />
    <EmptyState v-else-if="!resource.data || !resource.data.sectors.length" title="No open positions yet" description="Sector exposure will appear here once a strategy enters a position." />
    <div v-else class="flex h-full items-center justify-center gap-12 px-4 pb-4">
      <DonutChart :segments="donutSegments" :center-value="largestPct" center-label="Largest Sector" :size="200" class="shrink-0" />
      <div class="grid grid-cols-2 gap-x-8 gap-y-2.5">
        <div v-for="sector in resource.data.sectors" :key="sector.sector" class="flex items-center justify-between gap-3 text-[12px]">
          <span class="flex min-w-0 items-center gap-1.5 text-[var(--color-text-secondary)]">
            <span class="h-2 w-2 shrink-0 rounded-full" :style="{ background: colorFor(sector.sector) }" />
            <span class="truncate">{{ sector.sector }}</span>
          </span>
          <span class="font-mono-nums shrink-0 text-[var(--color-text-tertiary)]">{{ pct(sector.pct_of_nav) }}</span>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<script>
import { Layers } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import DonutChart from "@/components/primitives/DonutChart.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import { assignCategoricalColors } from "@/utils/categoricalColor"

export default {
  name: "SectorExposureCard",
  components: { BaseCard, DonutChart, EmptyState, ErrorState, LoadingState, StaleBadge },
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
    donutSegments() {
      return (this.resource.data?.sectors ?? []).map((s) => ({ label: s.sector, value: s.pct_of_nav ?? 0, color: this.colorFor(s.sector) }))
    },
    largestPct() {
      const largest = this.resource.data?.largest_sector
      return largest?.pct_of_nav !== null && largest?.pct_of_nav !== undefined ? `${largest.pct_of_nav}%` : "—"
    },
  },
  methods: {
    colorFor(sector) {
      return this.colorMap.get(sector)
    },
    pct(value) {
      return value !== null && value !== undefined ? `${value}%` : "—"
    },
  },
}
</script>
