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

          <!-- strategy_ids specifically gets a checkbox list of real strategies (by name) instead
               of a raw JSON array of IDs — nobody has strategy IDs memorized, but everybody
               recognizes the strategy by name. -->
          <div v-else-if="field.type === 'array' && field.name === 'strategy_ids'" class="flex flex-col gap-1.5 rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] p-2.5">
            <label v-for="s in strategiesStore.strategies" :key="s.id" class="flex items-center gap-2 text-sm text-[var(--color-text-primary)]">
              <input type="checkbox" :checked="((modelValue[field.name] ?? []) as number[]).includes(s.id)" @change="toggleStrategyId(field, s.id, ($event.target as HTMLInputElement).checked)" />
              {{ s.name }}
              <span v-if="!s.is_active" class="label-caps text-[var(--color-text-tertiary)]">disabled</span>
            </label>
            <p v-if="!strategiesStore.strategies.length" class="text-xs text-[var(--color-text-tertiary)]">No strategies available.</p>
          </div>

          <textarea
            v-else-if="field.type === 'array'"
            :id="fieldId(field.name)"
            :value="JSON.stringify(modelValue[field.name] ?? [])"
            rows="3"
            class="font-mono-nums w-full rounded-[var(--radius-sm)] border border-[var(--color-border-strong)] bg-[var(--color-surface)] px-2.5 py-1.5 text-sm text-[var(--color-text-primary)] focus:border-[var(--color-accent)] focus:outline-none"
            @change="updateJson(field, ($event.target as HTMLTextAreaElement).value)"
          />

          <label v-else-if="field.type === 'boolean'" class="flex items-center gap-2 text-sm text-[var(--color-text-primary)]">
            <input type="checkbox" :id="fieldId(field.name)" :checked="!!modelValue[field.name]" @change="updateBoolean(field, ($event.target as HTMLInputElement).checked)" />
            {{ modelValue[field.name] ? "Enabled" : "Disabled" }}
          </label>

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
import { useStrategiesStore } from "@/stores/strategies"

// Optional semantic grouping for known strategy config shapes — falls back to one flat,
// ungrouped section for any strategy whose fields don't match a known grouping (e.g. dummy).
const KNOWN_GROUPS: Record<string, string[]> = {
  Entry: ["underlying_ticker", "option_name", "vix_ticker", "entry_dte_target", "short_delta_target", "delta_tolerance", "wing_width_points"],
  "VIX gate": ["vix_percentile_lookback_days", "vix_avoid_band_low", "vix_avoid_band_high"],
  Exit: ["profit_target_pct", "stop_loss_multiple", "time_exit_dte"],
  "Risk & capital": ["max_lots", "account_capital_pct", "risk_free_rate"],
  Trading: ["live_trading_enabled"],
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
  created() {
    const store = useStrategiesStore()
    if (this.fields.some((f) => f.name === "strategy_ids") && store.resource.status === "idle") store.fetch()
  },
  computed: {
    strategiesStore() {
      return useStrategiesStore()
    },
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
    updateBoolean(field: ConfigField, checked: boolean) {
      this.$emit("update:modelValue", { ...this.modelValue, [field.name]: checked })
    },
    toggleStrategyId(field: ConfigField, id: number, checked: boolean) {
      const current = (this.modelValue[field.name] as number[] | undefined) ?? []
      const next = checked ? [...current, id] : current.filter((v) => v !== id)
      this.$emit("update:modelValue", { ...this.modelValue, [field.name]: next })
    },
  },
})
</script>
