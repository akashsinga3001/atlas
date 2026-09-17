import { defineStore } from "pinia"

import { fetchStrategyPerformance } from "@/services/api/portfolio"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { StrategyPerformance } from "@/types/portfolio"

export const useStrategyPerformanceStore = defineStore("strategyPerformance", {
  state: (): { resource: ResourceState<StrategyPerformance[]> } => ({
    resource: createResourceState<StrategyPerformance[]>(),
  }),
  actions: {
    async fetch() {
      await loadResource(this.resource, fetchStrategyPerformance)
    },
  },
})
