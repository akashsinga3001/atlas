<template>
  <button
    type="button"
    class="inline-flex items-center justify-center gap-1.5 whitespace-nowrap rounded-[var(--radius-sm)] font-medium disabled:cursor-not-allowed disabled:opacity-40"
    :class="[sizeClasses, variantClasses, depthClass]"
    :disabled="disabled || loading"
  >
    <Loader2 v-if="loading" :size="iconSize" class="animate-spin" />
    <component :is="icon" v-else-if="icon" :size="iconSize" />
    <slot />
  </button>
</template>

<script>
import { Loader2 } from "@lucide/vue"

const VARIANT_CLASSES = {
  primary: "bg-[var(--color-accent)] text-[var(--color-text-inverse)] hover:bg-[var(--color-accent-hover)]",
  secondary: "border border-[var(--color-border-strong)] text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]",
  ghost: "text-[var(--color-text-secondary)] hover:bg-[var(--color-surface-hover)] hover:text-[var(--color-text-primary)]",
  danger: "border border-[var(--color-negative-border)] text-[var(--color-negative)] hover:bg-[var(--color-negative-bg)]",
}

const SIZE_CLASSES = {
  sm: "px-2.5 py-1 text-xs",
  md: "px-3.5 py-2 text-sm",
}

export default {
  name: "BaseButton",
  components: { Loader2 },
  props: {
    variant: {
      type: String,
      default: "secondary",
      validator: (v) => Object.keys(VARIANT_CLASSES).includes(v),
    },
    size: {
      type: String,
      default: "md",
      validator: (v) => Object.keys(SIZE_CLASSES).includes(v),
    },
    icon: {
      type: [Object, Function],
      default: null,
    },
    loading: {
      type: Boolean,
      default: false,
    },
    disabled: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    variantClasses() {
      return VARIANT_CLASSES[this.variant]
    },
    sizeClasses() {
      return SIZE_CLASSES[this.size]
    },
    // Ghost buttons read as flat/text controls — a resting box-shadow on them looks like a
    // stray outline rather than a raised object, so they get the press physics without it.
    depthClass() {
      return this.variant === "ghost" ? "pressable-flat" : "pressable"
    },
    iconSize() {
      return this.size === "sm" ? 13 : 15
    },
  },
}
</script>
