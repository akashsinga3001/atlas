<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <!-- Global status strip -->
    <div class="grid grid-cols-3 gap-2.5 sm:grid-cols-6">
      <router-link to="/risk" class="surface-1 is-interactive flex items-center gap-2.5 rounded-[var(--radius-base)] px-3 py-2.5">
        <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-sm)]" :class="killSwitchStore.isActive ? 'bg-[var(--color-risk-hot)]/12 text-[var(--color-risk-hot)]' : 'bg-[var(--color-risk-calm)]/12 text-[var(--color-risk-calm)]'">
          <Power :size="14" />
        </span>
        <div class="min-w-0">
          <p class="label-caps">Trading</p>
          <p class="truncate text-[12px] font-semibold">{{ killSwitchStore.isActive ? "Blocked" : "Active" }}</p>
        </div>
      </router-link>
      <router-link to="/risk" class="surface-1 is-interactive flex items-center gap-2.5 rounded-[var(--radius-base)] px-3 py-2.5">
        <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-sm)]" :class="killSwitchStore.isActive ? 'bg-[var(--color-risk-hot)]/12 text-[var(--color-risk-hot)]' : 'bg-[var(--color-risk-calm)]/12 text-[var(--color-risk-calm)]'">
          <ShieldAlert :size="14" />
        </span>
        <div class="min-w-0">
          <p class="label-caps">Kill switch</p>
          <p class="truncate text-[12px] font-semibold">{{ killSwitchStore.isActive ? "Active" : "Off" }}</p>
        </div>
      </router-link>
      <router-link to="/risk" class="surface-1 is-interactive flex items-center gap-2.5 rounded-[var(--radius-base)] px-3 py-2.5">
        <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-sm)]" :class="anyBreakerTriggered ? 'bg-[var(--color-risk-hot)]/12 text-[var(--color-risk-hot)]' : 'bg-[var(--color-risk-calm)]/12 text-[var(--color-risk-calm)]'">
          <Zap :size="14" />
        </span>
        <div class="min-w-0">
          <p class="label-caps">Circuit breaker</p>
          <p class="truncate text-[12px] font-semibold">{{ anyBreakerTriggered ? "Breached" : "Normal" }}</p>
        </div>
      </router-link>
      <router-link to="/market" class="surface-1 is-interactive flex items-center gap-2.5 rounded-[var(--radius-base)] px-3 py-2.5">
        <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-sm)]" :class="marketSession === 'open' ? 'bg-[var(--color-risk-calm)]/12 text-[var(--color-risk-calm)]' : 'bg-[var(--color-inactive)]/12 text-[var(--color-inactive)]'">
          <Activity :size="14" />
        </span>
        <div class="min-w-0">
          <p class="label-caps">Market</p>
          <p class="truncate text-[12px] font-semibold capitalize">{{ marketSession.replace("-", " ") }}</p>
        </div>
      </router-link>
      <router-link to="/data-pipeline" class="surface-1 is-interactive flex items-center gap-2.5 rounded-[var(--radius-base)] px-3 py-2.5">
        <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-sm)]" :class="dataStale ? 'bg-[var(--color-risk-elevated)]/12 text-[var(--color-risk-elevated)]' : 'bg-[var(--color-risk-calm)]/12 text-[var(--color-risk-calm)]'">
          <Database :size="14" />
        </span>
        <div class="min-w-0">
          <p class="label-caps">Data</p>
          <p class="truncate text-[12px] font-semibold">{{ dataStale ? "Stale" : "Current" }}</p>
        </div>
      </router-link>
      <router-link to="/operations/jobs" class="surface-1 is-interactive flex items-center gap-2.5 rounded-[var(--radius-base)] px-3 py-2.5">
        <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-[var(--radius-sm)]" :class="anyJobFailed ? 'bg-[var(--color-risk-hot)]/12 text-[var(--color-risk-hot)]' : 'bg-[var(--color-risk-calm)]/12 text-[var(--color-risk-calm)]'">
          <Cpu :size="14" />
        </span>
        <div class="min-w-0">
          <p class="label-caps">System</p>
          <p class="truncate text-[12px] font-semibold">{{ anyJobFailed ? "Degraded" : "Healthy" }}</p>
        </div>
      </router-link>
    </div>

    <AttentionFeed :items="dashboardStore.attentionItems" />

    <!-- Portfolio summary — the one content-area anchor carrying the sidebar's black identity;
         deliberately scoped to this single, most-important card, not spread across the page. -->
    <section class="animate-fade rounded-[var(--radius-lg)] border p-4" style="background: var(--color-sidebar-bg); border-color: var(--color-sidebar-border); box-shadow: var(--shadow-floating), inset 0 1px 0 rgba(255, 255, 255, 0.06)">
      <header class="mb-3 flex items-center justify-between gap-2">
        <div class="flex items-center gap-1.5">
          <LineChart :size="14" class="text-white" />
          <h2 class="text-[11px] font-semibold uppercase tracking-wide text-white">Portfolio</h2>
        </div>
        <StaleBadge :last-updated-at="statsStore.resource.lastUpdatedAt" :has-error="statsStore.resource.status === 'error'" class="!text-white/50" />
      </header>
      <LoadingState v-if="statsStore.resource.status === 'loading'" />
      <ErrorState v-else-if="statsStore.resource.status === 'error' && !statsStore.resource.data" :message="statsStore.resource.error" @retry="refreshAll" />
      <div v-else-if="statsStore.resource.data" class="grid grid-cols-1 gap-5 lg:grid-cols-3">
        <div class="lg:col-span-2 grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wide text-white">NAV</p>
            <p class="figure-hero mt-1 text-2xl text-white">{{ formatCurrency(currentNav, { compact: true }) }}</p>
          </div>
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wide text-white">Total return</p>
            <p class="figure-hero mt-1 text-2xl" :class="pnlClassOnDark(statsStore.resource.data.true_return_pct)">{{ formatPercent(statsStore.resource.data.true_return_pct) }}</p>
          </div>
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wide text-white">Cash</p>
            <p class="font-mono-nums mt-1.5 text-[19px] font-semibold text-white">{{ formatCurrency(currentCash, { compact: true }) }}</p>
          </div>
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wide text-white">Deployed</p>
            <p class="font-mono-nums mt-1.5 text-[19px] font-semibold text-white">{{ formatCurrency(currentHoldings, { compact: true }) }}</p>
          </div>
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wide text-white">Drawdown</p>
            <p class="font-mono-nums mt-1.5 text-[19px] font-semibold" style="color: var(--color-risk-hot)">{{ statsStore.resource.data.max_drawdown_pct !== null ? `${statsStore.resource.data.max_drawdown_pct}%` : "—" }}</p>
          </div>
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wide text-white">Sharpe</p>
            <p class="font-mono-nums mt-1.5 text-[19px] font-semibold text-white">{{ statsStore.resource.data.sharpe_ratio ?? "—" }}</p>
          </div>
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wide text-white">Win rate</p>
            <p class="font-mono-nums mt-1.5 text-[19px] font-semibold text-white">{{ statsStore.resource.data.win_rate !== null ? `${statsStore.resource.data.win_rate}%` : "—" }}</p>
          </div>
          <div>
            <p class="text-[11px] font-semibold uppercase tracking-wide text-white">Open trades</p>
            <p class="font-mono-nums mt-1.5 text-[19px] font-semibold text-white">{{ statsStore.resource.data.open_trades }}</p>
          </div>
        </div>
        <div class="flex flex-col justify-center border-t border-white/10 pt-4 lg:border-l lg:border-t-0 lg:pl-6 lg:pt-0">
          <p class="text-[11px] font-semibold uppercase tracking-wide text-white">NAV trend</p>
          <PriceChart v-if="navSeries[0]?.data.length > 1" :series="navSeries" :height="90" />
          <p v-else class="mt-3 text-[11.5px] text-white/40">Not enough history to chart yet</p>
        </div>
      </div>
    </section>

    <!-- Active positions + Strategy activity — Strategy activity stays a fixed h-80 (its content
         is naturally capped), but Active positions grows to fit every open position rather than
         capping at a few rows and pointing at the Trades table for the rest: that page mixes
         open and closed trades together and has no live P&L, so it can't stand in as "the rest
         of the positions view." This is the one place that shows every open position with P&L. -->
    <div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
      <BaseCard title="Active positions" :icon="Wallet" class="xl:col-span-2" :padded="false">
        <div class="px-4 pb-2">
          <p class="label-caps">Equity</p>
        </div>
        <EmptyState v-if="!openEquityTrades.length" title="No open equity trades" description="Equity positions will appear here once a strategy enters one." />
        <div v-else class="overflow-x-auto px-4">
          <table class="data-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Strategy</th>
                <th>Entry</th>
                <th class="num">Qty</th>
                <th class="num">Entry price</th>
                <th class="num">P&amp;L</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in openEquityTrades" :key="t.id" class="cursor-pointer" @click="$router.push(`/trades/${t.id}`)">
                <td class="font-medium">{{ t.security.ticker }}</td>
                <td>{{ t.strategy_name }}</td>
                <td>{{ formatDate(t.entry_date) }}</td>
                <td class="num font-mono-nums">{{ t.fill_quantity ?? "—" }}</td>
                <td class="num font-mono-nums">{{ t.fill_price !== null ? formatCurrency(t.fill_price) : "—" }}</td>
                <td class="num font-mono-nums" :class="pnlClass(equityLivePnl(t))">{{ equityLivePnl(t) !== null ? formatCurrency(equityLivePnl(t), { signed: true }) : "—" }}</td>
                <td><StatusPill :label="t.status" :tone="t.status === 'open' ? 'live' : 'inactive'" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </BaseCard>

      <BaseCard title="Strategy activity" :icon="ListChecks" class="h-80">
        <LoadingState v-if="strategiesStore.resource.status === 'loading'" />
        <div v-else class="flex flex-col divide-y divide-[var(--color-border)]">
          <router-link v-for="s in strategiesStore.strategies" :key="s.id" :to="`/strategies/${s.id}`" class="flex flex-col gap-1.5 py-2.5 first:pt-0 last:pb-0 hover:opacity-80">
            <div class="flex items-center justify-between gap-2">
              <span class="text-[12.5px] font-medium">{{ s.name }}</span>
              <StatusPill :label="s.is_active ? 'Active' : 'Disabled'" :tone="s.is_active ? 'live' : 'inactive'" />
            </div>
            <p class="text-[11.5px] text-[var(--color-text-tertiary)]">
              {{ s.active_version ? `v${s.active_version.version}` : "no version" }} · last run {{ s.last_run_at ? formatDateTime(s.last_run_at) : "never" }} · {{ s.open_positions_count }} open
            </p>
          </router-link>
        </div>
      </BaseCard>
    </div>

    <!-- Today's activity + Operations health + Market snapshot — fixed, equal height; each
         card's body scrolls internally rather than the row stretching to its tallest card. -->
    <div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
      <BaseCard title="Today's activity" :icon="History" class="h-64">
        <EmptyState v-if="!todaysActivity.length" title="No activity yet today" />
        <div v-else class="flex flex-col divide-y divide-[var(--color-border)]">
          <div v-for="(item, i) in todaysActivity" :key="i" class="flex items-start gap-2.5 py-2 first:pt-0 last:pb-0">
            <span class="font-mono-nums mt-0.5 shrink-0 text-[11px] text-[var(--color-text-tertiary)]">{{ item.time }}</span>
            <div class="min-w-0">
              <p class="truncate text-[12px] text-[var(--color-text-primary)]">{{ item.text }}</p>
            </div>
          </div>
        </div>
      </BaseCard>

      <BaseCard title="Operations health" :icon="Cpu" class="h-64">
        <router-link to="/operations/jobs" class="mb-3 flex items-center gap-4 text-[12px]">
          <span class="text-[var(--color-positive)]">{{ jobsSuccessCount }} successful</span>
          <span v-if="jobsFailedCount > 0" class="text-[var(--color-negative)]">{{ jobsFailedCount }} failed</span>
        </router-link>
        <div class="flex flex-col divide-y divide-[var(--color-border)]">
          <div v-for="j in keyJobs" :key="j.name" class="flex items-center justify-between py-1.5 text-[12px] first:pt-0 last:pb-0">
            <span class="text-[var(--color-text-secondary)]">{{ j.display_name }}</span>
            <span class="font-mono-nums text-[var(--color-text-tertiary)]">{{ j.last_run_at ? formatDateTime(j.last_run_at) : "never" }}</span>
          </div>
        </div>
      </BaseCard>

      <MarketSentimentCard :resource="marketStore.resource" @retry="refreshAll" class="h-64" />
    </div>
  </div>
