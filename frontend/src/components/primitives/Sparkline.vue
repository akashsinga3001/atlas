<template>
  <svg :viewBox="`0 0 ${width} ${height}`" :width="width" :height="height" preserveAspectRatio="none" class="overflow-visible">
    <defs>
      <linearGradient :id="gradientId" x1="0" y1="0" x2="0" y2="1">
        <stop offset="0%" :stop-color="color" stop-opacity="0.35" />
        <stop offset="100%" :stop-color="color" stop-opacity="0" />
      </linearGradient>
    </defs>
    <path v-if="areaPath" :d="areaPath" :fill="`url(#${gradientId})`" />
    <polyline v-if="points.length > 1" :points="linePoints" fill="none" :stroke="color" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" />
    <circle v-if="points.length" :cx="lastPoint.x" :cy="lastPoint.y" r="2.25" :fill="color" />
  </svg>
</template>

<script>
export default {
  name: "Sparkline",
  props: {
    values: {
      type: Array,
      required: true,
    },
    color: {
      type: String,
      default: "#16171c",
    },
    width: {
      type: Number,
      default: 96,
    },
    height: {
      type: Number,
      default: 32,
    },
  },
  computed: {
    gradientId() {
      return `sparkline-${Math.random().toString(36).slice(2, 9)}`
    },
    points() {
      if (!this.values.length) return []
      const min = Math.min(...this.values)
      const max = Math.max(...this.values)
      const range = max - min || 1
      const step = this.values.length > 1 ? this.width / (this.values.length - 1) : 0
      return this.values.map((v, i) => ({
        x: i * step,
        y: this.height - ((v - min) / range) * (this.height - 4) - 2,
      }))
    },
    linePoints() {
      return this.points.map((p) => `${p.x},${p.y}`).join(" ")
    },
    lastPoint() {
      return this.points[this.points.length - 1]
    },
    areaPath() {
      if (this.points.length < 2) return ""
      const line = this.points.map((p) => `${p.x},${p.y}`).join(" L")
      return `M${line} L${this.width},${this.height} L0,${this.height} Z`
    },
  },
}
</script>
