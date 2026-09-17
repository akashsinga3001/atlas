import { defineStore } from "pinia"

import { fetchSignals } from "@/services/api/signals"
import type { SignalFilters } from "@/services/api/signals"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { Signal } from "@/types/signal"

// Backs the global, filterable Signals ledger (SignalsView) specifically — kept separate from
// stores/signals.ts, which is scoped to one strategy's signal list (SignalsPanel) and would
// collide with this one's filters/resource if they shared the same Pinia store id.
export const useSignalsLedgerStore = defineStore("signalsLedger", {
  state: (): { resource: ResourceState<Signal[]> } => ({
    resource: createResourceState<Signal[]>(),
  }),
  actions: {
    async fetch(filters: SignalFilters = {}) {
      await loadResource(this.resource, () => fetchSignals(filters))
    },
  },
})
