<template>
  <div class="flex flex-col gap-4">
    <div v-for="field in fields" :key="field.name">
      <label :for="fieldId(field.name)" class="label-caps mb-1.5 block">
        {{ field.name }}<span v-if="field.required" class="text-[var(--color-negative)]"> *</span>
      </label>

      <select
        v-if="field.type === 'enum'"
        :id="fieldId(field.name)"
        :value="modelValue[field.name]"
        class="w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent)] focus:outline-none"
        @change="update(field, ($event.target as HTMLSelectElement).value)"
      >
        <option v-for="opt in field.options" :key="String(opt)" :value="opt">{{ opt }}</option>
      </select>

      <textarea
        v-else-if="field.type === 'array'"
        :id="fieldId(field.name)"
        :value="JSON.stringify(modelValue[field.name] ?? [])"
        rows="3"
        class="font-mono-nums w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent)] focus:outline-none"
        @change="updateJson(field, ($event.target as HTMLTextAreaElement).value)"
      />

      <input
        v-else
        :id="fieldId(field.name)"
        :type="field.type === 'integer' || field.type === 'number' ? 'number' : 'text'"
        :step="field.type === 'number' ? 'any' : undefined"
        :value="modelValue[field.name]"
        class="font-mono-nums w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent)] focus:outline-none"
        @change="update(field, ($event.target as HTMLInputElement).value)"
      />

      <p v-if="field.description" class="mt-1 text-xs text-[var(--color-text-tertiary)]">{{ field.description }}</p>
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue"
import type { ConfigField } from "@/types/strategy"

export default defineComponent({
  name: "ConfigFieldForm",
  props: {
    fields: {
      type: Array as PropType<ConfigField[]>,
      required: true,
    },
    modelValue: {
      type: Object as PropType<Record<string, unknown>>,
      required: true,
    },
  },
  emits: ["update:modelValue"],
  methods: {
    fieldId(name: string) {
      return `config-field-${name}`
    },
    update(field: ConfigField, raw: string) {
      let value: unknown = raw
      if (field.type === "integer") value = raw === "" ? null : parseInt(raw, 10)
      if (field.type === "number") value = raw === "" ? null : parseFloat(raw)
      this.$emit("update:modelValue", { ...this.modelValue, [field.name]: value })
    },
    updateJson(field: ConfigField, raw: string) {
      try {
        const parsed = JSON.parse(raw)
        this.$emit("update:modelValue", { ...this.modelValue, [field.name]: parsed })
      } catch {
        // leave modelValue untouched until the JSON is valid again
      }
    },
  },
})
</script>
