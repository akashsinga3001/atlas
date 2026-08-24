export type OptionsPositionStatus = "pending" | "open" | "closing" | "closed" | "failed" | "skipped"
export type OptionsLegRole = "short_call" | "short_put" | "long_call" | "long_put"
export type OptionsLegStatus = "pending" | "open" | "closed" | "failed"
export type OptionsExitReason = "time_exit" | "expiry_exit"

export interface OptionsLeg {
  id: number
  role: OptionsLegRole
  status: OptionsLegStatus
  ticker: string
  strike: number | null
  option_type: string | null
  entry_fill_price: number | null
  entry_fill_quantity: number | null
  exit_fill_price: number | null
  exit_fill_quantity: number | null
}

export interface OptionsPosition {
  id: number
  strategy_id: number
  strategy_code: string
  strategy_name: string
  status: OptionsPositionStatus
  signal_date: string
  entry_date: string
  spot_at_signal: number
  expiry_date: string | null
  call_short_strike: number | null
  put_short_strike: number | null
  call_long_strike: number | null
  put_long_strike: number | null
  lots: number | null
  lot_size: number | null
  margin_per_lot: number | null
  net_credit_per_lot: number | null
  margin_total: number | null
  net_credit_total: number | null
  planned_exit_date: string | null
  exit_date: string | null
  exit_reason: OptionsExitReason | null
  skip_reason: string | null
  realized_pnl: number | null
  legs: OptionsLeg[]
}
