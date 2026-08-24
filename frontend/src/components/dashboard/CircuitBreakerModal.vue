<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" @click.self="$emit('close')">
    <div class="w-full max-w-sm rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-alt)] p-5" style="box-shadow: var(--shadow-modal)">
      <h3 class="text-sm font-semibold capitalize text-[var(--color-text-primary)]">{{ breaker.type }} circuit breaker</h3>

      <div v-if="breaker.last_triggered_at" class="mt-3 rounded-[var(--radius-sm)] border border-[var(--color-error-border)] bg-[var(--color-error-bg)] px-3 py-2 text-xs text-[var(--color-error)]">
        Last triggered {{ formatDateTime(breaker.last_triggered_at) }}<span v-if="breaker.last_reason"> — {{ breaker.last_reason }}</span>
      </div>

      <div class="mt-4 flex items-center justify-between">
        <label class="text-xs font-medium text-[var(--color-text-secondary)]">Enabled</label>
        <button type="button" class="relative h-5 w-9 rounded-full transition-colors" :class="form.enabled ? 'bg-[var(--color-positive)]' : 'bg-[var(--color-inactive-bg)]'" @click="form.enabled = !form.enabled">
          <span class="absolute top-0.5 h-4 w-4 rounded-full bg-[var(--color-bg)] transition-all" :class="form.enabled ? 'left-4' : 'left-0.5'" />
        </button>
      </div>

      <div class="mt-4">
        <label class="label-caps mb-1.5 block">Threshold %</label>
        <input
          v-model.number="form.threshold_pct"
          type="number"
          step="0.5"
          min="0"
          class="font-mono-nums w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent)] focus:outline-none"
        />
        <p class="mt-1 text-xs text-[var(--color-text-tertiary)]">Halts new entries (via the kill switch) when portfolio drawdown exceeds this percentage of capital.</p>
      </div>

      <p v-if="message" class="mt-3 text-xs text-[var(--color-warning)]">{{ message }}</p>

      <div class="mt-5 flex justify-end gap-2">
        <BaseButton variant="ghost" size="sm" @click="$emit('close')">Cancel</BaseButton>
        <BaseButton variant="primary" size="sm" :icon="Save" :loading="submitting" @click="submit">Save</BaseButton>
      </div>
    </div>
  </div>
</template>

<script>
import { Save } from "@lucide/vue"
import { useCircuitBreakersStore } from "@/stores/circuitBreakers"
import BaseButton from "@/components/primitives/BaseButton.vue"
import { formatDateTime } from "@/utils/format"

export default {
  name: "CircuitBreakerModal",
  components: { BaseButton },
  props: {
    breaker: {
      type: Object,
      required: true,
    },
  },
  emits: ["close"],
  data() {
    return {
      form: {
        enabled: this.breaker.enabled,
        threshold_pct: this.breaker.params.threshold_pct ?? 5,
      },
      submitting: false,
      message: "",
      Save,
    }
  },
  computed: {
    store() {
      return useCircuitBreakersStore()
    },
  },
  methods: {
    formatDateTime,
    async submit() {
      this.submitting = true
      const result = await this.store.update(this.breaker.id, { enabled: this.form.enabled, params: { ...this.breaker.params, threshold_pct: this.form.threshold_pct } })
      this.submitting = false
      if (result.error) {
        this.message = result.message ?? "Failed to save."
        return
      }
      this.$emit("close")
    },
  },
}
</script>
