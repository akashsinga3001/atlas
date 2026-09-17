<template>
  <BaseCard title="Market sentiment" :icon="Gauge">
    <template #header-actions>
      <StaleBadge :last-updated-at="resource.lastUpdatedAt" :has-error="resource.status === 'error'" />
    </template>
    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="$emit('retry')" />
    <EmptyState v-else-if="!resource.data" class="h-full" title="No sentiment data yet" />
    <div v-else class="flex h-full flex-col gap-4">
      <div class="flex flex-1 items-center justify-around gap-6">
        <SentimentGauge :score="resource.data.regime_score" :label="resource.data.label" :size="200" />
        <div v-if="scoreHistory.length > 1" class="flex flex-1 flex-col items-center gap-2">
          <p class="label-caps">Regime trend</p>
          <Sparkline :values="scoreHistory" color="#2f5fd6" :width="220" :height="72" />
        </div>
      </div>
      <div class="grid shrink-0 grid-cols-4 gap-2 text-center">
        <div class="rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] py-2">
          <p class="font-mono-nums text-[15px] font-semibold" :class="ratioClass(resource.data.advance_decline_ratio, 1)">{{ resource.data.advance_decline_ratio ?? "—" }}</p>
          <p class="label-caps mt-0.5">Adv/Decl</p>
        </div>
        <div class="rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] py-2">
          <p class="font-mono-nums text-[15px] font-semibold" :class="ratioClass(resource.data.pct_above_ema50, 50)">{{ formatPct(resource.data.pct_above_ema50) }}</p>
          <p class="label-caps mt-0.5">% &gt; EMA50</p>
        </div>
        <div class="rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] py-2">
          <p class="font-mono-nums text-[15px] font-semibold text-[var(--color-positive)]">{{ resource.data.new_highs_count ?? "—" }}</p>
          <p class="label-caps mt-0.5">New highs</p>
        </div>
        <div class="rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] py-2">
          <p class="font-mono-nums text-[15px] font-semibold text-[var(--color-negative)]">{{ resource.data.new_lows_count ?? "—" }}</p>
          <p class="label-caps mt-0.5">New lows</p>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<script>
import { Gauge } from "@lucide/vue"
import { useMarketStore } from "@/stores/market"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import Sparkline from "@/components/primitives/Sparkline.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import SentimentGauge from "@/components/dashboard/SentimentGauge.vue"

export default {
  name: "MarketSentimentCard",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, SentimentGauge, Sparkline, StaleBadge },
  props: {
    resource: {
      type: Object,
      required: true,
    },
  },
  emits: ["retry"],
  data() {
    return { Gauge }
  },
  computed: {
    scoreHistory() {
      return useMarketStore().scoreHistory
    },
  },
  methods: {
    formatPct(value) {
      return value === null || value === undefined ? "—" : `${value}%`
    },
    ratioClass(value, midpoint) {
      if (value === null || value === undefined) return ""
      if (value > midpoint) return "text-[var(--color-positive)]"
      if (value < midpoint) return "text-[var(--color-negative)]"
      return ""
    },
  },
}
</script>
