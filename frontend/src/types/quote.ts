export interface LiveQuote {
  last_price: number | null
  change_pct: number | null
  volume: number | null
  high: number | null
  low: number | null
}

export type QuoteMap = Record<string, LiveQuote>

export type ConnectionState = "connecting" | "live" | "reconnecting" | "disconnected"
