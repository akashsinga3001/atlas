<template>
  <BaseCard title="Recent Activity" :icon="History">
    <EmptyState v-if="!items.length" class="h-full" title="No activity yet today" />
    <div v-else class="flex h-full flex-col divide-y divide-[var(--color-border)]">
      <div v-for="(item, i) in items" :key="i" class="flex items-start gap-2.5 py-2.5 first:pt-0 last:pb-0">
        <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full" :class="iconWrapClass(item.type)">
          <component :is="iconFor(item.type)" :size="13" />
        </span>
        <div class="min-w-0 flex-1">
          <p class="truncate text-[12px] text-[var(--color-text-primary)]">{{ item.text }}</p>
          <p v-if="item.time" class="font-mono-nums text-[10.5px] text-[var(--color-text-tertiary)]">{{ item.time }}</p>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<script>
import { ArrowDownCircle, ArrowUpCircle, Camera, Cpu, Database, History, RefreshCw, Signal, Target } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"

// Keyed off the same job names registered backend-side (JobDefinition(name=...) across
// app/jobs/*.py) plus the two synthetic trade event types todaysActivity() emits.
const ICON_MAP = {
  OHLCV_IMPORT: { icon: Database, wrap: "bg-[var(--color-accent)]/12 text-[var(--color-accent)]" },
  FEATURE_GENERATION: { icon: Cpu, wrap: "bg-[var(--color-accent)]/12 text-[var(--color-accent)]" },
  TRADE_RECONCILIATION: { icon: RefreshCw, wrap: "bg-[var(--color-inactive)]/12 text-[var(--color-inactive)]" },
  STRATEGY_EXECUTION: { icon: Signal, wrap: "bg-[var(--color-accent)]/12 text-[var(--color-accent)]" },
  POSITION_SYNC: { icon: RefreshCw, wrap: "bg-[var(--color-inactive)]/12 text-[var(--color-inactive)]" },
  DAILY_ACCOUNT_SNAPSHOT: { icon: Camera, wrap: "bg-[var(--color-inactive)]/12 text-[var(--color-inactive)]" },
  trade_entry: { icon: ArrowUpCircle, wrap: "bg-[var(--color-positive)]/12 text-[var(--color-positive)]" },
  trade_exit: { icon: ArrowDownCircle, wrap: "bg-[var(--color-negative)]/12 text-[var(--color-negative)]" },
}
const DEFAULT_ICON = { icon: Target, wrap: "bg-[var(--color-inactive)]/12 text-[var(--color-inactive)]" }

export default {
  name: "RecentActivityCard",
  components: { BaseCard, EmptyState },
  props: {
    items: { type: Array, required: true }, // {type, text, time}[]
  },
  data() {
    return { History }
  },
  methods: {
    iconFor(type) {
      return (ICON_MAP[type] ?? DEFAULT_ICON).icon
    },
    iconWrapClass(type) {
      return (ICON_MAP[type] ?? DEFAULT_ICON).wrap
    },
  },
}
</script>
