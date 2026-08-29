<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <BaseCard title="Market sentiment" :icon="Gauge">
      <template #header-actions>
        <StaleBadge :last-updated-at="marketStore.resource.lastUpdatedAt" :has-error="marketStore.resource.status === 'error'" />
      </template>
      <LoadingState v-if="marketStore.resource.status === 'loading'" />
      <ErrorState v-else-if="marketStore.resource.status === 'error' && !marketStore.resource.data" :message="marketStore.resource.error" @retry="marketStore.fetch" />
      <div v-else-if="marketStore.resource.data" class="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <SentimentGauge :score="marketStore.resource.data.regime_score" :label="marketStore.resource.data.label" :size="180" />
        <div class="grid grid-cols-2 gap-x-6 gap-y-4 lg:col-span-2 sm:grid-cols-3">
          <MetricTile label="Adv/Decl" :value="String(marketStore.resource.data.advance_decline_ratio ?? '—')" :tone="ratioTone(marketStore.resource.data.advance_decline_ratio, 1)" />
          <MetricTile label="% &gt; EMA20" :value="formatPct(marketStore.resource.data.pct_above_ema20)" :tone="ratioTone(marketStore.resource.data.pct_above_ema20, 50)" />
          <MetricTile label="% &gt; EMA50" :value="formatPct(marketStore.resource.data.pct_above_ema50)" :tone="ratioTone(marketStore.resource.data.pct_above_ema50, 50)" />
          <MetricTile label="% &gt; EMA200" :value="formatPct(marketStore.resource.data.pct_above_ema200)" :tone="ratioTone(marketStore.resource.data.pct_above_ema200, 50)" />
          <MetricTile label="New highs" :value="String(marketStore.resource.data.new_highs_count ?? '—')" tone="positive" />
          <MetricTile label="New lows" :value="String(marketStore.resource.data.new_lows_count ?? '—')" tone="negative" />
        </div>
      </div>
    </BaseCard>

    <BaseCard title="Sentiment history" :icon="LineChart">
      <LoadingState v-if="marketStore.history.status === 'loading'" />
      <EmptyState v-else-if="!marketStore.history.data?.length" title="No sentiment history yet" />
      <PriceChart v-else :series="historySeries" :height="220" />
    </BaseCard>
  </div>
</template>

<script>
import { Gauge, LineChart } from "@lucide/vue"
import { useMarketStore } from "@/stores/market"
import { usePageHeaderStore } from "@/stores/pageHeader"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import MetricTile from "@/components/primitives/MetricTile.vue"
import PriceChart from "@/components/primitives/PriceChart.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import SentimentGauge from "@/components/dashboard/SentimentGauge.vue"

export default {
  name: "MarketView",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, MetricTile, PriceChart, SentimentGauge, StaleBadge },
  data() {
    return { Gauge, LineChart }
  },
  computed: {
    marketStore() {
      return useMarketStore()
    },
    historySeries() {
      return [
        {
          name: "Regime score",
          color: "#2f5fd6",
          data: (this.marketStore.history.data ?? [])
            .filter((h) => h.regime_score !== null)
            .map((h) => ({ time: h.candle_timestamp.slice(0, 10), value: h.regime_score })),
        },
      ]
    },
  },
  created() {
    usePageHeaderStore().set("Market", "Broader market context for strategy decisions")
    if (this.marketStore.resource.status === "idle") this.marketStore.fetch()
  },
  methods: {
    formatPct(value) {
      return value === null || value === undefined ? "—" : `${value}%`
    },
    ratioTone(value, midpoint) {
      if (value === null || value === undefined) return "neutral"
      if (value > midpoint) return "positive"
      if (value < midpoint) return "negative"
      return "neutral"
    },
  },
}
</script>
