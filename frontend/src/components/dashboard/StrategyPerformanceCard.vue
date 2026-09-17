<template>
  <BaseCard title="Strategy Performance" :icon="Target" :padded="false">
    <template #header-actions>
      <StaleBadge :last-updated-at="resource.lastUpdatedAt" :has-error="resource.status === 'error'" />
    </template>
    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="$emit('retry')" />
    <EmptyState v-else-if="!resource.data?.length" class="h-full" title="No active strategies with trades yet" />
    <div v-else class="flex h-full flex-col overflow-x-auto px-4 pb-4">
      <table class="data-table">
        <thead>
          <tr>
            <th>Strategy</th>
            <th class="num">Positions</th>
            <th class="num">P&amp;L</th>
            <th class="num">Return</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in resource.data" :key="row.strategy_id">
            <td class="font-medium">{{ row.name }}</td>
            <td class="num font-mono-nums">{{ row.positions }}</td>
            <td class="num font-mono-nums" :class="pnlClass(row.pnl)">{{ formatCurrency(row.pnl, { signed: true }) }}</td>
            <td class="num font-mono-nums" :class="pnlClass(row.return_pct)">{{ row.return_pct !== null ? formatPercent(row.return_pct) : "—" }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </BaseCard>
</template>

<script>
import { Target } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import { formatCurrency, formatPercent, pnlTone } from "@/utils/format"

export default {
  name: "StrategyPerformanceCard",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, StaleBadge },
  props: {
    resource: { type: Object, required: true },
  },
  emits: ["retry"],
  data() {
    return { Target }
  },
  methods: {
    formatCurrency,
    formatPercent,
    pnlClass(value) {
      const tone = pnlTone(value)
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return "text-[var(--color-text-primary)]"
    },
  },
}
</script>
