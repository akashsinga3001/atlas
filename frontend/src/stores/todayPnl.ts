import { defineStore } from "pinia"

import { fetchTodayPnl } from "@/services/api/portfolio"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { TodayPnlSummary } from "@/types/portfolio"

export const useTodayPnlStore = defineStore("todayPnl", {
  state: (): { resource: ResourceState<TodayPnlSummary> } => ({
    resource: createResourceState<TodayPnlSummary>(),
  }),
  actions: {
    async fetch() {
      await loadResource(this.resource, fetchTodayPnl)
    },
  },
})
