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

    <!-- Row 1: Portfolio Value (wide) · Key Metrics · Today's P&L -->
    <div class="grid grid-cols-1 gap-4 xl:grid-cols-4">
      <PortfolioValueCard
        class="xl:col-span-2"
        :loading="statsStore.resource.status === 'loading'"
        :last-updated-at="portfolioCardLastUpdatedAt"
        :has-error="portfolioCardHasError"
        :nav="currentNav"
        :cash="currentCash"
        :deployed="currentHoldings"
        :positions="statsStore.resource.data?.open_trades ?? 0"
        :today-delta="todayPnlStore.resource.data?.total_today ?? null"
        :today-delta-pct="livePnlPct"
        :nav-series="curveStore.nav.data ?? []"
      />
      <KeyMetricsCard
        :loading="statsStore.resource.status === 'loading'"
        :last-updated-at="statsStore.resource.lastUpdatedAt"
        :has-error="statsStore.resource.status === 'error'"
        :true-return-pct="statsStore.resource.data?.true_return_pct ?? null"
        :win-rate="statsStore.resource.data?.win_rate ?? null"
        :profit-factor="statsStore.resource.data?.profit_factor ?? null"
        :sharpe-ratio="statsStore.resource.data?.sharpe_ratio ?? null"
        :max-drawdown-pct="statsStore.resource.data?.max_drawdown_pct ?? null"
        :avg-win-pct="statsStore.resource.data?.avg_win_pct ?? null"
        :avg-loss-pct="statsStore.resource.data?.avg_loss_pct ?? null"
        :avg-holding-days="statsStore.resource.data?.avg_holding_days ?? null"
        :closed-trades="statsStore.resource.data?.closed_trades ?? 0"
      />
      <TodaysPnlCard
        :loading="todayPnlStore.resource.status === 'loading'"
        :last-updated-at="todayPnlStore.resource.lastUpdatedAt"
        :has-error="todayPnlStore.resource.status === 'error'"
        :total="todayPnlStore.resource.data?.total_today ?? totalLivePnl"
        :total-pnl="statsStore.resource.data?.total_pnl ?? null"
        :realized-today="todayPnlStore.resource.data?.realized_today ?? null"
        :unrealized-now="todayPnlStore.resource.data?.unrealized_now ?? null"
        :winners="winnersCount"
        :losers="losersCount"
        :breakeven="breakevenCount"
        :nav="currentNav"
        :cash="currentCash"
        :deployed="currentHoldings"
      />
    </div>

    <!-- Row 2: Active positions (wide) · Sector exposure sidebar -->
    <div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
      <BaseCard title="Active Positions" :icon="Wallet" :padded="false" class="xl:col-span-2">
        <template #header-actions>
          <div class="flex items-center gap-2">
            <input v-model="positionSearch" type="text" placeholder="Search positions…" class="filter-control w-40" />
            <button type="button" class="flex items-center gap-1.5 rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] px-2.5 py-1.5 text-[11.5px] font-medium text-[var(--color-text-secondary)] hover:text-[var(--color-text-primary)]" @click="exportPositionsCsv" :disabled="!filteredEquityTrades.length">
              <Download :size="12" />
              Export
            </button>
          </div>
        </template>
        <div class="flex flex-wrap items-center justify-between gap-2 px-4 pb-2">
          <p class="label-caps">Equity</p>
          <div v-if="openEquityTrades.length" class="flex items-center gap-4 text-[11.5px]">
            <span><span class="text-[var(--color-positive)]">{{ winnersCount }} up</span> <span class="text-[var(--color-text-tertiary)]">·</span> <span class="text-[var(--color-negative)]">{{ losersCount }} down</span></span>
            <span v-if="bestMover" class="text-[var(--color-text-tertiary)]">Best <span class="text-[var(--color-positive)] font-medium">{{ bestMover.ticker }} {{ formatPercent(bestMover.pnlPct) }}</span></span>
            <span v-if="worstMover" class="text-[var(--color-text-tertiary)]">Worst <span class="text-[var(--color-negative)] font-medium">{{ worstMover.ticker }} {{ formatPercent(worstMover.pnlPct) }}</span></span>
            <span v-if="avgPositionAgeDays !== null" class="text-[var(--color-text-tertiary)]">Avg age {{ avgPositionAgeDays.toFixed(1) }}d</span>
          </div>
        </div>
        <EmptyState v-if="!openEquityTrades.length" title="No open equity trades" description="Equity positions will appear here once a strategy enters one." />
        <EmptyState v-else-if="!filteredEquityTrades.length" title="No positions match your search" />
        <div v-else class="overflow-x-auto px-4">
          <table class="data-table positions-table">
            <thead>
              <tr>
                <th>Symbol</th>
                <th>Strategy</th>
                <th>Entry</th>
                <th class="num">Qty</th>
                <th class="num">Avg Price</th>
                <th class="num">LTP</th>
                <th class="num">P&amp;L</th>
                <th class="num">Return</th>
                <th>Weight</th>
                <th class="num">Age</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in sortedEquityTrades" :key="t.id" class="cursor-pointer" @click="$router.push(`/trades/${t.id}`)">
                <td>
                  <div class="flex items-center gap-2">
                    <Clock v-if="t.status === 'pending'" :size="12" class="text-[var(--color-warning)]" title="Order pending fill" />
                    <ArrowUpCircle v-else-if="equityLivePnl(t) > 0" :size="12" class="text-[var(--color-positive)]" />
                    <ArrowDownCircle v-else-if="equityLivePnl(t) < 0" :size="12" class="text-[var(--color-negative)]" />
                    <span class="font-medium">{{ t.security.ticker }}</span>
                  </div>
                </td>
                <td class="max-w-[140px] truncate text-[var(--color-text-secondary)]" :title="t.strategy_name">{{ t.strategy_name }}</td>
                <td class="text-[var(--color-text-secondary)]">{{ formatDate(t.entry_date) }}</td>
                <td class="num font-mono-nums">{{ t.fill_quantity ?? "—" }}</td>
                <td class="num font-mono-nums">{{ t.fill_price !== null ? formatCurrency(t.fill_price) : "—" }}</td>
                <td class="num font-mono-nums">{{ ltpFor(t) !== null ? formatCurrency(ltpFor(t)) : "—" }}</td>
                <td class="num font-mono-nums font-semibold" :class="pnlClass(equityLivePnl(t))">{{ equityLivePnl(t) !== null ? formatCurrency(equityLivePnl(t), { signed: true }) : "—" }}</td>
                <td class="num font-mono-nums" :class="pnlClass(positionReturnPct(t))">{{ positionReturnPct(t) !== null ? formatPercent(positionReturnPct(t)) : "—" }}</td>
                <td>
                  <div v-if="positionWeightPct(t) !== null" class="flex items-center gap-1.5">
                    <div class="h-1.5 w-12 shrink-0 overflow-hidden rounded-full bg-[var(--color-surface-alt)]">
                      <div class="h-full rounded-full bg-[var(--color-accent)]" :style="{ width: `${Math.min(positionWeightPct(t), 100)}%` }" />
                    </div>
                    <span class="font-mono-nums shrink-0 text-[var(--color-text-tertiary)]">{{ positionWeightPct(t).toFixed(1) }}%</span>
                  </div>
                  <span v-else>—</span>
                </td>
                <td class="num font-mono-nums text-[var(--color-text-secondary)]">{{ positionAgeDays(t) }}d</td>
              </tr>
            </tbody>
          </table>
        </div>
      </BaseCard>

      <SectorExposureCard :resource="sectorExposureStore.resource" @retry="sectorExposureStore.fetch" />
    </div>

    <!-- Row 3: Trade log (wide) · Strategy performance -->
    <div class="grid grid-cols-1 gap-4 xl:grid-cols-3">
      <RecentActivityCard class="xl:col-span-2" :items="todaysTrades" />
      <StrategyPerformanceCard :resource="strategyPerformanceStore.resource" @retry="strategyPerformanceStore.fetch" />
    </div>

    <!-- Row 4: Strategy activity + Market snapshot -->
    <div class="grid grid-cols-1 gap-4 xl:grid-cols-2">
      <BaseCard title="Strategy activity" :icon="ListChecks" class="min-h-[18rem]">
        <LoadingState v-if="strategiesStore.resource.status === 'loading'" />
        <div v-else class="flex h-full flex-col justify-center divide-y divide-[var(--color-border)]">
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

      <MarketSentimentCard :resource="marketStore.resource" @retry="refreshAll" class="min-h-[18rem]" />
    </div>
  </div>
