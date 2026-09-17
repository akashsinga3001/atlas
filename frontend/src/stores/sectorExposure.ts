import { defineStore } from "pinia"

import { fetchSectorExposure } from "@/services/api/portfolio"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { SectorExposure } from "@/types/portfolio"

export const useSectorExposureStore = defineStore("sectorExposure", {
  state: (): { resource: ResourceState<SectorExposure> } => ({
    resource: createResourceState<SectorExposure>(),
  }),
  actions: {
    async fetch() {
      await loadResource(this.resource, fetchSectorExposure)
    },
  },
})
