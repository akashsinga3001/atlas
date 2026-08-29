<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <div class="flex flex-wrap items-center gap-2">
      <select v-model="filters.status" class="filter-control">
        <option value="">All statuses</option>
        <option value="open">Open</option>
        <option value="closing">Closing</option>
        <option value="closed">Closed</option>
        <option value="pending">Pending</option>
        <option value="failed">Failed</option>
        <option value="skipped">Skipped</option>
      </select>
      <select v-model="filters.strategy" class="filter-control">
        <option value="">All strategies</option>
        <option v-for="name in strategyNames" :key="name" :value="name">{{ name }}</option>
      </select>
      <span class="ml-auto text-[12px] text-[var(--color-text-tertiary)]">{{ filtered.length }} positions</span>
    </div>

    <BaseCard :padded="false">
      <LoadingState v-if="optionsStore.resource.status === 'loading'" />
      <ErrorState v-else-if="optionsStore.resource.status === 'error' && !optionsStore.resource.data" :message="optionsStore.resource.error" @retry="optionsStore.fetch" />
      <EmptyState v-else-if="!filtered.length" title="No options positions match these filters" description="Positions will appear here when an options strategy successfully enters." />
      <div v-else class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Underlying</th>
              <th>Strategy</th>
              <th>Expiry</th>
              <th>Entry date</th>
              <th>Status</th>
              <th class="num">Legs</th>
              <th class="num">Net P&amp;L</th>
              <th class="num">Margin</th>
              <th>Planned exit</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="p in filtered" :key="p.id" class="cursor-pointer" @click="$router.push(`/options/${p.id}`)">
              <td class="font-medium">{{ underlyingLabel(p) }}</td>
              <td>{{ p.strategy_name }}</td>
              <td>{{ formatDate(p.expiry_date) }}</td>
              <td>{{ formatDate(p.entry_date) }}</td>
              <td><StatusPill :label="p.status" :tone="statusTone(p.status)" /></td>
              <td class="num font-mono-nums">{{ p.legs.length }}</td>
              <td class="num font-mono-nums" :class="pnlClass(p.realized_pnl)">{{ p.realized_pnl !== null ? formatCurrency(p.realized_pnl, { signed: true }) : "—" }}</td>
              <td class="num font-mono-nums">{{ p.margin_total !== null ? formatCurrency(p.margin_total, { compact: true }) : "—" }}</td>
              <td>{{ p.planned_exit_date ? formatDate(p.planned_exit_date) : "—" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </BaseCard>
  </div>
</template>

<script>
import { useOptionsStore } from "@/stores/options"
import { usePageHeaderStore } from "@/stores/pageHeader"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { formatCurrency, formatDate, pnlTone } from "@/utils/format"

const STATUS_TONES = { open: "live", closing: "warning", closed: "inactive", pending: "info", failed: "error", skipped: "inactive" }

export default {
  name: "OptionsView",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, StatusPill },
  data() {
    return {
      filters: { status: "", strategy: "" },
    }
  },
  computed: {
    optionsStore() {
      return useOptionsStore()
    },
    strategyNames() {
      return [...new Set(this.optionsStore.positions.map((p) => p.strategy_name))].sort()
    },
    filtered() {
      return this.optionsStore.positions.filter((p) => {
        if (this.filters.status && p.status !== this.filters.status) return false
        if (this.filters.strategy && p.strategy_name !== this.filters.strategy) return false
        return true
      })
    },
  },
  created() {
    usePageHeaderStore().set("Options", "Multi-leg options positions")
    if (this.optionsStore.resource.status === "idle") this.optionsStore.fetch()
  },
  methods: {
    formatCurrency,
    formatDate,
    statusTone(status) {
      return STATUS_TONES[status] ?? "inactive"
    },
    pnlClass(value) {
      const tone = pnlTone(value)
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return ""
    },
    underlyingLabel(p) {
      const parts = []
      if (p.call_short_strike) parts.push(`${p.call_short_strike}CE`)
      if (p.put_short_strike) parts.push(`${p.put_short_strike}PE`)
      return parts.length ? parts.join(" / ") : `Position #${p.id}`
    },
  },
}
</script>
