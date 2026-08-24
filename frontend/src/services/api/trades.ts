import { apiClient } from "./client"
import { unwrap } from "./unwrap"
import type { Trade, TradeStatus } from "@/types/trade"

export function fetchTrades(status?: TradeStatus) {
  return unwrap<Trade[]>(() => apiClient.get("/trades", { params: status ? { status } : undefined }))
}
