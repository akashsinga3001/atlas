<template>
  <span class="font-mono-nums" :class="toneClass">
    {{ display }}
    <span v-if="isLive" class="ml-1 inline-block h-1.5 w-1.5 rounded-full bg-[var(--color-live)]" title="Live" />
  </span>
</template>

<script>
import { formatCurrency, pnlTone } from "@/utils/format"

export default {
  name: "LivePnlCell",
  props: {
    value: {
      type: Number,
      default: null,
    },
    isLive: {
      type: Boolean,
      default: false,
    },
  },
  computed: {
    display() {
      return formatCurrency(this.value)
    },
    toneClass() {
      const tone = pnlTone(this.value)
      if (tone === "positive") return "text-[var(--color-positive)]"
      if (tone === "negative") return "text-[var(--color-negative)]"
      return "text-[var(--color-text-secondary)]"
    },
  },
}
</script>
