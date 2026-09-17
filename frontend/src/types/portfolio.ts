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
  net_deposits: number
  true_return_pct: number | null
}

export interface EquityCurvePoint {
  date: string
  cumulative_pnl: number
  trade_id: number
  ticker: string
  pnl: number
}

export interface LiveAccountValue {
  cash_balance: number
  holdings_value: number
  total_value: number
  computed_at: string
}

export interface NavCurvePoint {
  date: string
  cash_balance: number
  holdings_value: number
  total_value: number
  cash_flow: number | null
}

export interface CapitalAllocationStrategy {
  strategy_id: number
  code: string
  name: string
  is_active: boolean
  account_capital_pct: number
  allocated_amount: number
  deployed_amount: number
  deployed_pct_of_allocated: number | null
}

export interface CapitalAllocation {
  account_size: number | null
  strategies: CapitalAllocationStrategy[]
  total_allocated_pct: number
  overallocated: boolean
}

export interface SectorExposureSector {
  sector: string
  exposure_amount: number
  position_count: number
  pct_of_nav: number | null
}

export interface SectorExposure {
  account_size: number | null
  sectors: SectorExposureSector[]
  largest_position: { ticker: string; pct_of_nav: number | null } | null
  largest_sector: { sector: string; pct_of_nav: number | null } | null
}

export interface TodayPnlSummary {
  realized_today: number
  unrealized_now: number
  total_today: number
}

export interface StrategyPerformance {
  strategy_id: number
  name: string
  positions: number
  pnl: number
  return_pct: number | null
}

export interface ReturnDistributionBucket {
  bucket: string
  count: number
  is_win: boolean
}

export interface SectorPerformance {
  sector: string
  trades: number
  wins: number
  win_rate: number | null
  avg_return: number | null
}

export interface PortfolioAnalytics {
  return_distribution: ReturnDistributionBucket[]
  sector_performance: SectorPerformance[]
}
