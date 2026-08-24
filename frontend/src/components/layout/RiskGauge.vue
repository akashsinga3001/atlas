<template>
  <div class="flex h-8 shrink-0 items-center gap-4 border-b border-[var(--color-border)] bg-[var(--color-surface)] px-6">
    <span class="label-caps shrink-0">Risk</span>

    <div class="h-1.5 flex-1 overflow-hidden rounded-[var(--radius-sm)] bg-[var(--color-border-strong)]">
      <div class="h-full rounded-[var(--radius-sm)] transition-[width,background-color] duration-500" :style="{ width: `${fillPct}%`, backgroundColor: barColor }" />
    </div>

    <div class="font-mono-nums flex shrink-0 items-center gap-4 text-[11px]">
      <span v-if="halted" class="font-semibold" :style="{ color: 'var(--color-risk-hot)' }">HALTED — {{ haltedReason }}</span>
      <template v-else>
        <span class="text-[var(--color-text-tertiary)]">
          Deployed
          <strong class="ml-1 font-medium" :style="{ color: deployedRatio >= 1 ? 'var(--color-risk-hot)' : 'var(--color-text-secondary)' }">{{ deployedLabel }}</strong>
        </span>
        <span class="text-[var(--color-text-tertiary)]">
          Drawdown
          <strong class="ml-1 font-medium" :style="{ color: drawdownColor }">{{ drawdownLabel }}</strong>
        </span>
      </template>
    </div>
  </div>
</template>

<script>
import { useCapitalAllocationStore } from "@/stores/capitalAllocation"
import { useCircuitBreakersStore } from "@/stores/circuitBreakers"
import { useKillSwitchStore } from "@/stores/killSwitch"
import { usePortfolioStatsStore } from "@/stores/portfolioStats"

export default {
  name: "RiskGauge",
  computed: {
    capitalStore() {
      return useCapitalAllocationStore()
    },
    statsStore() {
      return usePortfolioStatsStore()
    },
    breakersStore() {
      return useCircuitBreakersStore()
    },
    killSwitchStore() {
      return useKillSwitchStore()
    },
    deployedRatio() {
      const pct = this.capitalStore.resource.data?.total_allocated_pct
      return pct !== undefined && pct !== null ? pct / 100 : 0
    },
    deployedLabel() {
      const pct = this.capitalStore.resource.data?.total_allocated_pct
      return pct !== undefined && pct !== null ? `${pct.toFixed(0)}%` : "—"
    },
    drawdownBreaker() {
      return this.breakersStore.breakers.find((b) => b.type === "drawdown") ?? null
    },
    drawdownThreshold() {
      const raw = this.drawdownBreaker?.params?.threshold_pct
      return typeof raw === "number" ? raw : 5.0
    },
    drawdownPct() {
      return this.statsStore.resource.data?.max_drawdown_pct ?? null
    },
    drawdownRatio() {
      if (this.drawdownPct === null || !this.drawdownBreaker?.enabled) return 0
      return this.drawdownPct / this.drawdownThreshold
    },
    drawdownLabel() {
      if (this.drawdownPct === null) return "—"
      return `${this.drawdownPct.toFixed(1)}% / ${this.drawdownThreshold.toFixed(0)}%`
    },
    drawdownColor() {
      if (this.drawdownRatio >= 1) return "var(--color-risk-hot)"
      if (this.drawdownRatio >= 0.75) return "var(--color-risk-elevated)"
      return "var(--color-text-secondary)"
    },
    halted() {
      return this.killSwitchStore.isActive
    },
    haltedReason() {
      return this.killSwitchStore.reason ?? "new entries paused"
    },
    dominantRatio() {
      return Math.max(this.deployedRatio, this.drawdownRatio)
    },
    fillPct() {
      if (this.halted) return 100
      return Math.min(this.dominantRatio, 1) * 100
    },
    barColor() {
      if (this.halted || this.dominantRatio >= 1) return "var(--color-risk-hot)"
      if (this.dominantRatio >= 0.75) return "var(--color-risk-elevated)"
      return "var(--color-risk-calm)"
    },
  },
  created() {
    if (this.capitalStore.resource.status === "idle") this.capitalStore.fetch()
    if (this.statsStore.resource.status === "idle") this.statsStore.fetch()
    if (this.breakersStore.resource.status === "idle") this.breakersStore.fetch()
  },
}
</script>
