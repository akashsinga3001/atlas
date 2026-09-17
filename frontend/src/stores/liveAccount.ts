import { defineStore } from "pinia"

import { fetchLiveAccountValue } from "@/services/api/portfolio"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { LiveAccountValue } from "@/types/portfolio"

export const useLiveAccountStore = defineStore("liveAccount", {
  state: (): { resource: ResourceState<LiveAccountValue> } => ({
    resource: createResourceState<LiveAccountValue>(),
  }),
  actions: {
    async fetch() {
      await loadResource(this.resource, fetchLiveAccountValue)
    },
  },
})
