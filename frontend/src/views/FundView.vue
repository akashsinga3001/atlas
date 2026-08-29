<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <BaseCard title="Account state" :icon="Landmark">
      <LoadingState v-if="curveStore.nav.status === 'loading'" />
      <ErrorState v-else-if="curveStore.nav.status === 'error' && !curveStore.nav.data" :message="curveStore.nav.error" @retry="curveStore.fetch" />
      <div v-else-if="latest" class="grid grid-cols-2 gap-x-6 gap-y-4 sm:grid-cols-4">
        <MetricTile label="As of" :value="formatDate(latest.date)" />
        <MetricTile label="Cash balance" :value="formatCurrency(latest.cash_balance)" />
        <MetricTile label="Holdings + margin" :value="formatCurrency(latest.holdings_value)" />
        <MetricTile label="Total value" :value="formatCurrency(latest.total_value)" />
      </div>
      <EmptyState v-else title="No account snapshots yet" description="Snapshots are recorded once the daily account-snapshot job has run." />
    </BaseCard>

    <p class="text-[11.5px] text-[var(--color-text-tertiary)]">
      Portfolio performance (NAV/return/drawdown) reflects trading results. Cash flows below are money you added or removed — they don't count as performance.
    </p>

    <CashFlowCard />

    <BaseCard title="Account snapshots" :icon="History">
      <LoadingState v-if="curveStore.nav.status === 'loading'" />
      <EmptyState v-else-if="!snapshots.length" title="No account snapshots yet" />
      <div v-else class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Date</th>
              <th class="num">Cash</th>
              <th class="num">Holdings + margin</th>
              <th class="num">Total value</th>
              <th class="num">Cash flow</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in snapshots" :key="s.date">
              <td>{{ formatDate(s.date) }}</td>
              <td class="num font-mono-nums">{{ formatCurrency(s.cash_balance) }}</td>
              <td class="num font-mono-nums">{{ formatCurrency(s.holdings_value) }}</td>
              <td class="num font-mono-nums font-medium">{{ formatCurrency(s.total_value) }}</td>
              <td class="num font-mono-nums">{{ s.cash_flow ? formatCurrency(s.cash_flow, { signed: true }) : "—" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </BaseCard>
  </div>
</template>

<script>
import { History, Landmark } from "@lucide/vue"
import { useEquityCurveStore } from "@/stores/equityCurve"
import { usePageHeaderStore } from "@/stores/pageHeader"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import MetricTile from "@/components/primitives/MetricTile.vue"
import CashFlowCard from "@/components/performance/CashFlowCard.vue"
import { formatCurrency, formatDate } from "@/utils/format"

export default {
  name: "FundView",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, MetricTile, CashFlowCard },
  data() {
    return { Landmark, History }
  },
  computed: {
    curveStore() {
      return useEquityCurveStore()
    },
    snapshots() {
      return (this.curveStore.nav.data ?? []).slice().reverse()
    },
    latest() {
      const nav = this.curveStore.nav.data ?? []
      return nav.length ? nav[nav.length - 1] : null
    },
  },
  created() {
    usePageHeaderStore().set("Fund", "Cash flows and account snapshots")
    if (this.curveStore.nav.status === "idle") this.curveStore.fetch()
  },
  methods: {
    formatCurrency,
    formatDate,
  },
}
</script>
