import { Security } from "./trade"

export interface Signal {
    id: number
    security: Security
    observed_at: string
    payload: Record<string, unknown>
    strategy_run_id: number
    trade_id: number | null
    trade_status: string | null
    trade_fill_price: number | null
    trade_entry_date: string | null
    signal_status: "entered" | "missed"
}
