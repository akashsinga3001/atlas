import type { SecurityInfo } from "./trade"

export type SignalStatus = "entered" | "missed"

export interface Signal {
  id: number
  security: SecurityInfo
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
  signal_status: SignalStatus
}

export interface SignalForwardDataPoint {
  date: string
  close: number
  stop_price: number | null
  atr_14: number | null
  mtm_pct: number | null
  exit_triggered: boolean
}

export interface SignalPerformance {
  signal: {
    id: number
    security: SecurityInfo
    observed_at: string
    strategy_name: string | null
    signal_status: SignalStatus
    trade_id: number | null
    trade_status: string | null
    fill_price: number | null
    fill_quantity: number | null
    entry_date: string | null
    exit_date: string | null
    exit_reason: string | null
    timeout_date: string | null
  }
  forward_data: SignalForwardDataPoint[]
  summary: {
    signal_close: number | null
    latest_close: number | null
    perf_since_signal: number | null
    max_close: number | null
    max_perf: number | null
    days_since_signal: number
    exit_triggered_on: string | null
    trade_pnl_pct: number | null
    simulated: boolean
  }
}
