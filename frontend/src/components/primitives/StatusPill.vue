<template>
  <span class="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-medium" :class="toneClasses">
    <component :is="icon" v-if="icon" :size="11" />
    <span v-else class="h-1.5 w-1.5 rounded-full" :class="dotClasses"></span>
    {{ label }}
  </span>
</template>

<script>
const TONE_CLASSES = {
  positive: "bg-[var(--color-positive-bg)] text-[var(--color-positive)] border-[var(--color-positive-border)]",
  negative: "bg-[var(--color-negative-bg)] text-[var(--color-negative)] border-[var(--color-negative-border)]",
  warning: "bg-[var(--color-warning-bg)] text-[var(--color-warning)] border-[var(--color-warning-border)]",
  error: "bg-[var(--color-error-bg)] text-[var(--color-error)] border-[var(--color-error-border)]",
  live: "bg-[var(--color-live-bg)] text-[var(--color-live)] border-[var(--color-live-border)]",
  inactive: "bg-[var(--color-inactive-bg)] text-[var(--color-inactive)] border-[var(--color-inactive-border)]",
}

const DOT_CLASSES = {
  positive: "bg-[var(--color-positive)]",
  negative: "bg-[var(--color-negative)]",
  warning: "bg-[var(--color-warning)]",
  error: "bg-[var(--color-error)]",
  live: "bg-[var(--color-live)]",
  inactive: "bg-[var(--color-inactive)]",
}

export default {
  name: "StatusPill",
  props: {
    label: {
      type: String,
      required: true,
    },
    tone: {
      type: String,
      default: "inactive",
      validator: (value) => Object.keys(TONE_CLASSES).includes(value),
    },
    icon: {
      type: [Object, Function],
      default: null,
    },
  },
  computed: {
    toneClasses() {
      return TONE_CLASSES[this.tone]
    },
    dotClasses() {
      return DOT_CLASSES[this.tone]
    },
  },
}
</script>
