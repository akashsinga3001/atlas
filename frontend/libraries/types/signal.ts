import { Security } from "./trade"

export interface Signal {
    id: number
    security: Security
    observed_at: string
    payload: Record<string, unknown>
    strategy_run_id: number
    strategy_name: string | null
    trade_id: number | null
    trade_status: string | null
    trade_fill_price: number | null
    trade_entry_date: string | null
    trade_pnl_pct: number | null
    trade_pnl: number | null
    signal_close: number | null
    latest_close: number | null
    perf_since_signal: number | null
    signal_status: "entered" | "missed"
}
