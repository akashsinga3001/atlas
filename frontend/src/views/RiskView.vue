<template>
  <div class="mx-auto flex max-w-[var(--content-max-width)] flex-col gap-4">
    <BaseCard title="Kill switch" :icon="killSwitchStore.isActive ? PauseCircle : Radio">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <StatusPill :label="killSwitchStore.isActive ? 'Active' : 'Off'" :tone="killSwitchStore.isActive ? 'error' : 'positive'" :icon="killSwitchStore.isActive ? PauseCircle : Radio" />
          <div v-if="killSwitchStore.isActive" class="text-[12.5px]">
            <p class="text-[var(--color-text-primary)]">{{ killSwitchStore.reason ?? "No reason recorded" }}</p>
          </div>
        </div>
        <BaseButton variant="secondary" size="sm" :icon="killSwitchStore.isActive ? Play : Pause" @click="showConfirm = true">
          {{ killSwitchStore.isActive ? "Resume entries" : "Pause entries" }}
        </BaseButton>
      </div>
      <div class="mt-4 rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] px-3.5 py-3 text-[12px] leading-relaxed text-[var(--color-text-secondary)]">
        The kill switch blocks <span class="font-medium text-[var(--color-text-primary)]">new entries only</span>. It does not close existing positions, and it does not disable exits or trailing stops — those keep running exactly as configured.
      </div>
    </BaseCard>

    <BaseCard title="Circuit breakers" :icon="Shield">
      <LoadingState v-if="breakersStore.resource.status === 'loading'" />
      <ErrorState v-else-if="breakersStore.resource.status === 'error' && !breakersStore.resource.data" :message="breakersStore.resource.error" @retry="breakersStore.fetch" />
      <EmptyState v-else-if="!breakersStore.breakers.length" title="No circuit breakers configured" />
      <div v-else class="flex flex-col divide-y divide-[var(--color-border)]">
        <div v-for="b in breakersStore.breakers" :key="b.id" class="flex items-center justify-between py-3 first:pt-0 last:pb-0">
          <div class="flex items-center gap-3">
            <StatusPill :label="b.enabled ? 'Enabled' : 'Disabled'" :tone="b.enabled ? 'positive' : 'inactive'" />
            <div>
              <p class="text-[13px] font-medium capitalize text-[var(--color-text-primary)]">{{ b.type }}</p>
              <p class="text-[11.5px] text-[var(--color-text-tertiary)]">
                Threshold {{ b.params.threshold_pct }}%
                <span v-if="b.type === 'drawdown'"> · current {{ currentDrawdown !== null ? `${currentDrawdown}%` : '—' }}</span>
              </p>
            </div>
          </div>

          <div class="flex items-center gap-4">
            <div v-if="b.type === 'drawdown' && currentDrawdown !== null" class="w-32">
              <div class="h-1.5 overflow-hidden rounded-full bg-[var(--color-border-strong)]">
                <div class="h-full rounded-full transition-all" :class="drawdownRatio >= 1 ? 'bg-[var(--color-risk-hot)]' : drawdownRatio >= 0.75 ? 'bg-[var(--color-risk-elevated)]' : 'bg-[var(--color-risk-calm)]'" :style="{ width: `${Math.min(drawdownRatio, 1) * 100}%` }" />
              </div>
            </div>
            <span v-if="b.last_triggered_at" class="text-[11px] text-[var(--color-error)]">triggered {{ formatDateTime(b.last_triggered_at) }}</span>
            <BaseButton variant="ghost" size="sm" @click="editing = b">Configure</BaseButton>
          </div>
        </div>
      </div>
    </BaseCard>

    <CircuitBreakerModal v-if="editing" :breaker="editing" @close="editing = null" />

    <div v-if="showConfirm" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" @click.self="showConfirm = false">
      <div class="w-full max-w-sm rounded-[var(--radius-lg)] bg-[var(--color-overlay)] p-6" style="box-shadow: var(--shadow-overlay)">
        <h3 class="text-[15px] font-semibold text-[var(--color-text-primary)]">{{ killSwitchStore.isActive ? "Resume new entries?" : "Pause new entries?" }}</h3>
        <p class="mt-2 text-[13px] leading-relaxed text-[var(--color-text-secondary)]">Existing positions' exits and trailing stops are never affected — this only pauses new entry jobs.</p>
        <input
          v-if="!killSwitchStore.isActive"
          v-model="reason"
          type="text"
          placeholder="Reason (required)"
          class="mt-4 w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-3.5 py-2.5 text-sm text-[var(--color-text-primary)] placeholder:text-[var(--color-text-tertiary)] focus:border-[var(--color-accent)] focus:outline-none"
        />
        <div class="mt-5 flex justify-end gap-2">
          <BaseButton variant="ghost" size="sm" @click="showConfirm = false">Cancel</BaseButton>
          <BaseButton variant="danger" size="sm" :disabled="!killSwitchStore.isActive && !reason.trim()" @click="confirm">Confirm</BaseButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { Pause, PauseCircle, Play, Radio, Shield } from "@lucide/vue"
import { useCircuitBreakersStore } from "@/stores/circuitBreakers"
import { useKillSwitchStore } from "@/stores/killSwitch"
import { usePageHeaderStore } from "@/stores/pageHeader"
import { usePortfolioStatsStore } from "@/stores/portfolioStats"
import BaseButton from "@/components/primitives/BaseButton.vue"
import BaseCard from "@/components/primitives/BaseCard.vue"
import EmptyState from "@/components/primitives/EmptyState.vue"
import ErrorState from "@/components/primitives/ErrorState.vue"
import LoadingState from "@/components/primitives/LoadingState.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import CircuitBreakerModal from "@/components/dashboard/CircuitBreakerModal.vue"
import { formatDateTime } from "@/utils/format"

export default {
  name: "RiskView",
  components: { BaseButton, BaseCard, EmptyState, ErrorState, LoadingState, StatusPill, CircuitBreakerModal },
  data() {
    return { Pause, PauseCircle, Play, Radio, Shield, showConfirm: false, reason: "", editing: null }
  },
  computed: {
    killSwitchStore() {
      return useKillSwitchStore()
    },
    breakersStore() {
      return useCircuitBreakersStore()
    },
    statsStore() {
      return usePortfolioStatsStore()
    },
    currentDrawdown() {
      return this.statsStore.resource.data?.max_drawdown_pct ?? null
    },
    drawdownBreaker() {
      return this.breakersStore.breakers.find((b) => b.type === "drawdown")
    },
    drawdownRatio() {
      if (this.currentDrawdown === null || !this.drawdownBreaker) return 0
      const threshold = this.drawdownBreaker.params.threshold_pct ?? 5
      return this.currentDrawdown / threshold
    },
  },
  created() {
    usePageHeaderStore().set("Risk Controls", "Kill switch and circuit breakers")
    if (this.breakersStore.resource.status === "idle") this.breakersStore.fetch()
    if (this.killSwitchStore.resource.status === "idle") this.killSwitchStore.fetch()
    if (this.statsStore.resource.status === "idle") this.statsStore.fetch()
  },
  methods: {
    formatDateTime,
    async confirm() {
      if (this.killSwitchStore.isActive) {
        await this.killSwitchStore.deactivate()
      } else {
        await this.killSwitchStore.activate(this.reason.trim())
        this.reason = ""
      }
      this.showConfirm = false
    },
  },
}
</script>
