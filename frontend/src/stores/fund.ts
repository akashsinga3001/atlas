import { defineStore } from "pinia"

import { createCashFlow, fetchCashFlows } from "@/services/api/fund"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { CashFlow, CashFlowCreate } from "@/types/fund"

export const useFundStore = defineStore("fund", {
  state: (): { resource: ResourceState<CashFlow[]> } => ({
    resource: createResourceState<CashFlow[]>(),
  }),
  getters: {
    flows: (state) => (state.resource.data ?? []).slice().sort((a, b) => (a.flow_date < b.flow_date ? 1 : -1)),
  },
  actions: {
    async fetch() {
      await loadResource(this.resource, fetchCashFlows)
    },
    async create(request: CashFlowCreate) {
      const result = await createCashFlow(request)
      if (!result.error) await this.fetch()
      return result
    },
  },
})
