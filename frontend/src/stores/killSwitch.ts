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
        // Route through the same status/error fields fetch() uses — a stale "error" status from
        // a prior failed refresh must not survive a subsequent successful action, and a failed
        // action needs `error` set or nothing downstream (e.g. a future StaleBadge) can see it.
        this.resource.status = "success"
        this.resource.error = null
      } else {
        this.resource.status = "error"
        this.resource.error = result.message ?? "Request failed"
      }
      return result
    },
    async deactivate() {
      const result = await deactivateKillSwitch()
      if (!result.error && result.data) {
        this.resource.data = result.data
        this.resource.lastUpdatedAt = Date.now()
        this.resource.status = "success"
        this.resource.error = null
      } else {
        this.resource.status = "error"
        this.resource.error = result.message ?? "Request failed"
      }
      return result
    },
  },
})
