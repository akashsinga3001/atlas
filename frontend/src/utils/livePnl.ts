import type { Trade } from "@/types/trade"
import type { QuoteMap } from "@/types/quote"

/** Mirrors PortfolioService._get_equity_unrealized_pnl — mark-to-market on a single-leg equity trade. */
export function computeEquityLivePnl(trade: Trade, quotes: QuoteMap): number | null {
  if (trade.status !== "open" || trade.fill_price === null || trade.fill_quantity === null) return null
  const ltp = quotes[trade.security.ticker]?.last_price
  if (ltp === null || ltp === undefined) return null
  return (ltp - trade.fill_price) * trade.fill_quantity
}
