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
    sharpe_ratio: number | null
    max_drawdown_pct: number | null
    profit_factor: number | null
    net_deposits: number | null
    true_return_pct: number | null
}

export interface NavCurvePoint {
    date: string
    cash_balance: number
    holdings_value: number
    total_value: number
    cash_flow: number | null
}

export type FlowType = "deposit" | "withdrawal"

export interface CashFlow {
    id: number
    flow_type: FlowType
    amount: number
    flow_date: string
    note: string | null
}

export interface EquityCurvePoint {
    date: string
    cumulative_pnl: number
    trade_id: number
    ticker: string
    pnl: number
}

export interface ReturnBucket {
    bucket: string
    count: number
    is_win: boolean
}

export interface SectorStat {
    sector: string
    trades: number
    wins: number
    win_rate: number | null
    avg_return: number | null
}

export interface PortfolioAnalytics {
    return_distribution: ReturnBucket[]
    sector_performance: SectorStat[]
}
