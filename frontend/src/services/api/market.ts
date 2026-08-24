import { apiClient } from "./client"
import { unwrap } from "./unwrap"
import type { MarketSentiment } from "@/types/market"

export function fetchMarketSentiment(timeframe = "1d") {
  return unwrap<MarketSentiment>(() => apiClient.get("/market/sentiment", { params: { timeframe } }))
}

export function fetchMarketSentimentHistory(timeframe = "1d", limit = 60) {
  return unwrap<MarketSentiment[]>(() => apiClient.get("/market/sentiment/history", { params: { timeframe, limit } }))
}
