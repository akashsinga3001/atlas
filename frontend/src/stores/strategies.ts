import { defineStore } from "pinia"

import { fetchStrategies, setStrategyActive } from "@/services/api/strategies"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { Strategy } from "@/types/strategy"

export const useStrategiesStore = defineStore("strategies", {
  state: (): { resource: ResourceState<Strategy[]> } => ({
    resource: createResourceState<Strategy[]>(),
  }),
  getters: {
    strategies: (state) => state.resource.data ?? [],
    activeCount: (state) => (state.resource.data ?? []).filter((s) => s.is_active).length,
    withPositionsCount: (state) => (state.resource.data ?? []).filter((s) => s.open_positions_count > 0).length,
    erroringCount: (state) => (state.resource.data ?? []).filter((s) => s.last_run_status === "FAILED").length,
  },
  actions: {
    async fetch() {
      await loadResource(this.resource, fetchStrategies)
    },
    async setActive(strategyId: number, isActive: boolean) {
      const result = await setStrategyActive(strategyId, isActive)
      if (!result.error) await this.fetch()
      return result
    },
  },
})
