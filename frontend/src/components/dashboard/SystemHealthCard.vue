<template>
  <BaseCard title="System health" :icon="ShieldCheck">
    <div class="flex flex-col gap-3.5">
      <div class="flex items-center justify-between">
        <span class="flex items-center gap-2 text-xs text-[var(--color-text-secondary)]"><Zap :size="13" />New entries</span>
        <StatusPill :label="killSwitch.isActive ? 'Paused' : 'Live'" :tone="killSwitch.isActive ? 'error' : 'positive'" />
      </div>

      <div v-if="breakers.length" class="flex flex-col gap-2.5">
        <button
          v-for="breaker in breakers"
          :key="breaker.id"
          type="button"
          class="flex items-center justify-between rounded-[var(--radius-sm)] px-1 py-0.5 text-left transition-colors hover:bg-[var(--color-surface-hover)]"
          @click="editingBreaker = breaker"
        >
          <span class="flex items-center gap-2 text-xs capitalize text-[var(--color-text-secondary)]"><CircuitBoard :size="13" />{{ breaker.type }} breaker</span>
          <span class="flex items-center gap-1.5">
            <StatusPill
              :label="!breaker.enabled ? 'Disabled' : breaker.last_triggered_at ? 'Triggered' : 'Armed'"
              :tone="!breaker.enabled ? 'inactive' : breaker.last_triggered_at ? 'error' : 'positive'"
            />
            <Settings2 :size="12" class="text-[var(--color-text-tertiary)]" />
          </span>
        </button>
      </div>
    </div>

    <CircuitBreakerModal v-if="editingBreaker" :breaker="editingBreaker" @close="editingBreaker = null" />
  </BaseCard>
</template>

<script>
import { CircuitBoard, Settings2, ShieldCheck, Zap } from "@lucide/vue"
import { useCircuitBreakersStore } from "@/stores/circuitBreakers"
import { useKillSwitchStore } from "@/stores/killSwitch"
import BaseCard from "@/components/primitives/BaseCard.vue"
import StatusPill from "@/components/primitives/StatusPill.vue"
import CircuitBreakerModal from "./CircuitBreakerModal.vue"

export default {
  name: "SystemHealthCard",
  components: { BaseCard, StatusPill, CircuitBoard, Settings2, Zap, CircuitBreakerModal },
  data() {
    return { ShieldCheck, editingBreaker: null }
  },
  computed: {
    killSwitch() {
      return useKillSwitchStore()
    },
    breakers() {
      return useCircuitBreakersStore().breakers
    },
  },
}
</script>
