<template>
  <BaseCard title="Market sentiment" :icon="Gauge">
    <template #header-actions>
      <StaleBadge :last-updated-at="resource.lastUpdatedAt" :has-error="resource.status === 'error'" />
    </template>
    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="$emit('retry')" />
    <EmptyState v-else-if="!resource.data" title="No sentiment data yet" />
    <div v-else>
      <div class="flex items-start justify-between">
        <div>
          <p class="figure-hero text-2xl text-[var(--color-text-primary)]">{{ resource.data.regime_score ?? "—" }}</p>
          <p class="mt-1 text-xs font-medium text-[var(--color-text-secondary)]">{{ resource.data.label ?? "Unknown" }}</p>
        </div>
        <Sparkline v-if="scoreHistory.length > 1" :values="scoreHistory" color="#2f5fd6" :width="100" :height="32" />
      </div>
      <dl class="mt-4 grid grid-cols-4 gap-3 border-t border-[var(--color-border)] pt-3 text-xs">
        <div>
          <dt class="text-[var(--color-text-tertiary)]">Adv/Decl</dt>
          <dd class="font-mono-nums mt-1 font-medium">{{ resource.data.advance_decline_ratio ?? "—" }}</dd>
        </div>
        <div>
          <dt class="text-[var(--color-text-tertiary)]">% &gt; EMA50</dt>
          <dd class="font-mono-nums mt-1 font-medium">{{ formatPct(resource.data.pct_above_ema50) }}</dd>
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

export default {
  name: "MarketSentimentCard",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, Sparkline, StaleBadge },
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
  },
}
</script>
