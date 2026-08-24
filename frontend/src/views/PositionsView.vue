<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-5">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold tracking-tight">Positions</h1>
        <p class="mt-1 text-sm text-[var(--color-text-tertiary)]">Equity and options, unified.</p>
      </div>
      <StatusPill :label="connectionLabel" :tone="connectionTone" :icon="Radio" />
    </div>

    <div class="flex flex-wrap items-center gap-3">
      <div class="flex rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] p-0.5">
        <button
          v-for="tab in typeTabs"
          :key="tab.id"
          type="button"
          class="rounded-[6px] px-3 py-1.5 text-xs font-medium transition-colors"
          :class="typeFilter === tab.id ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]'"
          @click="typeFilter = tab.id"
        >
          {{ tab.label }}
        </button>
      </div>

      <select
        v-model="strategyFilter"
        class="rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-xs text-[var(--color-text-primary)]"
      >
        <option :value="null">All strategies</option>
        <option v-for="s in strategiesStore.strategies" :key="s.id" :value="s.id">{{ s.name }}</option>
      </select>

      <label class="flex items-center gap-1.5 text-xs text-[var(--color-text-secondary)]">
        <input v-model="showClosed" type="checkbox" class="accent-[var(--color-accent)]" />
        Show closed
      </label>

      <span class="ml-auto text-xs text-[var(--color-text-tertiary)]">{{ filteredRows.length }} position{{ filteredRows.length === 1 ? "" : "s" }}</span>
    </div>

    <div v-if="partialErrorMessage" class="flex items-center gap-2 rounded-[var(--radius-sm)] border border-[var(--color-warning-border)] bg-[var(--color-warning-bg)] px-3 py-2 text-xs text-[var(--color-warning)]">
      <TriangleAlert :size="14" class="shrink-0" />
      {{ partialErrorMessage }}
    </div>

    <BaseCard :padded="false">
      <LoadingState v-if="isLoading" />
      <ErrorState v-else-if="hasHardError" :message="tradesStore.resource.error || optionsStore.resource.error" @retry="refresh" />
      <EmptyState v-else-if="!filteredRows.length" title="No positions match these filters" />
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="border-b border-[var(--color-border)] text-left">
            <th class="label-caps px-5 py-3.5 font-normal">Instrument</th>
            <th class="label-caps px-5 py-3.5 font-normal">Strategy</th>
            <th class="label-caps px-5 py-3.5 font-normal">Status</th>
            <th class="label-caps px-5 py-3.5 font-normal">Entry</th>
            <th class="label-caps px-5 py-3.5 font-normal text-right">P&L</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in filteredRows"
            :key="row.key"
            class="border-b border-[var(--color-border)] last:border-0"
            :class="row.signalId ? 'cursor-pointer hover:bg-[var(--color-surface-hover)]' : ''"
            @click="row.signalId && $router.push(`/signals/${row.signalId}`)"
          >
            <td class="px-5 py-4">
              <div class="flex items-center gap-3">
                <div
                  class="flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-sm)] border"
                  :class="row.kind === 'equity' ? 'border-[var(--color-positive-border)] bg-[var(--color-positive-bg)]' : 'border-[var(--color-accent-border)] bg-[var(--color-accent-bg)]'"
                >
                  <component
                    :is="row.kind === 'equity' ? LineChart : Layers3"
                    :size="14"
                    :class="row.kind === 'equity' ? 'text-[var(--color-positive)]' : 'text-[var(--color-accent)]'"
                  />
                </div>
                <div>
                  <p class="font-medium text-[var(--color-text-primary)]">{{ row.instrument }}</p>
                  <p class="label-caps mt-0.5">{{ row.kind }}</p>
                </div>
              </div>
            </td>
            <td class="px-5 py-4 text-[var(--color-text-secondary)]">{{ row.strategyName }}</td>
            <td class="px-5 py-4"><StatusPill :label="row.status" :tone="statusTone(row.status)" /></td>
            <td class="px-5 py-4 text-[var(--color-text-secondary)]">{{ formatDate(row.entryDate) }}</td>
            <td class="px-5 py-4 text-right"><LivePnlCell :value="row.pnl" :is-live="row.isLive" /></td>
          </tr>
        </tbody>
      </table>
    </BaseCard>
  </div>
</template>

<script>
import { Layers3, LineChart, Radio, TriangleAlert } from "@lucide/vue"
import { useOptionsStore } from "@/stores/options"
import { useStrategiesStore } from "@/stores/strategies"
import { useTradesStore } from "@/stores/trades"
import { createQuoteStream } from "@/services/quoteStream"
import { computeEquityLivePnl, computeOptionsLivePnl } from "@/utils/livePnl"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import LivePnlCell from "@/components/positions/LivePnlCell.vue"
import { formatDate } from "@/utils/format"

const STATUS_TONE = { open: "live", pending: "warning", closing: "warning", closed: "inactive", failed: "error", skipped: "inactive" }
const POSITIONS_POLL_INTERVAL_MS = 30_000

