<template>
  <div class="flex items-end gap-2" :style="{ height: `${height}px` }">
    <div v-for="bucket in buckets" :key="bucket.bucket" class="flex flex-1 flex-col items-center justify-end gap-1.5">
      <span class="font-mono-nums text-[11px] text-[var(--color-text-tertiary)]">{{ bucket.count || "" }}</span>
      <div
        class="w-full rounded-sm"
        :class="bucket.is_win ? 'bg-[var(--color-positive)]' : 'bg-[var(--color-negative)]'"
        :style="{ height: `${barHeight(bucket.count)}px`, opacity: bucket.count === 0 ? 0.15 : 0.85 }"
      />
      <span class="text-center text-[10px] leading-tight text-[var(--color-text-tertiary)]">{{ bucket.bucket }}</span>
    </div>
  </div>
</template>

<script>
export default {
  name: "ReturnDistributionChart",
  props: {
    buckets: {
      type: Array,
      required: true,
    },
    height: {
      type: Number,
      default: 160,
    },
  },
  computed: {
    maxCount() {
      return Math.max(1, ...this.buckets.map((b) => b.count))
    },
  },
  methods: {
    barHeight(count) {
      const plotHeight = this.height - 36
      return count === 0 ? 3 : Math.max(4, (count / this.maxCount) * plotHeight)
    },
  },
}
</script>
