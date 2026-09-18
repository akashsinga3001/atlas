<template>
  <BaseCard title="Today's P&L" :icon="TrendingUp">
    <template #header-actions>
      <StaleBadge :last-updated-at="lastUpdatedAt" :has-error="hasError" />
    </template>
    <LoadingState v-if="loading" />
    <div v-else class="flex h-full flex-col">
      <div class="flex flex-1 flex-col justify-center gap-3">
        <div class="flex items-end justify-between gap-3">
          <div>
            <p class="label-caps">Today</p>
            <p class="figure-hero mt-0.5 text-2xl" :class="pnlClass(total)">{{ total !== null ? formatCurrency(total, { compact: true, signed: true }) : "—" }}</p>
            <p v-if="realizedToday !== null || unrealizedNow !== null" class="mt-0.5 text-[10.5px] text-[var(--color-text-tertiary)]">
              Realized {{ formatCurrency(realizedToday, { compact: true, signed: true }) }} · Unrealized {{ formatCurrency(unrealizedNow, { compact: true, signed: true }) }}
            </p>
          </div>
          <div class="text-right">
            <p class="label-caps">Total P&amp;L</p>
            <p class="font-mono-nums mt-0.5 text-[15px] font-semibold" :class="pnlClass(totalPnl)">{{ totalPnl !== null ? formatCurrency(totalPnl, { compact: true, signed: true }) : "—" }}</p>
          </div>
        </div>

        <div class="grid grid-cols-3 gap-2 text-center">
          <div class="rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] py-2">
            <p class="font-mono-nums text-[15px] font-semibold text-[var(--color-positive)]">{{ winners }}</p>
            <p class="label-caps mt-0.5">Winners</p>
          </div>
          <div class="rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] py-2">
            <p class="font-mono-nums text-[15px] font-semibold text-[var(--color-negative)]">{{ losers }}</p>
            <p class="label-caps mt-0.5">Losers</p>
          </div>
          <div class="rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] py-2">
            <p class="font-mono-nums text-[15px] font-semibold text-[var(--color-text-primary)]">{{ breakeven }}</p>
            <p class="label-caps mt-0.5">Breakeven</p>
          </div>
        </div>
      </div>

      <div class="flex flex-1 flex-col justify-center gap-2 border-t border-[var(--color-border)] pt-3">
        <p class="label-caps">Capital Allocation</p>
        <div class="flex items-center justify-between text-[12px] font-medium">
          <span class="text-[var(--color-text-primary)]">{{ formatCurrency(deployed, { compact: true }) }} <span class="text-[var(--color-text-tertiary)] font-normal">({{ pct(deployedPct) }})</span></span>
          <span class="text-[var(--color-text-primary)]">{{ formatCurrency(cash, { compact: true }) }} <span class="text-[var(--color-text-tertiary)] font-normal">({{ pct(cashPct) }})</span></span>
        </div>
        <div class="flex h-2 w-full overflow-hidden rounded-full bg-[var(--color-surface-alt)]">
          <div class="h-full bg-[var(--color-positive)]" :style="{ width: `${Math.min(deployedPct ?? 0, 100)}%` }" />
        </div>
        <div class="flex items-center gap-4 text-[11px]">
          <span class="flex items-center gap-1.5 text-[var(--color-text-secondary)]"><span class="h-2 w-2 rounded-full bg-[var(--color-positive)]" />Deployed Capital</span>
          <span class="flex items-center gap-1.5 text-[var(--color-text-secondary)]"><span class="h-2 w-2 rounded-full bg-[var(--color-surface-alt)] ring-1 ring-inset ring-[var(--color-border-strong)]" />Available Cash</span>
        </div>
      </div>
    </div>
  </BaseCard>
</template>

<script>
import { TrendingUp } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import { formatCurrency, pnlTone } from "@/utils/format"

export default {
  name: "TodaysPnlCard",
  components: { BaseCard, LoadingState, StaleBadge },
  props: {
    loading: { type: Boolean, default: false },
    lastUpdatedAt: { type: Number, default: null },
    hasError: { type: Boolean, default: false },
    total: { type: Number, default: null },
    totalPnl: { type: Number, default: null },
    realizedToday: { type: Number, default: null },
    unrealizedNow: { type: Number, default: null },
    winners: { type: Number, default: 0 },
    losers: { type: Number, default: 0 },
    breakeven: { type: Number, default: 0 },
    nav: { type: Number, default: null },
    cash: { type: Number, default: null },
    deployed: { type: Number, default: null },
  },
  data() {
    return { TrendingUp }
  },
  computed: {
    cashPct() {
      return this.nav ? (this.cash / this.nav) * 100 : null
    },
    deployedPct() {
      return this.nav ? (this.deployed / this.nav) * 100 : null
    },
  },
  methods: {
    formatCurrency,
    pct(value) {
      return value !== null && value !== undefined ? `${value.toFixed(1)}%` : "—"
    },
    pnlClass(value) {
      const tone = pnlTone(value)
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return "text-[var(--color-text-primary)]"
    },
  },
}
</script>
