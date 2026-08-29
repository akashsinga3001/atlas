<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <div class="flex flex-wrap items-center gap-2">
      <select v-model="filters.strategy" class="filter-control" @change="load">
        <option value="">All strategies</option>
        <option v-for="s in strategiesStore.strategies" :key="s.id" :value="s.code">{{ s.name }}</option>
      </select>
      <select v-model="filters.status" class="filter-control">
        <option value="">All statuses</option>
        <option value="entered">Entered</option>
        <option value="missed">Missed</option>
      </select>
      <input v-model="filters.date_from" type="date" class="filter-control" @change="load" />
      <input v-model="filters.date_to" type="date" class="filter-control" @change="load" />
      <span class="ml-auto text-[12px] text-[var(--color-text-tertiary)]">{{ filtered.length }} signals</span>
    </div>

    <BaseCard :padded="false">
      <LoadingState v-if="resource.status === 'loading'" />
      <ErrorState v-else-if="resource.status === 'error' && !resource.data" :message="resource.error" @retry="load" />
      <EmptyState v-else-if="!filtered.length" title="No signals generated for the selected period" />
      <div v-else class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Timestamp</th>
              <th>Strategy</th>
              <th>Security</th>
              <th>Status</th>
              <th>Execution</th>
              <th class="num">Performance</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="s in filtered" :key="s.id" class="cursor-pointer" @click="$router.push(`/signals/${s.id}`)">
              <td>{{ formatDateTime(s.observed_at) }}</td>
              <td>{{ s.strategy_name ?? "—" }}</td>
              <td class="font-medium">{{ s.security.ticker }}</td>
              <td><StatusPill :label="s.signal_status" :tone="s.signal_status === 'entered' ? 'live' : 'inactive'" /></td>
              <td>{{ s.trade_status ?? "not entered" }}</td>
              <td class="num font-mono-nums" :class="pnlClass(s.perf_since_signal)">{{ s.perf_since_signal !== null ? formatPercent(s.perf_since_signal) : "—" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </BaseCard>
  </div>
</template>

<script>
import { fetchSignals } from "@/services/api/signals"
import { usePageHeaderStore } from "@/stores/pageHeader"
import { useStrategiesStore } from "@/stores/strategies"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { formatDateTime, formatPercent, pnlTone } from "@/utils/format"

export default {
  name: "SignalsView",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, StatusPill },
  data() {
    return {
      filters: { strategy: "", status: "", date_from: "", date_to: "" },
      resource: { status: "idle", data: null, error: null },
    }
  },
  computed: {
    strategiesStore() {
      return useStrategiesStore()
    },
    filtered() {
      const items = this.resource.data ?? []
      if (!this.filters.status) return items
      return items.filter((s) => s.signal_status === this.filters.status)
    },
  },
  created() {
    usePageHeaderStore().set("Signals", "Strategy signal → decision → execution → outcome")
    if (this.strategiesStore.resource.status === "idle") this.strategiesStore.fetch()
    this.load()
  },
  methods: {
    formatDateTime,
    formatPercent,
    pnlClass(value) {
      const tone = pnlTone(value)
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return ""
    },
    async load() {
      this.resource.status = "loading"
      const result = await fetchSignals({
        strategy: this.filters.strategy || undefined,
        date_from: this.filters.date_from || undefined,
        date_to: this.filters.date_to || undefined,
      })
      if (result.error) {
        this.resource.status = "error"
        this.resource.error = result.message
        return
      }
      this.resource.data = result.data
      this.resource.status = "success"
    },
  },
}
</script>
