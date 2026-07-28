import { useQuery } from "@tanstack/react-query"
import { getMarketSentiment, getMarketSentimentHistory } from "../api/market"

export function useMarketSentiment() {
    return useQuery({
        queryKey: ["market", "sentiment"],
        queryFn: getMarketSentiment
    })
}

export function useMarketSentimentHistory(limit = 60) {
    return useQuery({
        queryKey: ["market", "sentiment", "history", limit],
        queryFn: () => getMarketSentimentHistory(limit)
    })
}
