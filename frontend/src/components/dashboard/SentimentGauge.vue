<template>
  <div class="flex items-center gap-4">
    <svg :viewBox="`0 0 ${VB_W} ${VB_H}`" :width="size" :height="(size * VB_H) / VB_W" class="shrink-0">
      <path v-for="band in bands" :key="band.key" :d="band.path" fill="none" :stroke="band.color" :stroke-width="strokeWidth" stroke-linecap="butt" />
      <g v-if="hasScore" :transform="`rotate(${needleAngleDeg} ${cx} ${cy})`">
        <line :x1="cx" :y1="cy" :x2="cx + r - strokeWidth / 2 - 2" :y2="cy" stroke="var(--color-text-primary)" stroke-width="2.5" stroke-linecap="round" />
      </g>
      <circle :cx="cx" :cy="cy" r="4" fill="var(--color-text-primary)" />
    </svg>
    <div class="min-w-0">
      <p class="figure-hero leading-none" :class="scoreTextClass">{{ hasScore ? score : "—" }}</p>
      <StatusPill v-if="label" class="mt-2" :label="label" :tone="labelTone" />
    </div>
  </div>
</template>

<script>
import StatusPill from "@/components/primitives/StatusPill.vue"

const VB_W = 200
const VB_H = 118

// Fear & Greed style bands: red <-> gray <-> green, derived from the existing
// semantic negative/inactive/positive tokens via color-mix rather than new hex
// constants, so dark mode's own token values carry through automatically.
const BAND_DEFS = [
  { key: "extreme-fear", from: 0, to: 20, color: "var(--color-negative)" },
  { key: "fear", from: 20, to: 40, color: "color-mix(in srgb, var(--color-negative) 55%, var(--color-inactive) 45%)" },
  { key: "neutral", from: 40, to: 60, color: "var(--color-inactive)" },
  { key: "greed", from: 60, to: 80, color: "color-mix(in srgb, var(--color-positive) 55%, var(--color-inactive) 45%)" },
  { key: "extreme-greed", from: 80, to: 100, color: "var(--color-positive)" },
]

function angleForScore(score) {
  // score 0 -> 180deg (pointing left), score 100 -> 0deg (pointing right)
  return 180 - (score / 100) * 180
}

function pointOnArc(score, radius, cx, cy) {
  const rad = (angleForScore(score) * Math.PI) / 180
  return { x: cx + radius * Math.cos(rad), y: cy - radius * Math.sin(rad) }
}

export default {
  name: "SentimentGauge",
  components: { StatusPill },
  props: {
    score: {
      type: Number,
      default: null,
    },
    label: {
      type: String,
      default: null,
    },
    size: {
      type: Number,
      default: 140,
    },
  },
  data() {
    return { VB_W, VB_H, cx: VB_W / 2, cy: VB_H - 12, r: 80, strokeWidth: 14 }
  },
  computed: {
    hasScore() {
      return this.score !== null && this.score !== undefined
    },
    bands() {
      return BAND_DEFS.map((band) => {
        const p1 = pointOnArc(band.from, this.r, this.cx, this.cy)
        const p2 = pointOnArc(band.to, this.r, this.cx, this.cy)
        return { key: band.key, color: band.color, path: `M ${p1.x} ${p1.y} A ${this.r} ${this.r} 0 0 1 ${p2.x} ${p2.y}` }
      })
    },
    needleAngleDeg() {
      // rotate() is clockwise-positive; angleForScore is a standard math angle, so negate it.
      return this.hasScore ? -angleForScore(this.score) : 0
    },
    labelTone() {
      if (!this.hasScore) return "inactive"
      if (this.score < 40) return "negative"
      if (this.score < 60) return "inactive"
      return "positive"
    },
    scoreTextClass() {
      if (!this.hasScore) return "text-[var(--color-text-tertiary)]"
      if (this.score < 40) return "text-[var(--color-negative)]"
      if (this.score < 60) return "text-[var(--color-text-primary)]"
      return "text-[var(--color-positive)]"
    },
  },
}
</script>
