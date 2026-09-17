<template>
  <svg :viewBox="`0 0 ${size} ${size}`" :width="size" :height="size">
    <circle v-if="!segments.length" :cx="size / 2" :cy="size / 2" :r="radius" fill="none" :stroke="trackColor" :stroke-width="strokeWidth" />
    <circle
      v-for="seg in arcs"
      :key="seg.label"
      :cx="size / 2"
      :cy="size / 2"
      :r="radius"
      fill="none"
      :stroke="seg.color"
      :stroke-width="strokeWidth"
      :stroke-dasharray="`${seg.length} ${circumference - seg.length}`"
      :stroke-dashoffset="-seg.offset"
      stroke-linecap="butt"
      transform="rotate(-90)"
      :transform-origin="`${size / 2} ${size / 2}`"
    />
    <text :x="size / 2" :y="size / 2 - 6" text-anchor="middle" class="font-mono-nums" :style="{ fontSize: '20px', fontWeight: 600, fill: 'var(--color-text-primary)' }">{{ centerValue }}</text>
    <text :x="size / 2" :y="size / 2 + 14" text-anchor="middle" :style="{ fontSize: '10px', fill: 'var(--color-text-tertiary)' }">{{ centerLabel }}</text>
  </svg>
</template>

<script>
export default {
  name: "DonutChart",
  props: {
    // {label, value, color}[] — value in any consistent unit (₹, %, count); only relative size matters
    segments: {
      type: Array,
      required: true,
    },
    centerValue: {
      type: String,
      default: "",
    },
    centerLabel: {
      type: String,
      default: "",
    },
    size: {
      type: Number,
      default: 160,
    },
  },
  data() {
    return { strokeWidth: 22 }
  },
  computed: {
    radius() {
      return (this.size - this.strokeWidth) / 2
    },
    circumference() {
      return 2 * Math.PI * this.radius
    },
    trackColor() {
      return "var(--color-surface-alt)"
    },
    total() {
      return this.segments.reduce((sum, s) => sum + s.value, 0)
    },
    // Gap of ~1.5deg between segments (2px surface gap equivalent) so adjacent slices read as
    // distinct without a stroke drawn around them.
    arcs() {
      if (!this.total) return []
      const gap = this.circumference * (1.5 / 360)
      let offset = 0
      return this.segments.map((seg) => {
        const raw = (seg.value / this.total) * this.circumference
        const length = Math.max(raw - gap, 0)
        const arc = { label: seg.label, color: seg.color, length, offset }
        offset += raw
        return arc
      })
    },
  },
}
</script>
