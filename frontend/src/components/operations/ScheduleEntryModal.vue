<template>
  <div class="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" @click.self="$emit('close')">
    <div class="w-full max-w-md rounded-[var(--radius-lg)] border border-[var(--color-border)] bg-[var(--color-surface-alt)] p-5" style="box-shadow: var(--shadow-modal)">
      <h3 class="text-sm font-semibold text-[var(--color-text-primary)]">{{ isEdit ? "Edit schedule entry" : "New schedule entry" }}</h3>

      <div class="mt-4 flex flex-col gap-3">
        <div v-if="!isEdit">
          <label class="label-caps mb-1.5 block">Name</label>
          <input v-model="form.name" type="text" class="w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent)] focus:outline-none" />
        </div>
        <div>
          <label class="label-caps mb-1.5 block">Task (dotted path)</label>
          <input v-model="form.task" type="text" class="font-mono-nums w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent)] focus:outline-none" />
        </div>
        <div class="grid grid-cols-5 gap-2">
          <div v-for="field in cronFields" :key="field.key">
            <label class="label-caps mb-1.5 block">{{ field.label }}</label>
            <input v-model="form[field.key]" type="text" class="font-mono-nums w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2 py-1.5 text-center text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent)] focus:outline-none" />
          </div>
        </div>
        <div>
          <label class="label-caps mb-1.5 block">Group</label>
          <select v-model="form.group" class="w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-sm text-[var(--color-text-primary)]">
            <option value="trading">trading</option>
            <option value="data_pipeline">data_pipeline</option>
          </select>
        </div>
        <div>
          <label class="label-caps mb-1.5 block">Description</label>
          <input v-model="form.description" type="text" class="w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent)] focus:outline-none" />
        </div>
      </div>

      <p v-if="message" class="mt-3 text-xs text-[var(--color-warning)]">{{ message }}</p>

      <div class="mt-5 flex justify-between">
        <BaseButton v-if="isEdit" variant="danger" size="sm" :icon="Trash2" @click="remove">Delete</BaseButton>
        <div v-else />
        <div class="flex gap-2">
          <BaseButton variant="ghost" size="sm" @click="$emit('close')">Cancel</BaseButton>
          <BaseButton variant="primary" size="sm" :icon="Save" :loading="submitting" @click="submit">Save</BaseButton>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { Save, Trash2 } from "@lucide/vue"
import BaseButton from "@/components/primitives/BaseButton.vue"
import { useScheduleStore } from "@/stores/schedule"

const CRON_FIELDS = [
  { key: "minute", label: "Min" },
  { key: "hour", label: "Hour" },
  { key: "day_of_month", label: "DoM" },
  { key: "month_of_year", label: "Mon" },
  { key: "day_of_week", label: "DoW" },
]

export default {
  name: "ScheduleEntryModal",
  components: { BaseButton },
  props: {
    entry: {
      type: Object,
      default: null,
    },
  },
  emits: ["close"],
  data() {
    const source = this.entry
    return {
      cronFields: CRON_FIELDS,
      submitting: false,
      message: "",
      Save,
      Trash2,
      form: {
        name: source?.name ?? "",
        task: source?.task ?? "",
        minute: source?.minute ?? "*",
        hour: source?.hour ?? "*",
        day_of_month: source?.day_of_month ?? "*",
        month_of_year: source?.month_of_year ?? "*",
        day_of_week: source?.day_of_week ?? "*",
        group: source?.group ?? "trading",
        description: source?.description ?? "",
      },
    }
  },
  computed: {
    store() {
      return useScheduleStore()
    },
    isEdit() {
      return this.entry !== null
    },
  },
  methods: {
    async submit() {
      this.submitting = true
      const result = this.isEdit ? await this.store.update(this.entry.id, this.form) : await this.store.create({ ...this.form, enabled: true, kwargs: {} })
      this.submitting = false
      if (result.error) {
        this.message = result.message ?? "Failed to save."
        return
      }
      this.$emit("close")
    },
    async remove() {
      if (!this.isEdit) return
      this.submitting = true
      await this.store.remove(this.entry.id)
      this.submitting = false
      this.$emit("close")
    },
  },
}
</script>