</template>

<script>
import { Activity, Cpu, Database, History, LineChart, ListChecks, Power, ShieldAlert, Wallet, Zap } from "@lucide/vue"
import { useCircuitBreakersStore } from "@/stores/circuitBreakers"
import { useDashboardStore } from "@/stores/dashboard"
import { useEquityCurveStore } from "@/stores/equityCurve"
import { useJobsStore } from "@/stores/jobs"
import { useKillSwitchStore } from "@/stores/killSwitch"
import { useMarketStore } from "@/stores/market"
import { usePageHeaderStore } from "@/stores/pageHeader"
import { usePortfolioStatsStore } from "@/stores/portfolioStats"
import { useStrategiesStore } from "@/stores/strategies"
import { useTradesStore } from "@/stores/trades"

import AttentionFeed from "@/components/dashboard/AttentionFeed.vue"
import MarketSentimentCard from "@/components/dashboard/MarketSentimentCard.vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import MetricTile from "@/components/primitives/MetricTile.vue"
import PriceChart from "@/components/primitives/PriceChart.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { createQuoteStream } from "@/services/quoteStream"
import { formatCurrency, formatDate, formatDateTime, formatPercent, pnlTone } from "@/utils/format"
import { computeEquityLivePnl } from "@/utils/livePnl"
import { getMarketSession } from "@/utils/marketHours"

