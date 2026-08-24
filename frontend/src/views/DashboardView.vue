<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <div class="flex items-center justify-between">
      <h1 class="text-lg font-semibold">System overview</h1>
      <StaleBadge :last-updated-at="strategiesStore.resource.lastUpdatedAt" :threshold-ms="90_000" :has-error="strategiesStore.resource.status === 'error'" />
    </div>

    <PortfolioSummaryStrip :resource="portfolioStatsStore.resource" @retry="refreshAll" />

    <AttentionFeed :items="dashboardStore.attentionItems" />

    <div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
      <div class="xl:col-span-2">
        <StrategyStatusGrid :resource="strategiesStore.resource" @retry="refreshAll" />
      </div>
      <div class="flex flex-col gap-4">
        <SystemHealthCard />
        <MarketSentimentCard :resource="marketStore.resource" @retry="refreshAll" />
        <CapitalAllocationCard :resource="capitalAllocationStore.resource" @retry="refreshAll" />
      </div>
    </div>
  </div>
</template>

<script>
import { useCapitalAllocationStore } from "@/stores/capitalAllocation"
import { useDashboardStore } from "@/stores/dashboard"
import { useMarketStore } from "@/stores/market"
import { usePortfolioStatsStore } from "@/stores/portfolioStats"
import { useStrategiesStore } from "@/stores/strategies"

import AttentionFeed from "@/components/dashboard/AttentionFeed.vue"
import CapitalAllocationCard from "@/components/dashboard/CapitalAllocationCard.vue"
import MarketSentimentCard from "@/components/dashboard/MarketSentimentCard.vue"
import PortfolioSummaryStrip from "@/components/dashboard/PortfolioSummaryStrip.vue"
import StrategyStatusGrid from "@/components/dashboard/StrategyStatusGrid.vue"
import SystemHealthCard from "@/components/dashboard/SystemHealthCard.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"

const REFRESH_INTERVAL_MS = 30_000

export default {
  name: "DashboardView",
  components: { AttentionFeed, CapitalAllocationCard, MarketSentimentCard, PortfolioSummaryStrip, StaleBadge, StrategyStatusGrid, SystemHealthCard },
  data() {
    return {
      refreshHandle: null,
    }
  },
  computed: {
    dashboardStore() {
      return useDashboardStore()
    },
    strategiesStore() {
      return useStrategiesStore()
    },
    marketStore() {
      return useMarketStore()
    },
    capitalAllocationStore() {
      return useCapitalAllocationStore()
    },
    portfolioStatsStore() {
      return usePortfolioStatsStore()
    },
  },
  created() {
    this.refreshAll()
    this.refreshHandle = setInterval(this.refreshAll, REFRESH_INTERVAL_MS)
  },
  beforeUnmount() {
    if (this.refreshHandle) clearInterval(this.refreshHandle)
  },
  methods: {
    refreshAll() {
      this.dashboardStore.fetchAll()
    },
  },
}
</script>
