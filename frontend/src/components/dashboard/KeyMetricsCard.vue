<template>
  <BaseCard title="Performance" :icon="Award">
    <template #header-actions>
      <StaleBadge :last-updated-at="lastUpdatedAt" :has-error="hasError" />
    </template>
    <LoadingState v-if="loading" />
    <div v-else class="flex flex-col divide-y divide-[var(--color-border)]">
      <div v-for="row in rows" :key="row.label" class="flex items-center justify-between py-2 first:pt-0 last:pb-0">
        <span class="text-[12px] text-[var(--color-text-secondary)]">{{ row.label }}</span>
        <span class="font-mono-nums text-[12.5px] font-semibold" :class="toneClass(row.tone)">{{ row.display }}</span>
      </div>
    </div>
  </BaseCard>
</template>

<script>
import { Award } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import { pnlTone } from "@/utils/format"

export default {
  name: "KeyMetricsCard",
  components: { BaseCard, LoadingState, StaleBadge },
  props: {
    loading: { type: Boolean, default: false },
    lastUpdatedAt: { type: Number, default: null },
    hasError: { type: Boolean, default: false },
    // All sourced from PortfolioStats (usePortfolioStatsStore) — trade-level performance/edge
    // figures, deliberately distinct from the live NAV/cash/deployed numbers Portfolio Value and
    // Today's P&L already show. This card answers "is my edge real," not "where do I stand."
    trueReturnPct: { type: Number, default: null },
    winRate: { type: Number, default: null },
    profitFactor: { type: Number, default: null },
    sharpeRatio: { type: Number, default: null },
    maxDrawdownPct: { type: Number, default: null },
    avgWinPct: { type: Number, default: null },
    avgLossPct: { type: Number, default: null },
    avgHoldingDays: { type: Number, default: null },
    closedTrades: { type: Number, default: 0 },
  },
  data() {
    return { Award }
  },
  computed: {
    rows() {
      return [
        { label: "True Return", display: this.pct(this.trueReturnPct), tone: this.toneFromValue(this.trueReturnPct) },
        { label: "Win Rate", display: this.pct(this.winRate), tone: null },
        { label: "Profit Factor", display: this.num(this.profitFactor), tone: null },
        { label: "Sharpe Ratio", display: this.num(this.sharpeRatio), tone: null },
        { label: "Max Drawdown", display: this.maxDrawdownPct !== null ? `-${this.maxDrawdownPct}%` : "—", tone: "negative" },
        { label: "Avg Win", display: this.pct(this.avgWinPct), tone: this.avgWinPct !== null ? "positive" : null },
        { label: "Avg Loss", display: this.pct(this.avgLossPct), tone: this.avgLossPct !== null ? "negative" : null },
        { label: "Avg Holding", display: this.avgHoldingDays !== null ? `${this.avgHoldingDays}d` : "—", tone: null },
        { label: "Closed Trades", display: String(this.closedTrades), tone: null },
      ]
    },
  },
  methods: {
    pct(value) {
      return value !== null && value !== undefined ? `${value}%` : "—"
    },
    num(value) {
      return value !== null && value !== undefined ? String(value) : "—"
    },
    toneFromValue(value) {
      const tone = pnlTone(value)
      return tone === "inactive" ? null : tone
    },
    toneClass(tone) {
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return "text-[var(--color-text-primary)]"
    },
  },
}
</script>
