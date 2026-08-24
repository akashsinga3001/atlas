import { defineStore } from "pinia"

import { fetchCapitalAllocation } from "@/services/api/portfolio"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { CapitalAllocation } from "@/types/portfolio"

export const useCapitalAllocationStore = defineStore("capitalAllocation", {
  state: (): { resource: ResourceState<CapitalAllocation> } => ({
    resource: createResourceState<CapitalAllocation>(),
  }),
  actions: {
    async fetch() {
      await loadResource(this.resource, fetchCapitalAllocation)
    },
  },
})
