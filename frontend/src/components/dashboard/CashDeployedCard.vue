<template>
  <BaseCard title="Capital Allocation" :icon="PiggyBank">
    <LoadingState v-if="loading" />
    <div v-else class="flex h-full flex-col gap-4">
      <div class="flex items-center justify-between text-[12.5px] font-medium">
        <span class="text-[var(--color-text-primary)]">{{ formatCurrency(deployed, { compact: true }) }} <span class="text-[var(--color-text-tertiary)] font-normal">({{ pct(deployedPct) }})</span></span>
        <span class="text-[var(--color-text-primary)]">{{ formatCurrency(cash, { compact: true }) }} <span class="text-[var(--color-text-tertiary)] font-normal">({{ pct(cashPct) }})</span></span>
      </div>
      <div class="flex h-2.5 w-full overflow-hidden rounded-full bg-[var(--color-surface-alt)]">
        <div class="h-full bg-[var(--color-positive)]" :style="{ width: `${Math.min(deployedPct ?? 0, 100)}%` }" />
      </div>
      <div class="flex items-center gap-5 text-[11.5px]">
        <span class="flex items-center gap-1.5 text-[var(--color-text-secondary)]"><span class="h-2 w-2 rounded-full bg-[var(--color-positive)]" />Deployed Capital</span>
        <span class="flex items-center gap-1.5 text-[var(--color-text-secondary)]"><span class="h-2 w-2 rounded-full bg-[var(--color-surface-alt)] ring-1 ring-inset ring-[var(--color-border-strong)]" />Available Cash</span>
      </div>
    </div>
  </BaseCard>
</template>

<script>
import { PiggyBank } from "@lucide/vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import { formatCurrency } from "@/utils/format"

export default {
  name: "CashDeployedCard",
  components: { BaseCard, LoadingState },
  props: {
    loading: { type: Boolean, default: false },
    nav: { type: Number, default: null },
    cash: { type: Number, default: null },
    deployed: { type: Number, default: null },
  },
  data() {
    return { PiggyBank }
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
  },
}
</script>
