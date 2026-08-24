import { defineStore } from "pinia"

import { activateKillSwitch, deactivateKillSwitch, fetchKillSwitchStatus } from "@/services/api/killSwitch"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { KillSwitch } from "@/types/killSwitch"

export const useKillSwitchStore = defineStore("killSwitch", {
  state: (): { resource: ResourceState<KillSwitch> } => ({
    resource: createResourceState<KillSwitch>(),
  }),
  getters: {
    isActive: (state) => state.resource.data?.enabled ?? false,
    reason: (state) => state.resource.data?.reason ?? null,
  },
  actions: {
    async fetch() {
      await loadResource(this.resource, fetchKillSwitchStatus)
    },
    async activate(reason: string) {
      const result = await activateKillSwitch(reason)
      if (!result.error && result.data) {
        this.resource.data = result.data
        this.resource.lastUpdatedAt = Date.now()
      }
      return result
    },
    async deactivate() {
      const result = await deactivateKillSwitch()
      if (!result.error && result.data) {
        this.resource.data = result.data
        this.resource.lastUpdatedAt = Date.now()
      }
      return result
    },
  },
})