export default {
  name: "PositionsView",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, StatusPill, LivePnlCell, TriangleAlert },
  data() {
    return {
      Radio,
      LineChart,
      Layers3,
      typeFilter: "all",
      typeTabs: [
        { id: "all", label: "All" },
        { id: "equity", label: "Equity" },
        { id: "options", label: "Options" },
      ],
      strategyFilter: null,
      showClosed: false,
      quotes: {},
      connectionState: "disconnected",
      quoteStreamHandle: null,
      subscribedKey: "",
      pollHandle: null,
    }
  },
  computed: {
    tradesStore() {
      return useTradesStore()
    },
    optionsStore() {
      return useOptionsStore()
    },
    strategiesStore() {
      return useStrategiesStore()
    },
    // A hard failure or in-flight load in ONE source must never blank out the other source's
    // already-loaded data — these only cover the "nothing to show at all yet" case; a partial
    // problem surfaces as partialErrorMessage instead, alongside whatever data IS available.
    hasAnyData() {
      return this.tradesStore.resource.data !== null || this.optionsStore.resource.data !== null
    },
    isLoading() {
      if (this.hasAnyData) return false
      return this.tradesStore.resource.status === "loading" || this.optionsStore.resource.status === "loading"
    },
    hasHardError() {
      if (this.hasAnyData) return false
      return this.tradesStore.resource.status === "error" || this.optionsStore.resource.status === "error"
    },
    partialErrorMessage() {
      if (!this.hasAnyData) return ""
      if (this.tradesStore.resource.status === "error") return `Equity trades unavailable — ${this.tradesStore.resource.error ?? "refresh failed"}`
      if (this.optionsStore.resource.status === "error") return `Options positions unavailable — ${this.optionsStore.resource.error ?? "refresh failed"}`
      return ""
    },
    equityRows() {
      return this.tradesStore.trades.map((t) => ({
        key: `equity-${t.id}`,
        kind: "equity",
        strategyId: t.strategy_id,
        strategyName: t.strategy_name,
        instrument: t.security.ticker,
        status: t.status,
        entryDate: t.entry_date,
        pnl: t.status === "open" ? computeEquityLivePnl(t, this.quotes) ?? t.pnl : t.pnl,
        isLive: t.status === "open",
        signalId: t.strategy_signal_id,
      }))
    },
    optionsRows() {
      return this.optionsStore.positions.map((p) => ({
        key: `options-${p.id}`,
        kind: "options",
        strategyId: p.strategy_id,
        strategyName: p.strategy_name,
        instrument: p.expiry_date ? `NIFTY ${formatDate(p.expiry_date)} Condor` : "NIFTY Condor",
        status: p.status,
        entryDate: p.entry_date,
        pnl: p.status === "open" ? computeOptionsLivePnl(p, this.quotes) ?? p.realized_pnl : p.realized_pnl,
        isLive: p.status === "open",
        signalId: null,
      }))
    },
    allRows() {
      return [...this.equityRows, ...this.optionsRows].sort((a, b) => (a.entryDate < b.entryDate ? 1 : -1))
    },
    filteredRows() {
      return this.allRows.filter((row) => {
        if (this.typeFilter !== "all" && row.kind !== this.typeFilter) return false
        if (this.strategyFilter !== null && row.strategyId !== this.strategyFilter) return false
        if (!this.showClosed && (row.status === "closed" || row.status === "failed" || row.status === "skipped")) return false
        return true
      })
    },
    liveTickers() {
      const equityTickers = this.tradesStore.trades.filter((t) => t.status === "open").map((t) => t.security.ticker)
      const optionTickers = this.optionsStore.positions
        .filter((p) => p.status === "open")
        .flatMap((p) => p.legs.filter((leg) => leg.status === "open").map((leg) => leg.ticker))
      return [...new Set([...equityTickers, ...optionTickers])].sort()
    },
    connectionLabel() {
      return { connecting: "Connecting", live: "Live", reconnecting: "Reconnecting", disconnected: "No live positions" }[this.connectionState]
    },
    connectionTone() {
      return { connecting: "inactive", live: "positive", reconnecting: "warning", disconnected: "inactive" }[this.connectionState]
    },
  },
  watch: {
    // The set of tickers to stream changes as positions open/close — re-subscribing only when the
    // actual key set changes (not on every unrelated re-render) avoids tearing down a healthy stream.
    liveTickers: {
      immediate: true,
      handler(tickers) {
        const key = tickers.join(",")
        if (key === this.subscribedKey) return
        this.subscribedKey = key
        this.quoteStreamHandle?.close()
        this.quoteStreamHandle = null
        if (!tickers.length) {
          this.connectionState = "disconnected"
          return
        }
        this.quoteStreamHandle = createQuoteStream(
          tickers,
          (quotes) => {
            this.quotes = { ...this.quotes, ...quotes }
          },
          (state) => {
            this.connectionState = state
          },
        )
      },
    },
  },
  created() {
    this.refresh()
    // SSE only streams prices for tickers already known to be open — a position actually
    // closing/opening mid-session needs the underlying list itself re-fetched to show up.
    this.pollHandle = setInterval(this.refresh, POSITIONS_POLL_INTERVAL_MS)
  },
  beforeUnmount() {
    this.quoteStreamHandle?.close()
    if (this.pollHandle) clearInterval(this.pollHandle)
  },
  methods: {
    formatDate,
    refresh() {
      this.tradesStore.fetch()
      this.optionsStore.fetch()
      if (this.strategiesStore.resource.status === "idle") this.strategiesStore.fetch()
    },
    statusTone(status) {
      return STATUS_TONE[status] ?? "inactive"
    },
  },
}
</script>
