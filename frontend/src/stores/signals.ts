import { defineStore } from "pinia"

import { fetchSignals } from "@/services/api/signals"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { Signal } from "@/types/signal"

export const useSignalsStore = defineStore("signals", {
  state: (): { resource: ResourceState<Signal[]>; strategyName: string | null } => ({
    resource: createResourceState<Signal[]>(),
    strategyName: null,
  }),
  actions: {
    async loadForStrategy(strategyName: string) {
      this.strategyName = strategyName
      this.resource = createResourceState<Signal[]>()
      await loadResource(this.resource, () => fetchSignals({ strategy: strategyName }))
    },
  },
})
