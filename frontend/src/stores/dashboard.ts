import { defineStore } from "pinia"

import { useCapitalAllocationStore } from "@/stores/capitalAllocation"
import { useCircuitBreakersStore } from "@/stores/circuitBreakers"
import { useKillSwitchStore } from "@/stores/killSwitch"
import { useMarketStore } from "@/stores/market"
import { usePortfolioStatsStore } from "@/stores/portfolioStats"
import { useStrategiesStore } from "@/stores/strategies"

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
        useMarketStore().fetch(),
        usePortfolioStatsStore().fetch(),
      ])
    },
  },
})
