<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-5">
    <div class="flex items-center justify-between">
      <div>
        <h1 class="text-xl font-semibold tracking-tight">Strategies</h1>
        <p class="mt-1 text-sm text-[var(--color-text-tertiary)]">Every configured strategy, active or idle.</p>
      </div>
      <StaleBadge :last-updated-at="store.resource.lastUpdatedAt" :has-error="store.resource.status === 'error'" />
    </div>

    <BaseCard :padded="false">
      <LoadingState v-if="store.resource.status === 'loading'" />
      <ErrorState v-else-if="store.resource.status === 'error' && !store.resource.data" :message="store.resource.error" @retry="store.fetch" />
      <EmptyState v-else-if="!store.strategies.length" title="No strategies configured" />
      <table v-else class="w-full text-sm">
        <thead>
          <tr class="border-b border-[var(--color-border)] text-left">
            <th class="label-caps px-5 py-3.5 font-normal">Strategy</th>
            <th class="label-caps px-5 py-3.5 font-normal">Status</th>
            <th class="label-caps px-5 py-3.5 font-normal">Active version</th>
            <th class="label-caps px-5 py-3.5 font-normal">Open positions</th>
            <th class="label-caps px-5 py-3.5 font-normal">Last run</th>
            <th class="label-caps px-5 py-3.5 font-normal">Enabled</th>
            <th class="px-5 py-3.5"></th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="strategy in store.strategies"
            :key="strategy.id"
            class="group cursor-pointer border-b border-[var(--color-border)] last:border-0 hover:bg-[var(--color-surface-hover)]"
            @click="$router.push(`/strategies/${strategy.id}`)"
          >
            <td class="px-5 py-4">
              <div class="flex items-center gap-3">
                <div class="icon-badge flex h-8 w-8 shrink-0 items-center justify-center rounded-[var(--radius-sm)]">
                  <Layers :size="14" class="text-[var(--color-accent)]" />
                </div>
                <div>
                  <p class="font-medium text-[var(--color-text-primary)]">{{ strategy.name }}</p>
                  <p class="text-xs text-[var(--color-text-tertiary)]">{{ strategy.code }}</p>
                </div>
              </div>
            </td>
            <td class="px-5 py-4"><StatusPill :label="statusFor(strategy).label" :tone="statusFor(strategy).tone" /></td>
            <td class="font-mono-nums px-5 py-4 text-[var(--color-text-secondary)]">{{ strategy.active_version ? `v${strategy.active_version.version}` : "—" }}</td>
            <td class="font-mono-nums px-5 py-4">{{ strategy.open_positions_count }}</td>
            <td class="px-5 py-4 text-[var(--color-text-secondary)]">{{ strategy.last_run_at ? formatDateTime(strategy.last_run_at) : "Never" }}</td>
            <td class="px-5 py-4" @click.stop>
              <button
                type="button"
                class="relative h-5 w-9 rounded-full transition-colors"
                :class="strategy.is_active ? 'bg-[var(--color-positive)]' : 'bg-[var(--color-inactive-bg)]'"
                @click="toggleActive(strategy)"
              >
                <span class="absolute top-0.5 h-4 w-4 rounded-full bg-[var(--color-bg)] transition-all" :class="strategy.is_active ? 'left-4' : 'left-0.5'" />
              </button>
            </td>
            <td class="px-5 py-4 text-right">
              <ChevronRight :size="16" class="ml-auto text-[var(--color-text-tertiary)] opacity-0 transition-opacity group-hover:opacity-100" />
            </td>
          </tr>
        </tbody>
      </table>
    </BaseCard>
  </div>
</template>

<script>
import { ChevronRight, Layers } from "@lucide/vue"
import { useStrategiesStore } from "@/stores/strategies"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StaleBadge from "@/components/primitives/StaleBadge.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import { formatDateTime } from "@/utils/format"

export default {
  name: "StrategiesView",
  components: { BaseCard, EmptyState, ErrorState, LoadingState, StaleBadge, StatusPill, ChevronRight, Layers },
  computed: {
    store() {
      return useStrategiesStore()
    },
  },
  created() {
    this.store.fetch()
  },
  methods: {
    formatDateTime,
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
