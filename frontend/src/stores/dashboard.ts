import { defineStore } from "pinia"

import { useCapitalAllocationStore } from "@/stores/capitalAllocation"
import { useCircuitBreakersStore } from "@/stores/circuitBreakers"
import { useEquityCurveStore } from "@/stores/equityCurve"
import { useJobsStore } from "@/stores/jobs"
import { useKillSwitchStore } from "@/stores/killSwitch"
import { useLiveAccountStore } from "@/stores/liveAccount"
import { useMarketStore } from "@/stores/market"
import { usePortfolioStatsStore } from "@/stores/portfolioStats"
import { useSectorExposureStore } from "@/stores/sectorExposure"
import { useStrategiesStore } from "@/stores/strategies"
import { useStrategyPerformanceStore } from "@/stores/strategyPerformance"
import { useTodayPnlStore } from "@/stores/todayPnl"
import { useTradesStore } from "@/stores/trades"

export interface AttentionItem {
  id: string
  tone: "error" | "warning"
  message: string
}

export const useDashboardStore = defineStore("dashboard", {
  getters: {
    attentionItems(): AttentionItem[] {
      const items: AttentionItem[] = []

      const killSwitch = useKillSwitchStore()
      if (killSwitch.isActive) {
        items.push({ id: "kill-switch", tone: "error", message: `New entries paused — ${killSwitch.reason ?? "no reason recorded"}` })
      }

      const breakers = useCircuitBreakersStore()
      for (const breaker of breakers.breakers) {
        if (breaker.enabled && breaker.last_triggered_at) {
          items.push({ id: `breaker-${breaker.id}`, tone: "error", message: `${breaker.type} circuit breaker triggered — ${breaker.last_reason ?? ""}` })
        }
      }

      const capital = useCapitalAllocationStore()
      if (capital.resource.data?.overallocated) {
        items.push({ id: "overallocated", tone: "warning", message: `Combined strategy allocation exceeds 100% (${capital.resource.data.total_allocated_pct}%)` })
      }

      const strategies = useStrategiesStore()
      for (const strategy of strategies.strategies) {
        if (strategy.last_run_status === "FAILED") {
          items.push({ id: `strategy-${strategy.id}-failed`, tone: "warning", message: `${strategy.name}'s last run failed` })
        }
      }

      return items
    },
  },
  actions: {
    async fetchAll() {
      await Promise.all([
        useStrategiesStore().fetch(),
        useKillSwitchStore().fetch(),
        useCircuitBreakersStore().fetch(),
        useCapitalAllocationStore().fetch(),
        useLiveAccountStore().fetch(),
        useMarketStore().fetch(),
        usePortfolioStatsStore().fetch(),
        useSectorExposureStore().fetch(),
        useStrategyPerformanceStore().fetch(),
        useTodayPnlStore().fetch(),
        useEquityCurveStore().fetch(),
        useJobsStore().fetch(),
        useTradesStore().fetch(),
      ])
    },
  },
})