const REFRESH_INTERVAL_MS = 30_000
const KEY_JOB_NAMES = ["STRATEGY_EXECUTION", "TRADE_ENTRY", "TRADE_EXIT", "POSITION_SYNC", "DAILY_ACCOUNT_SNAPSHOT"]

export default {
  name: "OverviewView",
  components: { AttentionFeed, MarketSentimentCard, BaseCard, EmptyState, ErrorState, LineChart, LoadingState, MetricTile, PriceChart, StaleBadge, StatusPill, Power, ShieldAlert, Zap, Activity, Database },
  data() {
    return { LineChart, Wallet, ListChecks, History, Cpu, refreshHandle: null, quotes: {}, quoteState: "connecting", streamHandle: null }
  },
  computed: {
    dashboardStore() {
      return useDashboardStore()
    },
    strategiesStore() {
      return useStrategiesStore()
    },
    marketStore() {
      return useMarketStore()
    },
    statsStore() {
      return usePortfolioStatsStore()
    },
    curveStore() {
      return useEquityCurveStore()
    },
    killSwitchStore() {
      return useKillSwitchStore()
    },
    breakersStore() {
      return useCircuitBreakersStore()
    },
    jobsStore() {
      return useJobsStore()
    },
    tradesStore() {
      return useTradesStore()
    },
    marketSession() {
      return getMarketSession()
    },
    anyBreakerTriggered() {
      return this.breakersStore.breakers.some((b) => b.enabled && b.last_triggered_at)
    },
    anyJobFailed() {
      return this.jobsStore.jobs.some((j) => j.last_run_status === "failure")
    },
    dataStale() {
      const pipeline = this.jobsStore.jobs.find((j) => j.name === "OHLCV_IMPORT")
      if (!pipeline?.last_run_at) return true
      const ageMs = Date.now() - new Date(pipeline.last_run_at).getTime()
      return ageMs > 36 * 60 * 60 * 1000
    },
    latestNavPoint() {
      const nav = this.curveStore.nav.data ?? []
      return nav.length ? nav[nav.length - 1] : null
    },
    currentNav() {
      return this.latestNavPoint?.total_value ?? null
    },
    currentCash() {
      return this.latestNavPoint?.cash_balance ?? null
    },
    currentHoldings() {
      return this.latestNavPoint?.holdings_value ?? null
    },
    navSeries() {
      return [{ name: "NAV", color: "#1f8a5c", data: (this.curveStore.nav.data ?? []).map((p) => ({ time: p.date, value: p.total_value })) }]
    },
    openEquityTrades() {
      return this.tradesStore.openOrPending
    },
    jobsSuccessCount() {
      return this.jobsStore.jobs.filter((j) => j.last_run_status === "success").length
    },
    jobsFailedCount() {
      return this.jobsStore.jobs.filter((j) => j.last_run_status === "failure").length
    },
    keyJobs() {
      return this.jobsStore.jobs.filter((j) => KEY_JOB_NAMES.includes(j.name))
    },
    todaysActivity() {
      const today = new Date().toISOString().slice(0, 10)
      const items = []
      for (const j of this.jobsStore.jobs) {
        if (j.last_run_at && j.last_run_at.slice(0, 10) === today) {
          items.push({ ts: j.last_run_at, time: formatDateTime(j.last_run_at).split(", ").pop(), text: `${j.display_name} — ${j.last_run_status === "success" ? "completed" : j.last_run_status}` })
        }
      }
      for (const t of this.tradesStore.trades) {
        if (t.entry_date === today) items.push({ ts: t.entry_date, time: "", text: `${t.strategy_name} entered ${t.security.ticker}` })
        if (t.exit_date === today) items.push({ ts: t.exit_date, time: "", text: `${t.strategy_name} exited ${t.security.ticker}` })
      }
      return items.sort((a, b) => (a.ts < b.ts ? 1 : -1)).slice(0, 10)
    },
  },
  async created() {
    usePageHeaderStore().set("Overview", "Atlas trading desk")
    await this.refreshAll()
    this.refreshHandle = setInterval(this.refreshAll, REFRESH_INTERVAL_MS)
    this.startQuoteStream()
  },
  beforeUnmount() {
    if (this.refreshHandle) clearInterval(this.refreshHandle)
    this.streamHandle?.close()
  },
  methods: {
    formatCurrency,
    formatPercent,
    formatDate,
    formatDateTime,
    startQuoteStream() {
      const tickers = [...new Set(this.openEquityTrades.map((t) => t.security.ticker))]
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
    equityLivePnl(trade) {
      return trade.pnl ?? computeEquityLivePnl(trade, this.quotes)
    },
    pnlClass(value) {
      const tone = pnlTone(value)
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return ""
    },
    // Same tone logic, but with an explicit white fallback for the black Portfolio card — the
    // shared pnlClass() returns '' for the neutral case, which would inherit invisible dark
    // text on that card instead of falling back to something visible.
    pnlClassOnDark(value) {
      const tone = pnlTone(value)
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return "text-white"
    },
    refreshAll() {
      return this.dashboardStore.fetchAll()
    },
  },
}
</script>
