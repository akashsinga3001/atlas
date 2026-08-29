<template>
  <div class="flex flex-col gap-6">
    <div v-for="group in groupedFields" :key="group.label">
      <h4 v-if="group.label" class="label-caps mb-3">{{ group.label }}</h4>
      <div class="flex flex-col gap-4">
        <div v-for="field in group.fields" :key="field.name">
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
    </div>
  </div>
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue"
import type { ConfigField } from "@/types/strategy"

// Optional semantic grouping for known strategy config shapes — falls back to one flat,
// ungrouped section for any strategy whose fields don't match a known grouping (e.g. dummy).
const KNOWN_GROUPS: Record<string, string[]> = {
  Entry: ["underlying_ticker", "option_name", "signal_day_of_week", "strike_step", "short_otm_pct", "long_otm_pct"],
  "Risk & capital": ["capital_pct_calm", "capital_pct_elevated", "max_lots", "account_capital_pct"],
  Volatility: ["vol_regime_lookback_days"],
  Liquidity: ["liquidity_lookback_days", "liquidity_participation_pct"],
  Exit: ["hold_days"],
}

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
  computed: {
    groupedFields() {
      const byName = new Map(this.fields.map((f) => [f.name, f]))
      const grouped: { label: string; fields: ConfigField[] }[] = []
      const used = new Set<string>()

      for (const [label, names] of Object.entries(KNOWN_GROUPS)) {
        const groupFields = names.map((n) => byName.get(n)).filter((f): f is ConfigField => !!f)
        if (groupFields.length) {
          grouped.push({ label, fields: groupFields })
          groupFields.forEach((f) => used.add(f.name))
        }
      }

      const remaining = this.fields.filter((f) => !used.has(f.name))
      if (remaining.length) grouped.push({ label: grouped.length ? "Other" : "", fields: remaining })

      return grouped
    },
  },
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
