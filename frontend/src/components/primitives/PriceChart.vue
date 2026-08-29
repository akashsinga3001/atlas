<template>
  <div ref="container" :style="{ height: `${height}px` }" class="w-full" />
</template>

<script lang="ts">
import { defineComponent, type PropType } from "vue"
import { createChart, type IChartApi, type ISeriesApi, type Time } from "lightweight-charts"

export interface ChartSeries {
  name: string
  color: string
  data: { time: string; value: number }[]
  lineStyle?: 0 | 1 | 2 // 0 = solid, 1 = dotted, 2 = dashed
}

export default defineComponent({
  name: "PriceChart",
  props: {
    series: {
      type: Array as PropType<ChartSeries[]>,
      required: true,
    },
    height: {
      type: Number,
      default: 280,
    },
  },
  data() {
    return {
      chart: null as IChartApi | null,
      seriesRefs: [] as ISeriesApi<"Line">[],
      resizeObserver: null as ResizeObserver | null,
    }
  },
  watch: {
    series: {
      deep: true,
      handler() {
        this.renderSeries()
      },
    },
  },
  mounted() {
    this.initChart()
    this.renderSeries()
  },
  beforeUnmount() {
    this.resizeObserver?.disconnect()
    this.chart?.remove()
  },
  methods: {
    initChart() {
      const container = this.$refs.container as HTMLElement
      this.chart = createChart(container, {
        height: this.height,
        layout: { background: { color: "transparent" }, textColor: "#6b6d76", fontFamily: "'Inter', -apple-system, 'Segoe UI', sans-serif", fontSize: 11, attributionLogo: false },
        grid: { vertLines: { color: "rgba(20,21,26,0.05)" }, horzLines: { color: "rgba(20,21,26,0.05)" } },
        rightPriceScale: { borderColor: "rgba(20,21,26,0.1)" },
        leftPriceScale: { visible: false },
        timeScale: { borderColor: "rgba(20,21,26,0.1)" },
        crosshair: { vertLine: { color: "rgba(20,21,26,0.25)" }, horzLine: { color: "rgba(20,21,26,0.25)" } },
      })
      this.resizeObserver = new ResizeObserver(() => {
        if (container && this.chart) this.chart.applyOptions({ width: container.clientWidth })
      })
      this.resizeObserver.observe(container)
    },
    renderSeries() {
      if (!this.chart) return
      for (const s of this.seriesRefs) this.chart.removeSeries(s)
      this.seriesRefs = []

      for (const s of this.series) {
        const line = this.chart.addLineSeries({ color: s.color, lineWidth: 2, lineStyle: s.lineStyle ?? 0, priceLineVisible: false, lastValueVisible: false })
        line.setData(this.dedupeByTime(s.data).map((d) => ({ time: d.time as unknown as Time, value: d.value })))
        this.seriesRefs.push(line)
      }
      this.chart.timeScale().fitContent()
    },
    // lightweight-charts requires strictly ascending, unique timestamps. Source data can have more
    // than one point on the same day (e.g. multiple trades closing the same date on the equity
    // curve) — keep the last value per day, which is the correct end-of-day representation anyway.
    dedupeByTime(points: { time: string; value: number }[]) {
      const byTime = new Map<string, number>()
      for (const point of points) byTime.set(point.time, point.value)
      return Array.from(byTime.entries())
        .map(([time, value]) => ({ time, value }))
        .sort((a, b) => (a.time < b.time ? -1 : a.time > b.time ? 1 : 0))
    },
  },
})
</script>
