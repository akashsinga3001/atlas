import { defineStore } from "pinia"

import { fetchPortfolioAnalytics } from "@/services/api/portfolio"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { PortfolioAnalytics } from "@/types/portfolio"

export const usePortfolioAnalyticsStore = defineStore("portfolioAnalytics", {
  state: (): { resource: ResourceState<PortfolioAnalytics> } => ({
    resource: createResourceState<PortfolioAnalytics>(),
  }),
  actions: {
    async fetch() {
      await loadResource(this.resource, fetchPortfolioAnalytics)
    },
  },
})
