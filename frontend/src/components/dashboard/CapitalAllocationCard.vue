<template>
  <BaseCard title="Capital allocation" :icon="PiggyBank">
    <template #header-actions>
      <StaleBadge :last-updated-at="resource.lastUpdatedAt" :has-error="resource.status === 'error'" />
    </template>
    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="$emit('retry')" />
    <EmptyState v-else-if="!resource.data || resource.data.account_size === null" title="No capital snapshot yet" description="Waiting on the first daily account snapshot." />
    <div v-else class="flex flex-col gap-4">
      <div v-if="resource.data.overallocated" class="flex items-center gap-2 rounded-[var(--radius-sm)] border border-[var(--color-error-border)] bg-[var(--color-error-bg)] px-3 py-2 text-xs font-medium text-[var(--color-error)]">
        <TriangleAlert :size="14" class="shrink-0" />
        Combined allocation is {{ resource.data.total_allocated_pct }}% of account — over 100%
      </div>

      <p class="figure-hero text-2xl text-[var(--color-text-primary)]">{{ formatCurrency(resource.data.account_size, { compact: true }) }}</p>

      <div v-for="strategy in resource.data.strategies" :key="strategy.strategy_id" class="flex flex-col gap-1.5">
        <div class="flex items-center justify-between text-xs">
          <span class="text-[var(--color-text-secondary)]">{{ strategy.name }}</span>
          <span class="font-mono-nums text-[var(--color-text-tertiary)]">{{ formatCurrency(strategy.deployed_amount, { compact: true }) }} / {{ formatCurrency(strategy.allocated_amount, { compact: true }) }}</span>
        </div>
        <div class="h-1.5 w-full overflow-hidden rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)]">
          <div class="h-full rounded-[var(--radius-sm)] bg-[var(--color-accent)]" :style="{ width: `${Math.min(strategy.deployed_pct_of_allocated ?? 0, 100)}%` }"></div>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<script>
import { PiggyBank, TriangleAlert } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import { formatCurrency } from "@/utils/format"

export default {
  name: "CapitalAllocationCard",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, StaleBadge, TriangleAlert },
  props: {
    resource: {
      type: Object,
      required: true,
    },
  },
  emits: ["retry"],
  data() {
    return { PiggyBank }
  },
  methods: {
    formatCurrency,
  },
}
</script>
