import { defineStore } from "pinia"

import { fetchEquityCurve, fetchNavCurve } from "@/services/api/portfolio"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { EquityCurvePoint, NavCurvePoint } from "@/types/portfolio"

export const useEquityCurveStore = defineStore("equityCurve", {
  state: (): { equity: ResourceState<EquityCurvePoint[]>; nav: ResourceState<NavCurvePoint[]> } => ({
    equity: createResourceState<EquityCurvePoint[]>(),
    nav: createResourceState<NavCurvePoint[]>(),
  }),
  actions: {
    async fetch() {
      await Promise.all([loadResource(this.equity, fetchEquityCurve), loadResource(this.nav, fetchNavCurve)])
    },
  },
})
