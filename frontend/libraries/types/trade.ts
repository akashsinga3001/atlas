export type TradeStatus = "open" | "pending" | "closed"
export type ExitReason = "atr_stop" | "timeout" | "manual"

export interface Security {
    id: number
    ticker: string
    display_name: string
    sector: string | null
    industry: string | null
}

export interface Trade {
    id: number
    security: Security
    status: TradeStatus
    entry_date: string
    fill_price: number | null
    fill_quantity: number | null
    timeout_date: string
    exit_date: string | null
    exit_reason: ExitReason | null
    state: Record<string, unknown>
    invested_value: number | null
    pnl: number | null
    pnl_pct: number | null
}
