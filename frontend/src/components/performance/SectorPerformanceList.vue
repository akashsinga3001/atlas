<template>
  <div class="flex flex-col gap-3">
    <div v-for="sector in sectors" :key="sector.sector">
      <div class="flex items-center justify-between text-xs">
        <span class="text-[var(--color-text-secondary)]">{{ sector.sector }}</span>
        <span class="font-mono-nums flex items-center gap-3">
          <span class="text-[var(--color-text-tertiary)]">{{ sector.trades }} trades</span>
          <span :class="sector.avg_return !== null && sector.avg_return >= 0 ? 'text-[var(--color-positive)]' : 'text-[var(--color-negative)]'">{{ formatPercent(sector.avg_return) }}</span>
        </span>
      </div>
      <div class="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-[var(--color-surface-alt)]">
        <div class="h-full rounded-full bg-[var(--color-live)]" :style="{ width: `${sector.win_rate ?? 0}%` }" />
      </div>
    </div>
  </div>
</template>

<script>
import { formatPercent } from "@/utils/format"

export default {
  name: "SectorPerformanceList",
  props: {
    sectors: {
      type: Array,
      required: true,
    },
  },
  methods: {
    formatPercent,
  },
}
</script>
