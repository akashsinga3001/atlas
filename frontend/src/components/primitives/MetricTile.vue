<template>
  <div>
    <div class="flex items-center gap-1.5">
      <component :is="icon" v-if="icon" :size="12" class="text-[var(--color-text-tertiary)]" />
      <p class="label-caps">{{ label }}</p>
    </div>
    <p class="font-mono-nums mt-1.5 text-[19px] font-semibold leading-none tracking-tight" :class="toneClass">{{ value }}</p>
    <p v-if="sublabel" class="mt-1 text-xs text-[var(--color-text-tertiary)]">{{ sublabel }}</p>
  </div>
</template>

<script>
export default {
  name: "MetricTile",
  props: {
    label: {
      type: String,
      required: true,
    },
    value: {
      type: String,
      required: true,
    },
    sublabel: {
      type: String,
      default: "",
    },
    icon: {
      type: [Object, Function],
      default: null,
    },
    tone: {
      type: String,
      default: "neutral",
      validator: (value) => ["neutral", "positive", "negative"].includes(value),
    },
  },
  computed: {
    toneClass() {
      if (this.tone === "positive") return "text-[var(--color-positive)]"
      if (this.tone === "negative") return "text-[var(--color-negative)]"
      return "text-[var(--color-text-primary)]"
    },
  },
}
</script>
