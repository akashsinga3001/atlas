<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" @click.self="$emit('close')">
    <div class="w-full max-w-sm rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-alt)] p-5" style="box-shadow: var(--shadow-modal)">
      <h3 class="text-sm font-semibold text-[var(--color-text-primary)]">Record cash flow</h3>
      <p class="mt-1.5 text-xs text-[var(--color-text-secondary)]">Deposits and withdrawals feed the true-return calculation and NAV curve markers.</p>

      <div class="mt-4 flex flex-col gap-3">
        <div class="flex rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] p-0.5">
          <button
            v-for="type in ['deposit', 'withdrawal']"
            :key="type"
            type="button"
            class="flex-1 rounded-[6px] py-1.5 text-xs font-medium capitalize transition-colors"
            :class="form.flow_type === type ? 'bg-[var(--color-accent-bg)] text-[var(--color-accent)]' : 'text-[var(--color-text-tertiary)]'"
            @click="form.flow_type = type"
          >
            {{ type }}
          </button>
        </div>
        <div>
          <label class="label-caps mb-1.5 block">Amount (₹)</label>
          <input v-model.number="form.amount" type="number" min="0" step="1" class="font-mono-nums w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent)] focus:outline-none" />
        </div>
        <div>
          <label class="label-caps mb-1.5 block">Date</label>
          <input v-model="form.flow_date" type="date" class="font-mono-nums w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent)] focus:outline-none" />
        </div>
        <div>
          <label class="label-caps mb-1.5 block">Note (optional)</label>
          <input v-model="form.note" type="text" class="w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent)] focus:outline-none" />
        </div>
      </div>

      <p v-if="message" class="mt-3 text-xs text-[var(--color-warning)]">{{ message }}</p>

      <div class="mt-5 flex justify-end gap-2">
        <BaseButton variant="ghost" size="sm" @click="$emit('close')">Cancel</BaseButton>
        <BaseButton variant="primary" size="sm" :icon="Save" :disabled="!form.amount || !form.flow_date" :loading="submitting" @click="submit">Save</BaseButton>
      </div>
    </div>
  </div>
</template>

<script>
import { Save } from "@lucide/vue"
import { useFundStore } from "@/stores/fund"
import BaseButton from "@/components/primitives/BaseButton.vue"

function today() {
  return new Date().toISOString().slice(0, 10)
}

export default {
  name: "CashFlowModal",
  components: { BaseButton },
  emits: ["close"],
  data() {
    return {
      form: {
        flow_type: "deposit",
        amount: null,
        flow_date: today(),
        note: "",
      },
      submitting: false,
      message: "",
      Save,
    }
  },
  computed: {
    store() {
      return useFundStore()
    },
  },
  methods: {
    async submit() {
      this.submitting = true
      const result = await this.store.create({ ...this.form, note: this.form.note || undefined })
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
