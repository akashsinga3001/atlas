<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <BaseCard title="Performance" :icon="LineChart">
      <template #header-actions>
        <StaleBadge :last-updated-at="statsStore.resource.lastUpdatedAt" :has-error="statsStore.resource.status === 'error'" />
      </template>
      <LoadingState v-if="statsStore.resource.status === 'loading'" />
      <ErrorState v-else-if="statsStore.resource.status === 'error' && !statsStore.resource.data" :message="statsStore.resource.error" @retry="statsStore.fetch" />
      <div v-else-if="statsStore.resource.data" class="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4 lg:grid-cols-6">
        <MetricTile label="Total P&amp;L" :value="formatCurrency(statsStore.resource.data.total_pnl, { compact: true })" :tone="tileTone(statsStore.resource.data.total_pnl)" />
        <MetricTile label="True return" :value="formatPercent(statsStore.resource.data.true_return_pct)" :tone="tileTone(statsStore.resource.data.true_return_pct)" />
        <MetricTile label="Win rate" :value="pct(statsStore.resource.data.win_rate)" />
        <MetricTile label="Sharpe" :value="num(statsStore.resource.data.sharpe_ratio)" />
        <MetricTile label="Max drawdown" :value="pct(statsStore.resource.data.max_drawdown_pct)" tone="negative" />
        <MetricTile label="Profit factor" :value="num(statsStore.resource.data.profit_factor)" />
        <MetricTile label="Avg win" :value="formatPercent(statsStore.resource.data.avg_win_pct)" tone="positive" />
        <MetricTile label="Avg loss" :value="formatPercent(statsStore.resource.data.avg_loss_pct)" tone="negative" />
        <MetricTile label="Best trade" :value="formatPercent(statsStore.resource.data.best_trade_pct)" tone="positive" />
        <MetricTile label="Worst trade" :value="formatPercent(statsStore.resource.data.worst_trade_pct)" tone="negative" />
        <MetricTile label="Avg hold" :value="statsStore.resource.data.avg_holding_days !== null ? `${statsStore.resource.data.avg_holding_days}d` : '—'" />
        <MetricTile label="Total trades" :value="String(statsStore.resource.data.total_trades)" />
      </div>
    </BaseCard>

    <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <BaseCard title="Equity curve" :icon="TrendingUp">
        <LoadingState v-if="curveStore.equity.status === 'loading'" />
        <ErrorState v-else-if="curveStore.equity.status === 'error' && !curveStore.equity.data" :message="curveStore.equity.error" @retry="curveStore.fetch" />
        <EmptyState v-else-if="!curveStore.equity.data?.length" title="No closed trades yet" />
        <PriceChart v-else :series="equitySeries" :height="200" />
      </BaseCard>

      <BaseCard title="NAV curve" :icon="LineChart">
        <LoadingState v-if="curveStore.nav.status === 'loading'" />
        <ErrorState v-else-if="curveStore.nav.status === 'error' && !curveStore.nav.data" :message="curveStore.nav.error" @retry="curveStore.fetch" />
        <EmptyState v-else-if="!curveStore.nav.data?.length" title="No account snapshots yet" />
        <PriceChart v-else :series="navSeries" :height="200" />
      </BaseCard>
    </div>

    <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <BaseCard title="Return distribution" :icon="BarChart2">
        <LoadingState v-if="analyticsStore.resource.status === 'loading'" />
        <ErrorState v-else-if="analyticsStore.resource.status === 'error' && !analyticsStore.resource.data" :message="analyticsStore.resource.error" @retry="analyticsStore.fetch" />
        <ReturnDistributionChart v-else-if="analyticsStore.resource.data" :buckets="analyticsStore.resource.data.return_distribution" />
      </BaseCard>

      <BaseCard title="Sector performance" :icon="PieChart">
        <LoadingState v-if="analyticsStore.resource.status === 'loading'" />
        <ErrorState v-else-if="analyticsStore.resource.status === 'error' && !analyticsStore.resource.data" :message="analyticsStore.resource.error" @retry="analyticsStore.fetch" />
        <EmptyState v-else-if="!analyticsStore.resource.data?.sector_performance.length" title="No sector data yet" />
        <SectorPerformanceList v-else :sectors="analyticsStore.resource.data.sector_performance" />
      </BaseCard>
    </div>

    <CapitalAllocationCard :resource="capitalStore.resource" @retry="capitalStore.fetch" />
  </div>
</template>

<script>
import { BarChart2, LineChart, PieChart, TrendingUp } from "@lucide/vue"
import { useCapitalAllocationStore } from "@/stores/capitalAllocation"
import { useEquityCurveStore } from "@/stores/equityCurve"
import { usePageHeaderStore } from "@/stores/pageHeader"
import { usePortfolioAnalyticsStore } from "@/stores/portfolioAnalytics"
import { usePortfolioStatsStore } from "@/stores/portfolioStats"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import MetricTile from "@/components/primitives/MetricTile.vue"
import PriceChart from "@/components/primitives/PriceChart.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import CapitalAllocationCard from "@/components/dashboard/CapitalAllocationCard.vue"
import ReturnDistributionChart from "@/components/performance/ReturnDistributionChart.vue"
import SectorPerformanceList from "@/components/performance/SectorPerformanceList.vue"
import { formatCurrency, formatPercent, pnlTone } from "@/utils/format"

export default {
  name: "PortfolioView",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, MetricTile, PriceChart, StaleBadge, CapitalAllocationCard, ReturnDistributionChart, SectorPerformanceList },
  data() {
    return { BarChart2, LineChart, PieChart, TrendingUp }
  },
  computed: {
    statsStore() {
      return usePortfolioStatsStore()
    },
    curveStore() {
      return useEquityCurveStore()
    },
    analyticsStore() {
      return usePortfolioAnalyticsStore()
    },
    capitalStore() {
      return useCapitalAllocationStore()
    },
    equitySeries() {
      return [{ name: "Cumulative P&L", color: "#1f8a5c", data: (this.curveStore.equity.data ?? []).map((p) => ({ time: p.date, value: p.cumulative_pnl })) }]
    },
    navSeries() {
      return [{ name: "Account value", color: "#2f5fd6", data: (this.curveStore.nav.data ?? []).map((p) => ({ time: p.date, value: p.total_value })) }]
    },
  },
  created() {
    usePageHeaderStore().set("Portfolio", "Performance analytics workspace")
    this.statsStore.fetch()
    this.curveStore.fetch()
    this.analyticsStore.fetch()
    if (this.capitalStore.resource.status === "idle") this.capitalStore.fetch()
  },
  methods: {
    formatCurrency,
    formatPercent,
    pct(value) {
      return value !== null && value !== undefined ? `${value}%` : "—"
    },
    num(value) {
      return value !== null && value !== undefined ? String(value) : "—"
    },
    tileTone(value) {
      const tone = pnlTone(value)
      return tone === "inactive" ? "neutral" : tone
    },
  },
}
</script>