</template>

<script>
import { Activity, ArrowDownCircle, ArrowUpCircle, Clock, Cpu, Database, Download, ListChecks, Power, ShieldAlert, Wallet, Zap } from "@lucide/vue"
import { useCircuitBreakersStore } from "@/stores/circuitBreakers"
import { useDashboardStore } from "@/stores/dashboard"
import { useEquityCurveStore } from "@/stores/equityCurve"
import { useJobsStore } from "@/stores/jobs"
import { useKillSwitchStore } from "@/stores/killSwitch"
import { useLiveAccountStore } from "@/stores/liveAccount"
import { useMarketStore } from "@/stores/market"
import { usePageHeaderStore } from "@/stores/pageHeader"
import { usePortfolioStatsStore } from "@/stores/portfolioStats"
import { useSectorExposureStore } from "@/stores/sectorExposure"
import { useStrategiesStore } from "@/stores/strategies"
import { useStrategyPerformanceStore } from "@/stores/strategyPerformance"
import { useTodayPnlStore } from "@/stores/todayPnl"
import { useTradesStore } from "@/stores/trades"

import AttentionFeed from "@/components/dashboard/AttentionFeed.vue"
import KeyMetricsCard from "@/components/dashboard/KeyMetricsCard.vue"
import MarketSentimentCard from "@/components/dashboard/MarketSentimentCard.vue"
import PortfolioValueCard from "@/components/dashboard/PortfolioValueCard.vue"
import RecentActivityCard from "@/components/dashboard/RecentActivityCard.vue"
import SectorExposureCard from "@/components/dashboard/SectorExposureCard.vue"
import StrategyPerformanceCard from "@/components/dashboard/StrategyPerformanceCard.vue"
import TodaysPnlCard from "@/components/dashboard/TodaysPnlCard.vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { createQuoteStream } from "@/services/quoteStream"
import { formatCurrency, formatDate, formatDateTime, formatPercent, pnlTone, todayIST } from "@/utils/format"
import { computeEquityLivePnl } from "@/utils/livePnl"
import { getMarketSession } from "@/utils/marketHours"

