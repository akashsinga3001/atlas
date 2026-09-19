<template>
  <BaseCard title="Capital Allocation" :icon="PiggyBank" :padded="false">
    <template #header-actions>
      <StaleBadge :last-updated-at="resource.lastUpdatedAt" :has-error="resource.status === 'error'" />
    </template>
    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="$emit('retry')" />
    <EmptyState v-else-if="!resource.data || !allStrategies.length" title="No strategies yet" description="Capital budgets appear here once a strategy exists." />
    <!-- Nowhere else on the dashboard shows this: Portfolio Value shows total deployed $ across
         the whole book, Strategy Performance shows P&L per strategy — neither answers "is each
         strategy actually using the capital budget I gave it." A strategy sitting at 20% of its
         allocated budget for weeks is a signal worth seeing (not finding signals, or misconfigured),
         and one pinned at 100%+ is a different signal (fully committed, or over its own budget). -->
    <div v-else class="flex h-full flex-col gap-3 px-4 pb-4">
      <div class="grid shrink-0 grid-cols-2 gap-2 text-center">
        <div class="rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] py-2">
          <p class="font-mono-nums text-[15px] font-semibold" :class="resource.data.overallocated ? 'text-[var(--color-negative)]' : 'text-[var(--color-text-primary)]'">{{ resource.data.total_allocated_pct }}%</p>
          <p class="label-caps mt-0.5">Allocated</p>
        </div>
        <div class="rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] py-2">
          <p class="font-mono-nums text-[15px] font-semibold" :class="headroomPct < 0 ? 'text-[var(--color-negative)]' : 'text-[var(--color-text-primary)]'">{{ headroomPct < 0 ? "Over" : `${headroomPct}%` }}</p>
          <p class="label-caps mt-0.5">Headroom</p>
        </div>
      </div>

      <div class="flex flex-1 flex-col divide-y divide-[var(--color-border)]">
        <div v-for="s in rows" :key="s.id" class="flex flex-1 items-center gap-3 py-1.5">
          <div class="w-[92px] shrink-0">
            <p class="truncate text-[11.5px]" :class="s.active ? 'text-[var(--color-text-secondary)]' : 'text-[var(--color-text-tertiary)]'">{{ s.name }}</p>
            <p class="font-mono-nums text-[10px] text-[var(--color-text-tertiary)]">{{ s.active ? `${formatCurrency(s.deployed_amount, { compact: true })} / ${formatCurrency(s.allocated_amount, { compact: true })}` : "Not active" }}</p>
          </div>
          <div class="h-2 flex-1 overflow-hidden rounded-full bg-[var(--color-surface-alt)]">
            <div v-if="s.active" class="h-full rounded-full" :class="usageClass(s.deployed_pct_of_allocated)" :style="{ width: `${Math.min(s.deployed_pct_of_allocated ?? 0, 100)}%` }" />
          </div>
          <span class="font-mono-nums w-9 shrink-0 text-right text-[11.5px]" :class="s.deployed_pct_of_allocated !== null && s.deployed_pct_of_allocated > 100 ? 'text-[var(--color-negative)]' : 'text-[var(--color-text-tertiary)]'">
            {{ s.active && s.deployed_pct_of_allocated !== null ? `${s.deployed_pct_of_allocated}%` : "—" }}
          </span>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<script>
import { PiggyBank } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import { formatCurrency } from "@/utils/format"

export default {
  name: "CapitalAllocationCard",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, StaleBadge },
  props: {
    resource: {
      type: Object,
      required: true,
    },
    // All registered strategies (active or not) — get_capital_allocation() only returns
    // currently-active ones, but an idle strategy sitting at 0% is exactly the kind of thing an
    // owner deciding whether to activate something new would want to see here, not just the one
    // or two that happen to be running today.
    allStrategies: {
      type: Array,
      default: () => [],
    },
  },
  emits: ["retry"],
  data() {
    return { PiggyBank }
  },
  computed: {
    headroomPct() {
      return Math.round((100 - (this.resource.data?.total_allocated_pct ?? 0)) * 100) / 100
    },
    rows() {
      const byId = new Map((this.resource.data?.strategies ?? []).map((s) => [s.strategy_id, s]))
      return this.allStrategies.map((s) => {
        const allocation = byId.get(s.id)
        return allocation ? { id: s.id, name: s.name, active: true, ...allocation } : { id: s.id, name: s.name, active: false }
      })
    },
  },
  methods: {
    formatCurrency,
    usageClass(pct) {
      if (pct === null || pct === undefined) return "bg-[var(--color-border-strong)]"
      if (pct > 100) return "bg-[var(--color-negative)]"
      return "bg-[var(--color-accent)]"
    },
  },
}
</script>
