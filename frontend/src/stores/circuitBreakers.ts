import { defineStore } from "pinia"

import { acknowledgeCircuitBreaker, fetchCircuitBreakers, updateCircuitBreaker } from "@/services/api/circuitBreakers"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { CircuitBreaker, UpdateCircuitBreakerRequest } from "@/types/circuitBreaker"

export const useCircuitBreakersStore = defineStore("circuitBreakers", {
  state: (): { resource: ResourceState<CircuitBreaker[]> } => ({
    resource: createResourceState<CircuitBreaker[]>(),
  }),
  getters: {
    breakers: (state) => state.resource.data ?? [],
    anyTriggered: (state) => (state.resource.data ?? []).some((b) => b.enabled && b.last_triggered_at !== null),
  },
  actions: {
    async fetch() {
      await loadResource(this.resource, fetchCircuitBreakers)
    },
    async toggle(breakerId: number, enabled: boolean) {
      return this.update(breakerId, { enabled })
    },
    async update(breakerId: number, request: UpdateCircuitBreakerRequest) {
      const result = await updateCircuitBreaker(breakerId, request)
      if (!result.error) await this.fetch()
      return result
    },
    async acknowledge(breakerId: number) {
      const result = await acknowledgeCircuitBreaker(breakerId)
      if (!result.error) await this.fetch()
      return result
    },
  },
})
