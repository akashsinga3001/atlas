import client from "./client"
import { MarketSentiment } from "../types/market"

export async function getMarketSentiment(): Promise<MarketSentiment> {
    const res = await client.get("/market/sentiment")
    return res.data.data
}

export async function getMarketSentimentHistory(limit = 60): Promise<MarketSentiment[]> {
    const res = await client.get("/market/sentiment/history", { params: { limit } })
    return res.data.data ?? []
}
