<template>
  <BaseCard title="Key Metrics" :icon="ListChecks">
    <template #header-actions>
      <StaleBadge :last-updated-at="lastUpdatedAt" :has-error="hasError" />
    </template>
    <LoadingState v-if="loading" />
    <div v-else class="flex flex-col divide-y divide-[var(--color-border)]">
      <div v-for="row in rows" :key="row.label" class="flex items-center justify-between py-2 first:pt-0 last:pb-0">
        <span class="text-[12px] text-[var(--color-text-secondary)]">{{ row.label }}</span>
        <div class="flex items-center gap-2">
          <div v-if="row.bar !== undefined" class="h-1.5 w-14 overflow-hidden rounded-full bg-[var(--color-surface-alt)]">
            <div class="h-full rounded-full bg-[var(--color-accent)]" :style="{ width: `${Math.min(row.bar, 100)}%` }" />
          </div>
          <span class="font-mono-nums text-[12.5px] font-semibold" :class="row.tone ? pnlClass(row.value) : 'text-[var(--color-text-primary)]'">{{ row.display }}</span>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<script>
import { ListChecks } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import { formatCurrency, pnlTone } from "@/utils/format"

export default {
  name: "KeyMetricsCard",
  components: { BaseCard, LoadingState, StaleBadge },
  props: {
    loading: { type: Boolean, default: false },
    lastUpdatedAt: { type: Number, default: null },
    hasError: { type: Boolean, default: false },
    nav: { type: Number, default: null },
    totalPnl: { type: Number, default: null },
    realizedToday: { type: Number, default: null },
    unrealizedNow: { type: Number, default: null },
    cash: { type: Number, default: null },
    deployed: { type: Number, default: null },
    positions: { type: Number, default: 0 },
    avgPositionAgeDays: { type: Number, default: null },
    utilizationPct: { type: Number, default: null },
  },
  data() {
    return { ListChecks }
  },
  computed: {
    rows() {
      return [
        { label: "NAV", display: formatCurrency(this.nav), value: null },
        { label: "Total P&L", display: formatCurrency(this.totalPnl, { signed: true }), value: this.totalPnl, tone: true },
        { label: "Realized P&L (today)", display: formatCurrency(this.realizedToday, { signed: true }), value: this.realizedToday, tone: true },
        { label: "Unrealized P&L", display: formatCurrency(this.unrealizedNow, { signed: true }), value: this.unrealizedNow, tone: true },
        { label: "Cash Balance", display: formatCurrency(this.cash), value: null },
        { label: "Deployed Capital", display: formatCurrency(this.deployed), value: null },
        { label: "Utilization", display: this.utilizationPct !== null ? `${this.utilizationPct.toFixed(1)}%` : "—", value: null, bar: this.utilizationPct ?? 0 },
        { label: "Positions", display: String(this.positions), value: null },
        { label: "Avg Position Age", display: this.avgPositionAgeDays !== null ? `${this.avgPositionAgeDays.toFixed(1)}d` : "—", value: null },
      ]
    },
  },
  methods: {
    pnlClass(value) {
      const tone = pnlTone(value)
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return "text-[var(--color-text-primary)]"
    },
  },
}
</script>
