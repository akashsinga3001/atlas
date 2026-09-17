<template>
  <div ref="container" :style="fill ? {} : { height: `${height}px` }" :class="fill ? 'h-full w-full' : 'w-full'" />
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue"
import { createChart, type IChartApi, type ISeriesApi, type Time } from "lightweight-charts"

export interface BarPoint {
  time: string | number
  value: number
}

export default defineComponent({
  name: "BarChart",
  props: {
    data: {
      type: Array as PropType<BarPoint[]>,
      required: true,
    },
    height: {
      type: Number,
      default: 200,
    },
    timeVisible: {
      type: Boolean,
      default: false,
    },
    fill: {
      type: Boolean,
      default: false,
    },
  },
  data() {
    return {
      chart: null as IChartApi | null,
      series: null as ISeriesApi<"Histogram"> | null,
      resizeObserver: null as ResizeObserver | null,
      themeObserver: null as MutationObserver | null,
    }
  },
  watch: {
    data: {
      deep: true,
      handler() {
        this.renderData()
      },
    },
  },
  mounted() {
    this.initChart()
    this.renderData()
  },
  beforeUnmount() {
    this.resizeObserver?.disconnect()
    this.themeObserver?.disconnect()
    this.chart?.remove()
  },
  methods: {
    themeColors() {
      const styles = getComputedStyle(document.documentElement)
      const read = (name: string, fallback: string) => styles.getPropertyValue(name).trim() || fallback
      return {
        text: read("--color-text-tertiary", "#6b6d76"),
        grid: read("--color-border", "rgba(20,21,26,0.08)"),
        border: read("--color-border-strong", "rgba(20,21,26,0.16)"),
        positive: read("--color-positive", "#1f8a5c"),
        negative: read("--color-negative", "#c8402e"),
      }
    },
    initChart() {
      const container = this.$refs.container as HTMLElement
      const c = this.themeColors()
      this.chart = createChart(container, {
        height: this.fill ? container.clientHeight : this.height,
        layout: { background: { color: "transparent" }, textColor: c.text, fontFamily: "'Inter', -apple-system, 'Segoe UI', sans-serif", fontSize: 11, attributionLogo: false },
        grid: { vertLines: { visible: false }, horzLines: { color: c.grid } },
        rightPriceScale: { borderColor: c.border },
        leftPriceScale: { visible: false },
        timeScale: { borderColor: c.border, timeVisible: this.timeVisible, secondsVisible: false },
        crosshair: { vertLine: { color: c.border }, horzLine: { color: c.border } },
      })
      this.series = this.chart.addHistogramSeries({ priceLineVisible: false, lastValueVisible: false, base: 0 })
      this.resizeObserver = new ResizeObserver(() => {
        if (!container || !this.chart) return
        this.chart.applyOptions(this.fill ? { width: container.clientWidth, height: container.clientHeight } : { width: container.clientWidth })
      })
      this.resizeObserver.observe(container)
      this.themeObserver = new MutationObserver(() => this.applyTheme())
      this.themeObserver.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] })
    },
    applyTheme() {
      if (!this.chart) return
      const c = this.themeColors()
      this.chart.applyOptions({
        layout: { textColor: c.text },
        grid: { horzLines: { color: c.grid } },
        rightPriceScale: { borderColor: c.border },
        timeScale: { borderColor: c.border },
        crosshair: { vertLine: { color: c.border }, horzLine: { color: c.border } },
      })
      this.renderData()
    },
    renderData() {
      if (!this.series) return
      const c = this.themeColors()
      const byTime = new Map<string | number, number>()
      for (const point of this.data) byTime.set(point.time, point.value)
      const points = Array.from(byTime.entries())
        .map(([time, value]) => ({ time: time as unknown as Time, value, color: value >= 0 ? c.positive : c.negative }))
        .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0))
      this.series.setData(points)
      this.chart?.timeScale().fitContent()
    },
  },
})
</script>