const REFRESH_INTERVAL_MS = 30_000

export default {
  name: "OverviewView",
  components: {
    AttentionFeed, KeyMetricsCard, MarketSentimentCard, PortfolioValueCard, RecentActivityCard, SectorExposureCard, StrategyPerformanceCard, TodaysPnlCard,
    BaseCard, EmptyState, LoadingState, StatusPill, Power, ShieldAlert, Zap, Activity, Database, Cpu, Download, ArrowUpCircle, ArrowDownCircle, Clock,
  },
  data() {
    return { Wallet, ListChecks, refreshHandle: null, quotes: {}, quoteState: "connecting", streamHandle: null, subscribedTickers: [], positionSearch: "" }
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
    liveAccountStore() {
      return useLiveAccountStore()
    },
    sectorExposureStore() {
      return useSectorExposureStore()
    },
    strategyPerformanceStore() {
      return useStrategyPerformanceStore()
    },
    todayPnlStore() {
      return useTodayPnlStore()
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
    currentNav() {
      return this.liveAccountStore.resource.data?.total_value ?? null
    },
    currentCash() {
      return this.liveAccountStore.resource.data?.cash_balance ?? null
    },
    currentHoldings() {
      return this.liveAccountStore.resource.data?.holdings_value ?? null
    },
    portfolioCardLastUpdatedAt() {
      const stats = this.statsStore.resource.lastUpdatedAt
      const live = this.liveAccountStore.resource.lastUpdatedAt
      if (stats === null) return live
      if (live === null) return stats
      return Math.min(stats, live)
    },
    portfolioCardHasError() {
      return this.statsStore.resource.status === "error" || this.liveAccountStore.resource.status === "error"
    },
    avgPositionAgeDays() {
      if (!this.openEquityTrades.length) return null
      const today = new Date()
      const ages = this.openEquityTrades.map((t) => (today - new Date(t.entry_date)) / 86400000)
      return ages.reduce((sum, a) => sum + a, 0) / ages.length
    },
    openEquityTrades() {
      return this.tradesStore.openOrPending
    },
    filteredEquityTrades() {
      const q = this.positionSearch.trim().toLowerCase()
      if (!q) return this.openEquityTrades
      return this.openEquityTrades.filter((t) => t.security.ticker.toLowerCase().includes(q) || t.strategy_name.toLowerCase().includes(q))
    },
    // Biggest movers (winners and losers) surface first — the table is a "what needs my
    // attention" view, not a ledger, so ordering by live P&L magnitude beats entry-date order.
    sortedEquityTrades() {
      return [...this.filteredEquityTrades].sort((a, b) => Math.abs(this.equityLivePnl(b) ?? 0) - Math.abs(this.equityLivePnl(a) ?? 0))
    },
    // Live unrealized P&L across every open position, from the same SSE quote stream that
    // drives Active positions' own per-row P&L — genuinely live, not the historical
    // true_return_pct (Modified Dietz, EOD-snapshot-based) that belongs on Portfolio instead.
    totalLivePnl() {
      const values = this.openEquityTrades.map((t) => this.equityLivePnl(t)).filter((v) => v !== null)
      return values.length ? values.reduce((sum, v) => sum + v, 0) : null
    },
    totalDeployedCost() {
      return this.openEquityTrades.reduce((sum, t) => sum + (t.fill_price !== null && t.fill_quantity !== null ? t.fill_price * t.fill_quantity : 0), 0)
    },
    livePnlPct() {
      if (this.totalLivePnl === null || !this.totalDeployedCost) return null
      return (this.totalLivePnl / this.totalDeployedCost) * 100
    },
    // Per-position live % move (cost-basis relative), for breadth and best/worst-mover —
    // answers "what's actually driving the live P&L" without leaving this card for the table.
    positionsWithLivePnlPct() {
      return this.openEquityTrades
        .map((t) => {
          const pnlAbs = this.equityLivePnl(t)
          const cost = t.fill_price !== null && t.fill_quantity !== null ? t.fill_price * t.fill_quantity : null
          if (pnlAbs === null || !cost) return null
          return { ticker: t.security.ticker, pnlAbs, pnlPct: (pnlAbs / cost) * 100 }
        })
        .filter((p) => p !== null)
    },
    winnersCount() {
      return this.positionsWithLivePnlPct.filter((p) => p.pnlAbs > 0).length
    },
    losersCount() {
      return this.positionsWithLivePnlPct.filter((p) => p.pnlAbs < 0).length
    },
    breakevenCount() {
      return this.positionsWithLivePnlPct.filter((p) => p.pnlAbs === 0).length
    },
    bestMover() {
      if (!this.positionsWithLivePnlPct.length) return null
      return this.positionsWithLivePnlPct.reduce((best, p) => (p.pnlPct > best.pnlPct ? p : best))
    },
    worstMover() {
      if (!this.positionsWithLivePnlPct.length) return null
      return this.positionsWithLivePnlPct.reduce((worst, p) => (p.pnlPct < worst.pnlPct ? p : worst))
    },
    // Only entries/exits — Trade only stores a date (not a fill timestamp), so there's no
    // real "time" to show; job/pipeline runs are deliberately excluded (see RecentActivityCard).
    todaysTrades() {
      const today = todayIST()
      const items = []
      for (const t of this.tradesStore.trades) {
        if (t.entry_date === today) items.push({ key: `${t.id}-entry`, action: "entry", ticker: t.security.ticker, strategy: t.strategy_name, price: t.fill_price })
        if (t.exit_date === today) items.push({ key: `${t.id}-exit`, action: "exit", ticker: t.security.ticker, strategy: t.strategy_name, price: t.exit_price })
      }
      return items.slice(0, 30)
    },
  },
  async created() {
    usePageHeaderStore().set("Overview", "Atlas trading desk")
    await this.refreshAll()
    this.refreshHandle = setInterval(() => this.refreshAll(), REFRESH_INTERVAL_MS)
    this.startQuoteStream()
  },
  watch: {
    // openEquityTrades changes reactively on every refreshAll() poll — a strategy can open a new
    // position at any time, and without this the SSE stream keeps its ticker list frozen from
    // whenever the page first loaded, silently showing no live P&L for any position opened since.
    openEquityTrades() {
      const tickers = [...new Set(this.openEquityTrades.map((t) => t.security.ticker))].sort()
      const current = this.subscribedTickers
      if (tickers.length === current.length && tickers.every((t, i) => t === current[i])) return
      this.startQuoteStream()
    },
  },
  beforeUnmount() {
    if (this.refreshHandle) clearInterval(this.refreshHandle)
    this.streamHandle?.close()
  },
  methods: {
    formatCurrency,
    formatDate,
    formatDateTime,
    formatPercent,
    startQuoteStream() {
      this.streamHandle?.close()
      const tickers = [...new Set(this.openEquityTrades.map((t) => t.security.ticker))].sort()
      this.subscribedTickers = tickers
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
    ltpFor(trade) {
      return this.quotes[trade.security.ticker]?.last_price ?? null
    },
    positionReturnPct(trade) {
      const ltp = this.ltpFor(trade)
      if (ltp === null || !trade.fill_price) return null
      return ((ltp - trade.fill_price) / trade.fill_price) * 100
    },
    positionWeightPct(trade) {
      if (!this.currentNav || trade.fill_price === null || trade.fill_quantity === null) return null
      return ((trade.fill_price * trade.fill_quantity) / this.currentNav) * 100
    },
    positionAgeDays(trade) {
      return Math.floor((new Date() - new Date(trade.entry_date)) / 86400000)
    },
    exportPositionsCsv() {
      if (!this.filteredEquityTrades.length) return
      const header = ["Symbol", "Strategy", "Entry Date", "Qty", "Avg Price", "LTP", "P&L", "Return %", "Weight %", "Age (days)"]
      const rows = this.filteredEquityTrades.map((t) => [
        t.security.ticker, t.strategy_name, t.entry_date, t.fill_quantity ?? "", t.fill_price ?? "",
        this.ltpFor(t) ?? "", this.equityLivePnl(t) ?? "", this.positionReturnPct(t)?.toFixed(2) ?? "",
        this.positionWeightPct(t)?.toFixed(2) ?? "", this.positionAgeDays(t),
      ])
      const csv = [header, ...rows].map((r) => r.join(",")).join("\n")
      const blob = new Blob([csv], { type: "text/csv" })
      const url = URL.createObjectURL(blob)
      const link = document.createElement("a")
      link.href = url
      link.download = `active-positions-${todayIST()}.csv`
      link.click()
      URL.revokeObjectURL(url)
    },
    pnlClass(value) {
      const tone = pnlTone(value)
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return ""
    },
    refreshAll() {
      return this.dashboardStore.fetchAll()
    },
  },
}
</script>

<style scoped>
.positions-table td {
  white-space: nowrap;
}
</style>
