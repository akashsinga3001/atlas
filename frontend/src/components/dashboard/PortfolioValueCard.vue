<template>
  <BaseCard title="Portfolio Value" :icon="LineChart">
    <template #header-actions>
      <StaleBadge :last-updated-at="lastUpdatedAt" :has-error="hasError" />
    </template>
    <LoadingState v-if="loading" />
    <div v-else class="flex h-full flex-col gap-4">
      <div class="flex shrink-0 flex-wrap items-start justify-between gap-4">
        <div>
          <p class="figure-hero text-2xl text-[var(--color-text-primary)]">{{ formatCurrency(nav, { compact: true }) }}</p>
          <p class="mt-1 text-[13px] font-medium" :class="pnlClass(todayDelta)">
            {{ todayDelta !== null ? formatCurrency(todayDelta, { compact: true, signed: true }) : "—" }}
            <span v-if="todayDeltaPct !== null">({{ formatPercent(todayDeltaPct) }})</span>
            <span class="text-[var(--color-text-tertiary)]">Today</span>
          </p>
        </div>
        <div class="flex items-start gap-5 text-right">
          <div>
            <p class="label-caps">Deployed</p>
            <p class="font-mono-nums mt-1 text-[13px] font-semibold text-[var(--color-text-primary)]">{{ formatCurrency(deployed, { compact: true }) }}</p>
            <p class="mt-0.5 text-[10.5px] text-[var(--color-text-tertiary)]">{{ pct(deployedPct) }}</p>
          </div>
          <div>
            <p class="label-caps">Cash</p>
            <p class="font-mono-nums mt-1 text-[13px] font-semibold text-[var(--color-text-primary)]">{{ formatCurrency(cash, { compact: true }) }}</p>
            <p class="mt-0.5 text-[10.5px] text-[var(--color-text-tertiary)]">{{ pct(cashPct) }}</p>
          </div>
          <div>
            <p class="label-caps">Positions</p>
            <p class="font-mono-nums mt-1 text-[13px] font-semibold text-[var(--color-text-primary)]">{{ positions }}</p>
            <p class="mt-0.5 text-[10.5px] text-[var(--color-text-tertiary)]">&nbsp;</p>
          </div>
        </div>
      </div>

      <div class="flex shrink-0 items-center justify-between">
        <TimeRangeTabs v-model="range" />
        <p v-if="range === '1D'" class="text-[10.5px] text-[var(--color-text-tertiary)]">Since dashboard opened today</p>
      </div>

      <EmptyState v-if="!chartSeries[0]?.data.length" class="flex-1" title="Not enough history to chart yet" />
      <PriceChart v-else class="min-h-0 flex-1" :series="chartSeries" fill :time-visible="range === '1D'" />
    </div>
  </BaseCard>
</template>

<script>
import { LineChart } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import PriceChart from "@/components/primitives/PriceChart.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import TimeRangeTabs from "@/components/primitives/TimeRangeTabs.vue"
import { formatCurrency, formatPercent, pnlTone } from "@/utils/format"

const RANGE_DAYS = { "1W": 7, "1M": 30, "3M": 90 }

export default {
  name: "PortfolioValueCard",
  components: { BaseCard, EmptyState, LoadingState, PriceChart, StaleBadge, TimeRangeTabs },
  props: {
    loading: { type: Boolean, default: false },
    lastUpdatedAt: { type: Number, default: null },
    hasError: { type: Boolean, default: false },
    nav: { type: Number, default: null },
    cash: { type: Number, default: null },
    deployed: { type: Number, default: null },
    positions: { type: Number, default: 0 },
    todayDelta: { type: Number, default: null },
    todayDeltaPct: { type: Number, default: null },
    navSeries: { type: Array, default: () => [] }, // [{date, total_value}] daily, from the existing NAV curve
    intradayPoints: { type: Array, default: () => [] }, // [{time (ms), value}] from the client-side intraday buffer
  },
  data() {
    return { LineChart, range: "1D" }
  },
  computed: {
    cashPct() {
      return this.nav ? (this.cash / this.nav) * 100 : null
    },
    deployedPct() {
      return this.nav ? (this.deployed / this.nav) * 100 : null
    },
    chartSeries() {
      if (this.range === "1D") {
        return [{ name: "Portfolio value", color: "#1f8a5c", area: true, data: this.intradayPoints.map((p) => ({ time: Math.floor(p.time / 1000), value: p.value })) }]
      }
      const days = RANGE_DAYS[this.range]
      let points = this.navSeries
      if (days) {
        const cutoff = new Date()
        cutoff.setDate(cutoff.getDate() - days)
        points = points.filter((p) => new Date(p.date) >= cutoff)
      } else if (this.range === "YTD") {
        const jan1 = new Date(new Date().getFullYear(), 0, 1)
        points = points.filter((p) => new Date(p.date) >= jan1)
      }
      return [{ name: "Portfolio value", color: "#1f8a5c", area: true, data: points.map((p) => ({ time: p.date, value: p.total_value })) }]
    },
  },
  methods: {
    formatCurrency,
    formatPercent,
    pct(value) {
      return value !== null && value !== undefined ? `${value.toFixed(1)}%` : "—"
    },
    pnlClass(value) {
      const tone = pnlTone(value)
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return "text-[var(--color-text-secondary)]"
    },
  },
}
</script>
