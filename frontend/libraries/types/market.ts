export interface MarketSentiment {
    candle_timestamp: string
    regime_score: number | null
    label: string | null
    advance_decline_ratio: number | null
    market_breadth_ema20: number | null
    market_breadth_ema50: number | null
    pct_above_ema20: number | null
    pct_above_ema50: number | null
    pct_above_ema200: number | null
    new_highs_count: number | null
    new_lows_count: number | null
}
