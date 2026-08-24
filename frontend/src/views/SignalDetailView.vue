<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-5">
    <router-link to="/positions" class="inline-flex w-fit items-center gap-1 text-xs text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]">
      <ArrowLeft :size="12" />
      Positions
    </router-link>

    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="load" />
    <EmptyState v-else-if="!resource.data" title="Signal not found" />

    <template v-else>
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="flex h-10 w-10 items-center justify-center rounded-[var(--radius-base)] border border-[var(--color-positive-border)] bg-[var(--color-positive-bg)]">
            <LineChartIcon :size="18" class="text-[var(--color-positive)]" />
          </div>
          <div>
            <h1 class="text-xl font-semibold tracking-tight">{{ resource.data.signal.security.ticker }}</h1>
            <p class="mt-0.5 text-xs text-[var(--color-text-tertiary)]">{{ resource.data.signal.strategy_name ?? "—" }} · {{ formatDateTime(resource.data.signal.observed_at) }}</p>
          </div>
        </div>
        <div class="flex items-center gap-2">
          <StatusPill v-if="resource.data.summary.simulated" label="Simulated (no trade)" tone="inactive" />
          <StatusPill v-else :label="resource.data.signal.trade_status" :tone="resource.data.signal.trade_status === 'open' ? 'live' : 'inactive'" />
        </div>
      </div>

      <BaseCard :padded="true">
        <div class="grid grid-cols-2 gap-6 sm:grid-cols-4">
          <MetricTile label="Fill price" :value="formatCurrency(resource.data.signal.fill_price)" />
          <MetricTile label="Perf since signal" :value="formatPercent(resource.data.summary.perf_since_signal)" :tone="pnlTone(resource.data.summary.perf_since_signal)" />
          <MetricTile label="Trade P&L" :value="formatPercent(resource.data.summary.trade_pnl_pct)" :tone="pnlTone(resource.data.summary.trade_pnl_pct)" />
          <MetricTile label="Max perf" :value="formatPercent(resource.data.summary.max_perf)" :tone="pnlTone(resource.data.summary.max_perf)" />
        </div>
      </BaseCard>

      <BaseCard title="Forward price vs. trailing stop" :icon="LineChartIcon">
        <PriceChart :series="chartSeries" />
      </BaseCard>

      <BaseCard title="Daily progression" :icon="CalendarDays" :padded="false">
        <table class="w-full text-sm">
          <thead>
            <tr class="border-b border-[var(--color-border)] text-left">
              <th class="label-caps px-5 py-3.5 font-normal">Date</th>
              <th class="label-caps px-5 py-3.5 font-normal text-right">Close</th>
              <th class="label-caps px-5 py-3.5 font-normal text-right">Stop</th>
              <th class="label-caps px-5 py-3.5 font-normal text-right">MTM</th>
              <th class="label-caps px-5 py-3.5 font-normal">Exit</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in resource.data.forward_data" :key="row.date" class="border-b border-[var(--color-border)] last:border-0">
              <td class="px-5 py-3.5 text-[var(--color-text-secondary)]">{{ formatDate(row.date) }}</td>
              <td class="font-mono-nums px-5 py-3.5 text-right">{{ formatCurrency(row.close) }}</td>
              <td class="font-mono-nums px-5 py-3.5 text-right text-[var(--color-text-tertiary)]">{{ row.stop_price !== null ? formatCurrency(row.stop_price) : "—" }}</td>
              <td class="font-mono-nums px-5 py-3.5 text-right" :class="row.mtm_pct !== null && row.mtm_pct > 0 ? 'text-[var(--color-positive)]' : 'text-[var(--color-negative)]'">{{ formatPercent(row.mtm_pct) }}</td>
              <td class="px-5 py-3.5"><StatusPill v-if="row.exit_triggered" label="Exit triggered" tone="error" /></td>
            </tr>
          </tbody>
        </table>
      </BaseCard>
    </template>
  </div>
</template>

<script>
import { ArrowLeft, CalendarDays, LineChart as LineChartIcon } from "@lucide/vue"
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
  components: { BaseCard, EmptyState, ErrorState, LoadingState, MetricTile, PriceChart, StatusPill, ArrowLeft, CalendarDays },
  data() {
    return { LineChartIcon }
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
      const series = [{ name: "Close", color: "#4ed08a", data: forward.map((r) => ({ time: r.date, value: r.close })) }]
      const stopPoints = forward.filter((r) => r.stop_price !== null).map((r) => ({ time: r.date, value: r.stop_price }))
      if (stopPoints.length) series.push({ name: "Stop", color: "#f2545c", lineStyle: 2, data: stopPoints })
      return series
    },
  },
  created() {
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
    pnlTone,
    load() {
      this.store.loadFor(Number(this.$route.params.id))
    },
  },
}
</script>
