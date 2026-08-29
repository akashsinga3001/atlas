<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <router-link to="/options" class="inline-flex w-fit items-center gap-1 text-xs text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]">
      <ArrowLeft :size="12" />
      Options
    </router-link>

    <LoadingState v-if="resource.status === 'loading'" />
    <ErrorState v-else-if="resource.status === 'error' && !position" :message="resource.error" @retry="load" />
    <EmptyState v-else-if="!position" title="Options position not found" />

    <template v-else>
      <div class="flex items-center justify-between">
        <div>
          <h2 class="font-display text-xl font-semibold tracking-tight">{{ underlyingLabel }}</h2>
          <p class="mt-0.5 text-xs text-[var(--color-text-tertiary)]">{{ position.strategy_name }} · expiry {{ formatDate(position.expiry_date) }}</p>
        </div>
        <StatusPill :label="position.status" :tone="statusTone(position.status)" />
      </div>

      <!-- Lifecycle -->
      <div class="flex items-center gap-1.5 text-[11px]">
        <template v-for="(stage, i) in lifecycleStages" :key="stage">
          <span
            class="rounded-[var(--radius-sm)] px-2 py-1 font-medium"
            :class="stageClass(stage)"
          >{{ stage }}</span>
          <ChevronRight v-if="i < lifecycleStages.length - 1" :size="12" class="text-[var(--color-text-tertiary)]" />
        </template>
        <span v-if="isTerminalNonClosed" class="ml-2 rounded-[var(--radius-sm)] bg-[var(--color-error-bg)] px-2 py-1 font-medium text-[var(--color-error)]">{{ position.status }}</span>
      </div>

      <BaseCard>
        <div class="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
          <MetricTile label="Spot at signal" :value="formatCurrency(position.spot_at_signal)" />
          <MetricTile label="Entry date" :value="formatDate(position.entry_date)" />
          <MetricTile label="Planned exit" :value="position.planned_exit_date ? formatDate(position.planned_exit_date) : '—'" />
          <MetricTile label="Exit date" :value="position.exit_date ? formatDate(position.exit_date) : '—'" />
          <MetricTile
            label="Net P&amp;L"
            :value="position.realized_pnl !== null ? formatCurrency(position.realized_pnl, { signed: true }) : livePnl !== null ? formatCurrency(livePnl, { signed: true }) : '—'"
            :sublabel="position.realized_pnl === null && livePnl !== null ? 'Unrealized, live' : ''"
            :tone="tileTone(position.realized_pnl ?? livePnl)"
          />
          <MetricTile label="Margin" :value="position.margin_total !== null ? formatCurrency(position.margin_total) : '—'" />
          <MetricTile label="Net credit" :value="position.net_credit_total !== null ? formatCurrency(position.net_credit_total) : '—'" />
          <MetricTile label="Lots" :value="`${position.lots ?? '—'} × ${position.lot_size ?? '—'}`" />
        </div>
        <p v-if="position.skip_reason" class="mt-4 rounded-[var(--radius-sm)] bg-[var(--color-warning-bg)] px-3 py-2 text-[12px] text-[var(--color-warning)]">{{ position.skip_reason }}</p>
      </BaseCard>

      <BaseCard title="Legs" :icon="Layers3">
        <template #header-actions>
          <span v-if="position.status === 'open'" class="flex items-center gap-1.5 text-[11px] text-[var(--color-text-tertiary)]">
            <span class="h-1.5 w-1.5 rounded-full" :class="quoteState === 'live' ? 'bg-[var(--color-risk-calm)]' : 'bg-[var(--color-risk-elevated)]'" />
            {{ quoteState === "live" ? "Live" : quoteState === "connecting" ? "Connecting…" : "Reconnecting…" }}
          </span>
        </template>
        <PositionLegTable :legs="position.legs" :quotes="quotes" />
      </BaseCard>
    </template>
  </div>
</template>

<script>
import { ArrowLeft, ChevronRight, Layers3 } from "@lucide/vue"
import { fetchOptionsPositions } from "@/services/api/options"
import { usePageHeaderStore } from "@/stores/pageHeader"
import { createQuoteStream } from "@/services/quoteStream"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import MetricTile from "@/components/primitives/MetricTile.vue"
import PositionLegTable from "@/components/primitives/PositionLegTable.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { computeOptionsLivePnl } from "@/utils/livePnl"
import { formatCurrency, formatDate, pnlTone } from "@/utils/format"

const LIFECYCLE = ["pending", "open", "closing", "closed"]
const STATUS_TONES = { open: "live", closing: "warning", closed: "inactive", pending: "info", failed: "error", skipped: "inactive" }

export default {
  name: "OptionsDetailView",
  components: { ArrowLeft, ChevronRight, BaseCard, EmptyState, ErrorState, LoadingState, MetricTile, PositionLegTable, StatusPill },
  data() {
    return {
      Layers3,
      resource: { status: "idle", data: null, error: null },
      quotes: {},
      quoteState: "connecting",
      streamHandle: null,
    }
  },
  computed: {
    position() {
      const id = Number(this.$route.params.id)
      return (this.resource.data ?? []).find((p) => p.id === id) ?? null
    },
    livePnl() {
      return this.position ? computeOptionsLivePnl(this.position, this.quotes) : null
    },
    lifecycleStages() {
      return LIFECYCLE
    },
    isTerminalNonClosed() {
      return this.position && (this.position.status === "failed" || this.position.status === "skipped")
    },
    underlyingLabel() {
      const p = this.position
      if (!p) return ""
      const parts = []
      if (p.call_short_strike) parts.push(`${p.call_short_strike}CE`)
      if (p.put_short_strike) parts.push(`${p.put_short_strike}PE`)
      return parts.length ? `Iron Condor ${parts.join(" / ")}` : `Position #${p.id}`
    },
  },
  created() {
    usePageHeaderStore().set("Options position")
    this.load()
  },
  beforeUnmount() {
    this.streamHandle?.close()
  },
  methods: {
    formatCurrency,
    formatDate,
    statusTone(status) {
      return STATUS_TONES[status] ?? "inactive"
    },
    tileTone(value) {
      const tone = pnlTone(value)
      return tone === "inactive" ? "neutral" : tone
    },
    stageClass(stage) {
      if (this.isTerminalNonClosed) return "bg-[var(--color-inactive-bg)] text-[var(--color-text-tertiary)]"
      const currentIndex = LIFECYCLE.indexOf(this.position.status)
      const stageIndex = LIFECYCLE.indexOf(stage)
      if (stageIndex < currentIndex) return "bg-[var(--color-positive-bg)] text-[var(--color-positive)]"
      if (stageIndex === currentIndex) return "bg-[var(--color-accent-bg)] text-[var(--color-accent)]"
      return "bg-[var(--color-inactive-bg)] text-[var(--color-text-tertiary)]"
    },
    async load() {
      this.resource.status = "loading"
      const result = await fetchOptionsPositions()
      if (result.error) {
        this.resource.status = "error"
        this.resource.error = result.message
        return
      }
      this.resource.data = result.data
      this.resource.status = "success"
      if (this.position) {
        usePageHeaderStore().set(this.underlyingLabel, this.position.strategy_name)
        this.startQuoteStream()
      }
    },
    startQuoteStream() {
      if (this.streamHandle || this.position.status !== "open") return
      const tickers = this.position.legs.filter((l) => l.status === "open").map((l) => l.ticker)
      if (!tickers.length) return
      this.streamHandle = createQuoteStream(
        tickers,
        (quotes) => {
          this.quotes = quotes
        },
        (state) => {
          this.quoteState = state
        },
      )
    },
  },
}
</script>
