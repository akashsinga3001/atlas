<template>
  <BaseCard title="Today's P&L" :icon="TrendingUp">
    <template #header-actions>
      <StaleBadge :last-updated-at="lastUpdatedAt" :has-error="hasError" />
    </template>
    <LoadingState v-if="loading" />
    <div v-else class="flex h-full flex-col gap-3">
      <p class="figure-hero shrink-0 text-2xl" :class="pnlClass(total)">{{ total !== null ? formatCurrency(total, { compact: true, signed: true }) : "—" }}</p>

      <EmptyState v-if="!barData.length" class="flex-1" title="Building up today's chart" description="Bars fill in as the dashboard stays open." />
      <BarChart v-else class="min-h-0 flex-1" :data="barData" fill time-visible />

      <div class="grid shrink-0 grid-cols-3 gap-2 text-center">
        <div class="rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] py-2">
          <p class="font-mono-nums text-[15px] font-semibold text-[var(--color-positive)]">{{ winners }}</p>
          <p class="label-caps mt-0.5">Winners</p>
        </div>
        <div class="rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] py-2">
          <p class="font-mono-nums text-[15px] font-semibold text-[var(--color-negative)]">{{ losers }}</p>
          <p class="label-caps mt-0.5">Losers</p>
        </div>
        <div class="rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] py-2">
          <p class="font-mono-nums text-[15px] font-semibold text-[var(--color-text-primary)]">{{ breakeven }}</p>
          <p class="label-caps mt-0.5">Breakeven</p>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<script>
import { TrendingUp } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import BarChart from "@/components/primitives/BarChart.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import { formatCurrency, pnlTone } from "@/utils/format"

export default {
  name: "TodaysPnlCard",
  components: { BaseCard, BarChart, EmptyState, LoadingState, StaleBadge },
  props: {
    loading: { type: Boolean, default: false },
    lastUpdatedAt: { type: Number, default: null },
    hasError: { type: Boolean, default: false },
    total: { type: Number, default: null },
    winners: { type: Number, default: 0 },
    losers: { type: Number, default: 0 },
    breakeven: { type: Number, default: 0 },
    intradayPoints: { type: Array, default: () => [] }, // [{time (ms), value}]
  },
  data() {
    return { TrendingUp }
  },
  computed: {
    // Bar = P&L movement between consecutive buffered points, not the account value itself —
    // this is what makes it read as "today's P&L over time" rather than a second NAV line.
    barData() {
      const points = this.intradayPoints
      if (points.length < 2) return []
      const bars = []
      for (let i = 1; i < points.length; i++) {
        bars.push({ time: Math.floor(points[i].time / 1000), value: points[i].value - points[i - 1].value })
      }
      return bars
    },
  },
  methods: {
    formatCurrency,
    pnlClass(value) {
      const tone = pnlTone(value)
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return "text-[var(--color-text-primary)]"
    },
  },
}
</script>
