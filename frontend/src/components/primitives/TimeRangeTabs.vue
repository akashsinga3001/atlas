<template>
  <div class="flex items-center gap-1 rounded-[var(--radius-sm)] bg-[var(--color-surface-alt)] p-0.5">
    <button
      v-for="opt in options"
      :key="opt"
      type="button"
      class="rounded-[var(--radius-sm)] px-2.5 py-1 text-[11px] font-medium transition-colors"
      :class="opt === modelValue ? 'bg-[var(--color-surface)] text-[var(--color-text-primary)] shadow-sm' : 'text-[var(--color-text-tertiary)] hover:text-[var(--color-text-secondary)]'"
      @click="$emit('update:modelValue', opt)"
    >
      {{ opt }}
    </button>
  </div>
</template>

<script>
export default {
  name: "TimeRangeTabs",
  props: {
    modelValue: {
      type: String,
      required: true,
    },
    options: {
      type: Array,
      default: () => ["1D", "1W", "1M", "3M", "YTD", "ALL"],
    },
  },
  emits: ["update:modelValue"],
}
</script>
