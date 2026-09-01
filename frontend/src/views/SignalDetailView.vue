<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <router-link to="/signals" class="inline-flex w-fit items-center gap-1 text-xs text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]">
      <ArrowLeft :size="12" />
      Signals
    </router-link>

    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="load" />
    <EmptyState v-else-if="!resource.data" title="Signal not found" />

    <template v-else>
      <div class="flex items-center justify-between">
        <div>
          <h1 class="font-display text-xl font-semibold tracking-tight text-[var(--color-text-primary)]">{{ resource.data.signal.security.ticker }}</h1>
          <p class="mt-0.5 text-xs text-[var(--color-text-tertiary)]">{{ resource.data.signal.strategy_name ?? "—" }} · {{ formatDateTime(resource.data.signal.observed_at) }}</p>
        </div>
        <StatusPill v-if="resource.data.summary.simulated" label="Simulated (no trade)" tone="inactive" />
        <StatusPill v-else :label="resource.data.signal.trade_status" :tone="resource.data.signal.trade_status === 'open' ? 'live' : 'inactive'" />
      </div>

      <BaseCard>
        <div class="grid grid-cols-2 gap-6 sm:grid-cols-4">
          <MetricTile label="Fill price" :value="formatCurrency(resource.data.signal.fill_price)" />
          <MetricTile label="Perf since signal" :value="formatPercent(resource.data.summary.perf_since_signal)" :tone="tileTone(resource.data.summary.perf_since_signal)" />
          <MetricTile label="Trade P&L" :value="formatPercent(resource.data.summary.trade_pnl_pct)" :tone="tileTone(resource.data.summary.trade_pnl_pct)" />
          <MetricTile label="Max perf" :value="formatPercent(resource.data.summary.max_perf)" :tone="tileTone(resource.data.summary.max_perf)" />
        </div>
      </BaseCard>

      <BaseCard title="Forward price vs. trailing stop" :icon="LineChartIcon">
        <PriceChart :series="chartSeries" :height="200" />
      </BaseCard>

      <BaseCard title="Daily progression" :icon="CalendarDays" :padded="false">
        <div class="overflow-x-auto">
          <table class="data-table">
            <thead>
              <tr>
                <th>Date</th>
                <th class="num">Close</th>
                <th class="num">Stop</th>
                <th class="num">MTM</th>
                <th>Exit</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="row in resource.data.forward_data" :key="row.date">
                <td>{{ formatDate(row.date) }}</td>
                <td class="num font-mono-nums">{{ formatCurrency(row.close) }}</td>
                <td class="num font-mono-nums text-[var(--color-text-tertiary)]">{{ row.stop_price !== null ? formatCurrency(row.stop_price) : "—" }}</td>
                <td class="num font-mono-nums" :class="row.mtm_pct !== null && row.mtm_pct > 0 ? 'text-[var(--color-positive)]' : 'text-[var(--color-negative)]'">{{ formatPercent(row.mtm_pct) }}</td>
                <td><StatusPill v-if="row.exit_triggered" label="Exit triggered" tone="error" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </BaseCard>
    </template>
  </div>
</template>

<script>
import { ArrowLeft, CalendarDays, LineChart as LineChartIcon } from "@lucide/vue"
import { usePageHeaderStore } from "@/stores/pageHeader"
import { useSignalDetailStore } from "@/stores/signalDetail"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import MetricTile from "@/components/primitives/MetricTile.vue"
import PriceChart from "@/components/primitives/PriceChart.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { formatCurrency, formatDate, formatDateTime, formatPercent, pnlTone } from "@/utils/format"

export default {
  name: "SignalDetailView",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, MetricTile, PriceChart, StatusPill, ArrowLeft },
  data() {
    return { LineChartIcon, CalendarDays }
  },
  computed: {
    store() {
      return useSignalDetailStore()
    },
    resource() {
      return this.store.resource
    },
    chartSeries() {
      if (!this.resource.data) return []
      const forward = this.resource.data.forward_data
      const series = [{ name: "Close", color: "#1f8a5c", data: forward.map((r) => ({ time: r.date, value: r.close })) }]
      const stopPoints = forward.filter((r) => r.stop_price !== null).map((r) => ({ time: r.date, value: r.stop_price }))
      if (stopPoints.length) series.push({ name: "Stop", color: "#c8402e", lineStyle: 2, data: stopPoints })
      return series
    },
  },
  created() {
    usePageHeaderStore().set("Signal detail")
    this.load()
  },
  async beforeRouteUpdate(to) {
    await this.store.loadFor(Number(to.params.id))
  },
  methods: {
    formatCurrency,
    formatDate,
    formatDateTime,
    formatPercent,
    tileTone(value) {
      const tone = pnlTone(value)
      return tone === "inactive" ? "neutral" : tone
    },
    load() {
      this.store.loadFor(Number(this.$route.params.id))
      if (this.resource.data) usePageHeaderStore().set(this.resource.data.signal.security.ticker, this.resource.data.signal.strategy_name ?? "")
    },
  },
}
</script>
