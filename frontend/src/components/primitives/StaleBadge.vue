<template>
  <span
    v-if="lastUpdatedAt !== null"
    class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-[11px] font-medium"
    :class="showWarning ? 'bg-[var(--color-warning-bg)] text-[var(--color-warning)]' : 'text-[var(--color-text-tertiary)]'"
  >
    <AlertTriangle v-if="hasError" :size="11" />
    <Clock v-else :size="11" />
    {{ label }} {{ relativeLabel }}
  </span>
</template>

<script>
import { AlertTriangle, Clock } from "@lucide/vue"

export default {
  name: "StaleBadge",
  components: { AlertTriangle, Clock },
  props: {
    lastUpdatedAt: {
      type: Number,
      default: null,
    },
    thresholdMs: {
      type: Number,
      default: 60_000,
    },
    // True when the most recent refresh attempt for this data failed — surfaced immediately,
    // independent of thresholdMs, so a failure is visible before the data itself even looks old.
    hasError: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      now: Date.now(),
      tickHandle: null,
    }
  },
  computed: {
    ageMs() {
      if (this.lastUpdatedAt === null) return null
      return this.now - this.lastUpdatedAt
    },
    stale() {
      return this.ageMs !== null && this.ageMs > this.thresholdMs
    },
    showWarning() {
      return this.stale || this.hasError
    },
    label() {
      if (this.hasError) return "Refresh failed —"
      return this.stale ? "Stale" : "Updated"
    },
    relativeLabel() {
      if (this.ageMs === null) return ""
      const seconds = Math.floor(this.ageMs / 1000)
      if (seconds < 5) return "just now"
      if (seconds < 60) return `${seconds}s ago`
      const minutes = Math.floor(seconds / 60)
      return `${minutes}m ago`
    },
  },
  mounted() {
    this.tickHandle = setInterval(() => {
      this.now = Date.now()
    }, 5000)
  },
  beforeUnmount() {
    if (this.tickHandle) clearInterval(this.tickHandle)
  },
}
</script>
