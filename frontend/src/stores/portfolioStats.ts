import { defineStore } from "pinia"

import { fetchPortfolioStats } from "@/services/api/portfolio"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { PortfolioStats } from "@/types/portfolio"

export const usePortfolioStatsStore = defineStore("portfolioStats", {
  state: (): { resource: ResourceState<PortfolioStats> } => ({
    resource: createResourceState<PortfolioStats>(),
  }),
  actions: {
    async fetch() {
      await loadResource(this.resource, fetchPortfolioStats)
    },
  },
})
