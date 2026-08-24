<template>
  <BaseCard title="Strategies" :icon="Layers">
    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="$emit('retry')" />
    <EmptyState v-else-if="!strategies.length" title="No strategies configured" />
    <div v-else class="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
      <router-link
        v-for="strategy in strategies"
        :key="strategy.id"
        :to="`/strategies/${strategy.id}`"
        class="group flex flex-col gap-2.5 rounded-[var(--radius-base)] border border-[var(--color-border)] bg-[var(--color-surface-alt)] p-4 transition-all duration-150 hover:-translate-y-0.5 hover:border-[var(--color-border-strong)] hover:bg-[var(--color-surface-hover)] hover:shadow-[0_8px_20px_-8px_rgba(0,0,0,0.5)]"
      >
        <div class="flex items-center justify-between gap-2">
          <span class="text-sm font-medium text-[var(--color-text-primary)]">{{ strategy.name }}</span>
          <ChevronRight :size="14" class="text-[var(--color-text-tertiary)] opacity-0 transition-opacity group-hover:opacity-100" />
        </div>
        <StatusPill :label="statusFor(strategy).label" :tone="statusFor(strategy).tone" class="w-fit" />
        <p class="text-xs text-[var(--color-text-tertiary)]">
          {{ strategy.open_positions_count }} open position{{ strategy.open_positions_count === 1 ? "" : "s" }}
          <span v-if="strategy.last_run_at"> · last run {{ formatDateTime(strategy.last_run_at) }}</span>
        </p>
      </router-link>
    </div>
  </BaseCard>
</template>

<script>
import { ChevronRight, Layers } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { formatDateTime } from "@/utils/format"

export default {
  name: "StrategyStatusGrid",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, StatusPill, ChevronRight },
  props: {
    resource: {
      type: Object,
      required: true,
    },
  },
  emits: ["retry"],
  data() {
    return { Layers }
  },
  computed: {
    strategies() {
      return this.resource.data ?? []
    },
  },
  methods: {
    formatDateTime,
    statusFor(strategy) {
      if (strategy.last_run_status === "FAILED") return { label: "Error", tone: "error" }
      if (!strategy.is_active) return { label: "Inactive", tone: "inactive" }
      if (strategy.open_positions_count > 0) return { label: "Active", tone: "live" }
      return { label: "Idle", tone: "inactive" }
    },
  },
}
</script>
