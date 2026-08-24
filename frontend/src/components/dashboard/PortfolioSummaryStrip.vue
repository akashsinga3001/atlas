<template>
  <BaseCard title="Portfolio summary" :icon="Wallet">
    <template #header-actions>
      <StaleBadge :last-updated-at="resource.lastUpdatedAt" :has-error="resource.status === 'error'" />
    </template>
    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="$emit('retry')" />
    <div v-else-if="resource.data">
      <div class="flex items-start justify-between">
        <div>
          <p class="label-caps">Total P&L</p>
          <p class="figure-hero mt-1.5 text-4xl" :class="pnlTextClass(resource.data.total_pnl)">
            {{ formatCurrency(resource.data.total_pnl, { compact: true }) }}
          </p>
          <p class="mt-1 text-xs font-medium" :class="pnlTextClass(resource.data.true_return_pct)">{{ formatPercent(resource.data.true_return_pct) }} true return</p>
        </div>
        <Sparkline v-if="pnlHistory.length > 1" :values="pnlHistory" :color="sparklineColor" :width="140" :height="44" />
      </div>
      <div class="mt-5 grid grid-cols-2 gap-4 border-t border-[var(--color-border)] pt-4 sm:grid-cols-2">
        <MetricTile label="Win rate" :value="resource.data.win_rate !== null ? `${resource.data.win_rate}%` : '—'" />
        <MetricTile label="Open trades" :value="String(resource.data.open_trades)" />
      </div>
    </div>
  </BaseCard>
</template>

<script>
import { Wallet } from "@lucide/vue"
import { useEquityCurveStore } from "@/stores/equityCurve"
import BaseCard from "@/components/primitives/BaseCard.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import MetricTile from "@/components/primitives/MetricTile.vue"
import Sparkline from "@/components/primitives/Sparkline.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import { formatCurrency, formatPercent, pnlTone } from "@/utils/format"

export default {
  name: "PortfolioSummaryStrip",
  components: { BaseCard, ErrorState, LoadingState, MetricTile, Sparkline, StaleBadge },
  props: {
    resource: {
      type: Object,
      required: true,
    },
  },
  emits: ["retry"],
  data() {
    return { Wallet }
  },
  computed: {
    curveStore() {
      return useEquityCurveStore()
    },
    pnlHistory() {
      return (this.curveStore.equity.data ?? []).map((p) => p.cumulative_pnl)
    },
    sparklineColor() {
      return this.resource.data && this.pnlTone(this.resource.data.total_pnl) === "negative" ? "#f2545c" : "#4ed08a"
    },
  },
  created() {
    if (this.curveStore.equity.status === "idle") this.curveStore.fetch()
  },
  methods: {
    formatCurrency,
    formatPercent,
    pnlTone,
    pnlTextClass(value) {
      const tone = this.pnlTone(value)
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return "text-[var(--color-text-primary)]"
    },
  },
}
</script>
