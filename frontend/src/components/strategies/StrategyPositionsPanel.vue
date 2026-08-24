<template>
  <div class="flex flex-col gap-6">
    <div>
      <h3 class="label-caps mb-2">Equity trades</h3>
      <LoadingState v-if="tradesStore.resource.status === 'loading'" />
      <ErrorState v-else-if="tradesStore.resource.status === 'error' && !tradesStore.resource.data" :message="tradesStore.resource.error" @retry="tradesStore.fetch" />
      <EmptyState v-else-if="!trades.length" title="No equity trades for this strategy" />
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="border-b border-[var(--color-border)] text-left">
            <th class="label-caps pb-3 font-normal">Ticker</th>
            <th class="label-caps pb-3 font-normal">Status</th>
            <th class="label-caps pb-3 font-normal">Entry</th>
            <th class="label-caps pb-3 font-normal text-right">P&L</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="trade in trades" :key="trade.id" class="border-b border-[var(--color-border)] last:border-0">
            <td class="py-3.5 font-medium">{{ trade.security.ticker }}</td>
            <td class="py-3.5"><StatusPill :label="trade.status" :tone="trade.status === 'open' ? 'live' : 'inactive'" /></td>
            <td class="py-3.5 text-[var(--color-text-secondary)]">{{ formatDate(trade.entry_date) }}</td>
            <td class="font-mono-nums py-3.5 text-right" :class="pnlClass(trade.pnl)">{{ formatCurrency(trade.pnl) }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div>
      <h3 class="label-caps mb-2">Options positions</h3>
      <LoadingState v-if="optionsStore.resource.status === 'loading'" />
      <ErrorState v-else-if="optionsStore.resource.status === 'error' && !optionsStore.resource.data" :message="optionsStore.resource.error" @retry="optionsStore.fetch" />
      <EmptyState v-else-if="!positions.length" title="No options positions for this strategy" />
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="border-b border-[var(--color-border)] text-left">
            <th class="label-caps pb-3 font-normal">Expiry</th>
            <th class="label-caps pb-3 font-normal">Status</th>
            <th class="label-caps pb-3 font-normal">Lots</th>
            <th class="label-caps pb-3 font-normal text-right">Realized P&L</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="position in positions" :key="position.id" class="border-b border-[var(--color-border)] last:border-0">
            <td class="py-3.5 font-medium">{{ formatDate(position.expiry_date) }}</td>
            <td class="py-3.5"><StatusPill :label="position.status" :tone="statusTone(position.status)" /></td>
            <td class="font-mono-nums py-3.5">{{ position.lots ?? "—" }}</td>
            <td class="font-mono-nums py-3.5 text-right" :class="pnlClass(position.realized_pnl)">{{ formatCurrency(position.realized_pnl) }}</td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script>
import { useOptionsStore } from "@/stores/options"
import { useTradesStore } from "@/stores/trades"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { formatCurrency, formatDate, pnlTone } from "@/utils/format"

const OPTIONS_STATUS_TONE = { open: "live", pending: "warning", closing: "warning", closed: "inactive", failed: "error", skipped: "inactive" }

export default {
  name: "StrategyPositionsPanel",
  components: { EmptyState, ErrorState, LoadingState, StatusPill },
  props: {
    strategyId: {
      type: Number,
      required: true,
    },
  },
  computed: {
    tradesStore() {
      return useTradesStore()
    },
    optionsStore() {
      return useOptionsStore()
    },
    trades() {
      return this.tradesStore.forStrategy(this.strategyId)
    },
    positions() {
      return this.optionsStore.forStrategy(this.strategyId)
    },
  },
  created() {
    if (this.tradesStore.resource.status === "idle") this.tradesStore.fetch()
    if (this.optionsStore.resource.status === "idle") this.optionsStore.fetch()
  },
  methods: {
    formatCurrency,
    formatDate,
    pnlClass(value) {
      const tone = pnlTone(value)
      return tone === "positive" ? "text-[var(--color-positive)]" : tone === "negative" ? "text-[var(--color-negative)]" : "text-[var(--color-text-secondary)]"
    },
    statusTone(status) {
      return OPTIONS_STATUS_TONE[status] ?? "inactive"
    },
  },
}
</script>
