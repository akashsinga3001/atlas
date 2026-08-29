<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <div class="flex items-center justify-end">
      <StaleBadge :last-updated-at="store.resource.lastUpdatedAt" :has-error="store.resource.status === 'error'" />
    </div>

    <BaseCard :padded="false">
      <LoadingState v-if="store.resource.status === 'loading'" />
      <ErrorState v-else-if="store.resource.status === 'error' && !store.resource.data" :message="store.resource.error" @retry="store.fetch" />
      <EmptyState v-else-if="!store.strategies.length" title="No strategies configured" />
      <div v-else class="overflow-x-auto">
        <table class="data-table">
          <thead>
            <tr>
              <th>Strategy</th>
              <th>Asset class</th>
              <th>Status</th>
              <th>Active version</th>
              <th class="num">Open positions</th>
              <th>Last run</th>
              <th>Enabled</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="strategy in store.strategies" :key="strategy.id" class="group cursor-pointer" @click="$router.push(`/strategies/${strategy.id}`)">
              <td>
                <div class="flex items-center gap-2">
                  <p class="font-medium text-[var(--color-text-primary)]">{{ strategy.name }}</p>
                  <span v-if="strategy.code === 'dummy'" class="label-caps rounded-[var(--radius-sm)] bg-[var(--color-inactive-bg)] px-1.5 py-0.5">Test</span>
                </div>
                <p class="text-[11px] text-[var(--color-text-tertiary)]">{{ strategy.code }}</p>
              </td>
              <td class="text-[var(--color-text-secondary)]">{{ assetClass(strategy) }}</td>
              <td><StatusPill :label="statusFor(strategy).label" :tone="statusFor(strategy).tone" /></td>
              <td class="font-mono-nums text-[var(--color-text-secondary)]">{{ strategy.active_version ? `v${strategy.active_version.version}` : "—" }}</td>
              <td class="num font-mono-nums">{{ strategy.open_positions_count }}</td>
              <td class="text-[var(--color-text-secondary)]">{{ strategy.last_run_at ? formatDateTime(strategy.last_run_at) : "Never" }}</td>
              <td @click.stop>
                <button
                  type="button"
                  class="relative h-5 w-9 rounded-full transition-colors"
                  :class="strategy.is_active ? 'bg-[var(--color-positive)]' : 'bg-[var(--color-border-strong)]'"
                  @click="toggleActive(strategy)"
                >
                  <span
                    class="absolute top-0.5 h-4 w-4 rounded-full bg-white transition-all"
                    style="box-shadow: 0 1px 3px rgba(20, 21, 26, 0.25)"
                    :class="strategy.is_active ? 'left-4' : 'left-0.5'"
                  />
                </button>
              </td>
              <td class="text-right"><ChevronRight :size="14" class="ml-auto text-[var(--color-text-tertiary)] opacity-0 transition-opacity group-hover:opacity-100" /></td>
            </tr>
          </tbody>
        </table>
      </div>
    </BaseCard>
  </div>
</template>

<script>
import { ChevronRight } from "@lucide/vue"
import { useStrategiesStore } from "@/stores/strategies"
import { usePageHeaderStore } from "@/stores/pageHeader"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { formatDateTime } from "@/utils/format"

const OPTIONS_ENGINES = new Set(["options_iron_condor"])

export default {
  name: "StrategiesView",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, StaleBadge, StatusPill, ChevronRight },
  computed: {
    store() {
      return useStrategiesStore()
    },
  },
  created() {
    usePageHeaderStore().set("Strategies", "Every registered strategy, active or idle")
    this.store.fetch()
  },
  methods: {
    formatDateTime,
    assetClass(strategy) {
      if (strategy.code === "dummy") return "—"
      return OPTIONS_ENGINES.has(strategy.active_version?.implementation_class) || strategy.code === "nifty_iron_condor" ? "Options" : "Equity"
    },
    statusFor(strategy) {
      if (strategy.last_run_status === "FAILED") return { label: "Error", tone: "error" }
      if (!strategy.is_active) return { label: "Inactive", tone: "inactive" }
      if (strategy.open_positions_count > 0) return { label: "Active", tone: "live" }
      return { label: "Idle", tone: "inactive" }
    },
    toggleActive(strategy) {
      this.store.setActive(strategy.id, !strategy.is_active)
    },
  },
}
</script>
