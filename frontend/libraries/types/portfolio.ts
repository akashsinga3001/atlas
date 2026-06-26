export interface PortfolioStats {
    total_trades: number
    open_trades: number
    closed_trades: number
    win_rate: number | null
    avg_holding_days: number | null
    avg_win_pct: number | null
    avg_loss_pct: number | null
    best_trade_pct: number | null
    worst_trade_pct: number | null
    total_pnl: number | null
}

export interface EquityCurvePoint {
    date: string
    cumulative_pnl: number
    trade_id: number
    ticker: string
    pnl: number
}
