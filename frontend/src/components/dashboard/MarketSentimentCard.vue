<template>
  <BaseCard title="Market sentiment" :icon="Gauge">
    <template #header-actions>
      <StaleBadge :last-updated-at="resource.lastUpdatedAt" :has-error="resource.status === 'error'" />
    </template>
    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="$emit('retry')" />
    <EmptyState v-else-if="!resource.data" title="No sentiment data yet" />
    <div v-else>
      <div class="flex items-start justify-between gap-3">
        <SentimentGauge :score="resource.data.regime_score" :label="resource.data.label" :size="120" />
        <Sparkline v-if="scoreHistory.length > 1" :values="scoreHistory" color="#2f5fd6" :width="90" :height="28" />
      </div>
      <dl class="mt-4 grid grid-cols-4 gap-3 border-t border-[var(--color-border)] pt-3 text-xs">
        <div>
          <dt class="text-[var(--color-text-tertiary)]">Adv/Decl</dt>
          <dd class="font-mono-nums mt-1 font-medium" :class="ratioClass(resource.data.advance_decline_ratio, 1)">{{ resource.data.advance_decline_ratio ?? "—" }}</dd>
        </div>
        <div>
          <dt class="text-[var(--color-text-tertiary)]">% &gt; EMA50</dt>
          <dd class="font-mono-nums mt-1 font-medium" :class="ratioClass(resource.data.pct_above_ema50, 50)">{{ formatPct(resource.data.pct_above_ema50) }}</dd>
        </div>
        <div>
          <dt class="text-[var(--color-text-tertiary)]">New highs</dt>
          <dd class="font-mono-nums mt-1 font-medium text-[var(--color-positive)]">{{ resource.data.new_highs_count ?? "—" }}</dd>
        </div>
        <div>
          <dt class="text-[var(--color-text-tertiary)]">New lows</dt>
          <dd class="font-mono-nums mt-1 font-medium text-[var(--color-negative)]">{{ resource.data.new_lows_count ?? "—" }}</dd>
        </div>
      </dl>
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
