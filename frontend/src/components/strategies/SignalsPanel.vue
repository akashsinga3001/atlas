<template>
  <div>
    <LoadingState v-if="store.resource.status === 'loading'" />
    <ErrorState v-else-if="store.resource.status === 'error' && !store.resource.data" :message="store.resource.error" @retry="load" />
    <EmptyState v-else-if="!signals.length" title="No signals yet" description="This strategy hasn't generated any signals." />
    <table v-else class="w-full text-sm">
      <thead>
        <tr class="border-b border-[var(--color-border)] text-left">
          <th class="label-caps pb-3.5 font-normal">Security</th>
          <th class="label-caps pb-3.5 font-normal">Observed</th>
          <th class="label-caps pb-3.5 font-normal">Status</th>
          <th class="label-caps pb-3.5 font-normal text-right">Perf since signal</th>
          <th class="label-caps pb-3.5 font-normal text-right">Trade P&L</th>
        </tr>
      </thead>
      <tbody>
        <tr
          v-for="signal in signals"
          :key="signal.id"
          class="border-b border-[var(--color-border)] last:border-0"
          :class="signal.trade_id ? 'cursor-pointer hover:bg-[var(--color-surface-hover)]' : ''"
          @click="signal.trade_id && $router.push(`/signals/${signal.id}`)"
        >
          <td class="py-3.5">
            <p class="font-medium text-[var(--color-text-primary)]">{{ signal.security.ticker }}</p>
            <p class="text-xs text-[var(--color-text-tertiary)]">{{ signal.security.sector ?? "—" }}</p>
          </td>
          <td class="py-3.5 text-[var(--color-text-secondary)]">{{ formatDateTime(signal.observed_at) }}</td>
          <td class="py-3.5">
            <StatusPill :label="signal.signal_status" :tone="signal.signal_status === 'entered' ? 'live' : 'inactive'" />
          </td>
          <td class="font-mono-nums py-3.5 text-right" :class="pnlClass(signal.perf_since_signal)">{{ formatPercent(signal.perf_since_signal) }}</td>
          <td class="font-mono-nums py-3.5 text-right" :class="pnlClass(signal.trade_pnl_pct)">{{ formatPercent(signal.trade_pnl_pct) }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script>
import { useSignalsStore } from "@/stores/signals"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { formatDateTime, formatPercent, pnlTone } from "@/utils/format"

export default {
  name: "SignalsPanel",
  components: { EmptyState, ErrorState, LoadingState, StatusPill },
  props: {
    strategyName: {
      type: String,
      required: true,
    },
  },
  computed: {
    store() {
      return useSignalsStore()
    },
    signals() {
      return this.store.resource.data ?? []
    },
  },
  watch: {
    strategyName: {
      immediate: true,
      handler(name) {
        if (name) this.load()
      },
    },
  },
  methods: {
    formatDateTime,
    formatPercent,
    load() {
      this.store.loadForStrategy(this.strategyName)
    },
    pnlClass(value) {
      const tone = pnlTone(value)
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return "text-[var(--color-text-tertiary)]"
    },
  },
}
</script>
