<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" @click.self="$emit('close')">
    <div class="w-full max-w-md rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-alt)] p-5" style="box-shadow: var(--shadow-modal)">
      <div class="flex items-center gap-2.5">
        <div class="flex h-8 w-8 items-center justify-center rounded-[var(--radius-sm)] bg-[var(--color-accent-bg)]">
          <PlayCircle :size="15" class="text-[var(--color-accent)]" />
        </div>
        <h3 class="text-sm font-semibold text-[var(--color-text-primary)]">Trigger {{ job.display_name }}</h3>
      </div>
      <p class="mt-2 text-xs text-[var(--color-text-secondary)]">{{ job.description }}</p>

      <div v-if="job.parameter_fields.length" class="mt-4">
        <ConfigFieldForm v-model="params" :fields="job.parameter_fields" />
      </div>

      <p v-if="message" class="mt-3 text-xs text-[var(--color-warning)]">{{ message }}</p>

      <div class="mt-5 flex justify-end gap-2">
        <BaseButton variant="ghost" size="sm" @click="$emit('close')">Cancel</BaseButton>
        <BaseButton variant="primary" size="sm" :icon="PlayCircle" :loading="submitting" @click="submit">Trigger</BaseButton>
      </div>
    </div>
  </div>
</template>

<script>
import { PlayCircle } from "@lucide/vue"
import ConfigFieldForm from "@/components/strategies/ConfigFieldForm.vue"
import BaseButton from "@/components/primitives/BaseButton.vue"
import { useJobsStore } from "@/stores/jobs"

export default {
  name: "JobTriggerModal",
  components: { BaseButton, ConfigFieldForm, PlayCircle },
  props: {
    job: {
      type: Object,
      required: true,
    },
  },
  emits: ["close"],
  data() {
    return {
      params: Object.fromEntries(this.job.parameter_fields.map((f) => [f.name, f.default])),
      submitting: false,
      message: "",
    }
  },
  computed: {
    store() {
      return useJobsStore()
    },
  },
  methods: {
    async submit() {
      this.submitting = true
      const result = await this.store.trigger(this.job.name, this.params)
      this.submitting = false
      if (result.error) {
        this.message = result.message ?? "Failed to trigger job."
        return
      }
      this.$emit("close")
    },
  },
}
</script>
