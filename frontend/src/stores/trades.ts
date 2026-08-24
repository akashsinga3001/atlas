import { defineStore } from "pinia"

import { fetchTrades } from "@/services/api/trades"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { Trade } from "@/types/trade"

export const useTradesStore = defineStore("trades", {
  state: (): { resource: ResourceState<Trade[]> } => ({
    resource: createResourceState<Trade[]>(),
  }),
  getters: {
    trades: (state) => state.resource.data ?? [],
    forStrategy: (state) => (strategyId: number) => (state.resource.data ?? []).filter((t) => t.strategy_id === strategyId),
    openOrPending: (state) => (state.resource.data ?? []).filter((t) => t.status === "open" || t.status === "pending"),
  },
  actions: {
    async fetch() {
      await loadResource(this.resource, () => fetchTrades())
    },
  },
})
