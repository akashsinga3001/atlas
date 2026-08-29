<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <router-link to="/trades" class="inline-flex w-fit items-center gap-1 text-xs text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]">
      <ArrowLeft :size="12" />
      Trades
    </router-link>

    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !trade" :message="resource.error" @retry="load" />
    <EmptyState v-else-if="!trade" title="Trade not found" />

    <template v-else>
      <div class="flex items-center justify-between">
        <div>
          <h2 class="font-display text-xl font-semibold tracking-tight">{{ trade.security.ticker }}</h2>
          <p class="mt-0.5 text-xs text-[var(--color-text-tertiary)]">{{ trade.strategy_name }} · {{ trade.security.sector ?? "—" }}</p>
        </div>
        <StatusPill :label="trade.status" :tone="statusTone(trade.status)" />
      </div>

      <BaseCard>
        <div class="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
          <MetricTile label="Entry date" :value="formatDate(trade.entry_date)" />
          <MetricTile label="Entry price" :value="trade.fill_price !== null ? formatCurrency(trade.fill_price) : '—'" />
          <MetricTile label="Quantity" :value="String(trade.fill_quantity ?? '—')" />
          <MetricTile label="Invested" :value="trade.invested_value !== null ? formatCurrency(trade.invested_value) : '—'" />
          <MetricTile label="Exit date" :value="trade.exit_date ? formatDate(trade.exit_date) : '—'" />
          <MetricTile label="Exit reason" :value="trade.exit_reason ?? '—'" />
          <MetricTile label="P&amp;L" :value="trade.pnl !== null ? formatCurrency(trade.pnl, { signed: true }) : '—'" :tone="tileTone(trade.pnl)" />
          <MetricTile label="P&amp;L %" :value="trade.pnl_pct !== null ? formatPercent(trade.pnl_pct) : '—'" :tone="tileTone(trade.pnl_pct)" />
        </div>
      </BaseCard>

      <BaseCard v-if="hasTrailingStopInfo" title="ATR trailing stop" :icon="TrendingDown">
        <div class="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-3">
          <MetricTile label="Current stop" :value="trade.state.current_stop !== undefined ? formatCurrency(trade.state.current_stop) : '—'" />
          <MetricTile label="Highest close" :value="trade.state.highest_close !== undefined ? formatCurrency(trade.state.highest_close) : '—'" />
          <MetricTile label="Timeout date" :value="formatDate(trade.timeout_date)" />
        </div>
      </BaseCard>
      <BaseCard v-else title="Exit rule" :icon="Clock">
        <p class="text-[12.5px] text-[var(--color-text-secondary)]">Timeout exit scheduled for <span class="font-medium text-[var(--color-text-primary)]">{{ formatDate(trade.timeout_date) }}</span> if no earlier exit condition triggers.</p>
      </BaseCard>
    </template>
  </div>
</template>

<script>
import { ArrowLeft, Clock, TrendingDown } from "@lucide/vue"
import { fetchTrades } from "@/services/api/trades"
import { usePageHeaderStore } from "@/stores/pageHeader"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import MetricTile from "@/components/primitives/MetricTile.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { formatCurrency, formatDate, formatPercent, pnlTone } from "@/utils/format"

export default {
  name: "TradeDetailView",
  components: { ArrowLeft, BaseCard, EmptyState, ErrorState, LoadingState, MetricTile, StatusPill },
  data() {
    return {
      Clock,
      TrendingDown,
      resource: { status: "idle", data: null, error: null },
    }
  },
  computed: {
    trade() {
      const id = Number(this.$route.params.id)
      return (this.resource.data ?? []).find((t) => t.id === id) ?? null
    },
    hasTrailingStopInfo() {
      return this.trade?.state && ("current_stop" in this.trade.state || "highest_close" in this.trade.state)
    },
  },
  created() {
    usePageHeaderStore().set("Trade detail")
    this.load()
  },
  methods: {
    formatCurrency,
    formatDate,
    formatPercent,
    pnlTone,
    tileTone(value) {
      const tone = pnlTone(value)
      return tone === "inactive" ? "neutral" : tone
    },
    statusTone(status) {
      if (status === "open") return "live"
      if (status === "closed") return "inactive"
      return "warning"
    },
    async load() {
      this.resource.status = "loading"
      const result = await fetchTrades()
      if (result.error) {
        this.resource.status = "error"
        this.resource.error = result.message
        return
      }
      this.resource.data = result.data
      this.resource.status = "success"
      if (this.trade) usePageHeaderStore().set(this.trade.security.ticker, this.trade.strategy_name)
    },
  },
}
</script>
