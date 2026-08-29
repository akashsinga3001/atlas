<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <div class="flex flex-wrap items-center gap-2">
      <input v-model="filters.symbol" type="text" placeholder="Search symbol…" class="filter-control w-44" />
      <select v-model="filters.status" class="filter-control">
        <option value="">All statuses</option>
        <option value="open">Open</option>
        <option value="pending">Pending</option>
        <option value="closed">Closed</option>
      </select>
      <select v-model="filters.strategy" class="filter-control">
        <option value="">All strategies</option>
        <option v-for="name in strategyNames" :key="name" :value="name">{{ name }}</option>
      </select>
      <span class="ml-auto text-[12px] text-[var(--color-text-tertiary)]">{{ filtered.length }} trades</span>
    </div>

    <BaseCard :padded="false">
      <LoadingState v-if="tradesStore.resource.status === 'loading'" />
      <ErrorState v-else-if="tradesStore.resource.status === 'error' && !tradesStore.resource.data" :message="tradesStore.resource.error" @retry="tradesStore.fetch" />
      <EmptyState v-else-if="!filtered.length" title="No trades match these filters" description="Equity trades will appear here once a strategy enters a position." />
      <div v-else class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Strategy</th>
              <th>Status</th>
              <th>Entry date</th>
              <th>Exit date</th>
              <th class="num">Qty</th>
              <th class="num">Entry price</th>
              <th class="num">P&amp;L</th>
              <th class="num">P&amp;L %</th>
              <th>Duration</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="t in filtered" :key="t.id" class="cursor-pointer" @click="$router.push(`/trades/${t.id}`)">
              <td class="font-medium">{{ t.security.ticker }}</td>
              <td>{{ t.strategy_name }}</td>
              <td><StatusPill :label="t.status" :tone="statusTone(t.status)" /></td>
              <td>{{ formatDate(t.entry_date) }}</td>
              <td>{{ t.exit_date ? formatDate(t.exit_date) : "—" }}</td>
              <td class="num font-mono-nums">{{ t.fill_quantity ?? "—" }}</td>
              <td class="num font-mono-nums">{{ t.fill_price !== null ? formatCurrency(t.fill_price) : "—" }}</td>
              <td class="num font-mono-nums" :class="pnlClass(t.pnl)">{{ t.pnl !== null ? formatCurrency(t.pnl, { signed: true }) : "—" }}</td>
              <td class="num font-mono-nums" :class="pnlClass(t.pnl_pct)">{{ t.pnl_pct !== null ? formatPercent(t.pnl_pct) : "—" }}</td>
              <td>{{ durationLabel(t) }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </BaseCard>
  </div>
</template>

<script>
import { useTradesStore } from "@/stores/trades"
import { usePageHeaderStore } from "@/stores/pageHeader"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { formatCurrency, formatDate, formatPercent, pnlTone } from "@/utils/format"

export default {
  name: "TradesView",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, StatusPill },
  data() {
    return {
      filters: { symbol: "", status: "", strategy: "" },
    }
  },
  computed: {
    tradesStore() {
      return useTradesStore()
    },
    strategyNames() {
      return [...new Set(this.tradesStore.trades.map((t) => t.strategy_name))].sort()
    },
    filtered() {
      return this.tradesStore.trades.filter((t) => {
        if (this.filters.symbol && !t.security.ticker.toLowerCase().includes(this.filters.symbol.toLowerCase())) return false
        if (this.filters.status && t.status !== this.filters.status) return false
        if (this.filters.strategy && t.strategy_name !== this.filters.strategy) return false
        return true
      })
    },
  },
  created() {
    usePageHeaderStore().set("Trades", "Equity trading ledger")
    if (this.tradesStore.resource.status === "idle") this.tradesStore.fetch()
  },
  methods: {
    formatCurrency,
    formatDate,
    formatPercent,
    statusTone(status) {
      if (status === "open") return "live"
      if (status === "closed") return "inactive"
      return "warning"
    },
    pnlClass(value) {
      const tone = pnlTone(value)
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return ""
    },
    durationLabel(t) {
      if (!t.exit_date) return "—"
      const days = Math.round((new Date(t.exit_date).getTime() - new Date(t.entry_date).getTime()) / 86400000)
      return `${days}d`
    },
  },
}
</script>
