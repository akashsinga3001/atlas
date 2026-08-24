import { defineStore } from "pinia"

import { fetchMarketSentiment, fetchMarketSentimentHistory } from "@/services/api/market"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { MarketSentiment } from "@/types/market"

export const useMarketStore = defineStore("market", {
  state: (): { resource: ResourceState<MarketSentiment>; history: ResourceState<MarketSentiment[]> } => ({
    resource: createResourceState<MarketSentiment>(),
    history: createResourceState<MarketSentiment[]>(),
  }),
  getters: {
    scoreHistory: (state) => (state.history.data ?? []).map((h) => h.regime_score).filter((v) => v !== null),
  },
  actions: {
    async fetch() {
      await Promise.all([loadResource(this.resource, () => fetchMarketSentiment()), loadResource(this.history, () => fetchMarketSentimentHistory())])
    },
  },
})
