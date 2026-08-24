import { defineStore } from "pinia"

import { fetchSignalPerformance } from "@/services/api/signals"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { SignalPerformance } from "@/types/signal"

export const useSignalDetailStore = defineStore("signalDetail", {
  state: (): { resource: ResourceState<SignalPerformance> } => ({
    resource: createResourceState<SignalPerformance>(),
  }),
  actions: {
    async loadFor(signalId: number) {
      this.resource = createResourceState<SignalPerformance>()
      await loadResource(this.resource, () => fetchSignalPerformance(signalId))
    },
  },
})
