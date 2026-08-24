import { defineStore } from "pinia"

import { fetchOptionsPositions } from "@/services/api/options"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { OptionsPosition } from "@/types/options"

const OPEN_STATUSES = new Set(["pending", "open", "closing"])

export const useOptionsStore = defineStore("options", {
  state: (): { resource: ResourceState<OptionsPosition[]> } => ({
    resource: createResourceState<OptionsPosition[]>(),
  }),
  getters: {
    positions: (state) => state.resource.data ?? [],
    forStrategy: (state) => (strategyId: number) => (state.resource.data ?? []).filter((p) => p.strategy_id === strategyId),
    open: (state) => (state.resource.data ?? []).filter((p) => OPEN_STATUSES.has(p.status)),
  },
  actions: {
    async fetch() {
      await loadResource(this.resource, () => fetchOptionsPositions())
    },
  },
})
