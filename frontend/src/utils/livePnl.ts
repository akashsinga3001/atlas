import type { Trade } from "@/types/trade"
import type { OptionsPosition } from "@/types/options"
import type { QuoteMap } from "@/types/quote"

const SHORT_ROLES = new Set(["short_call", "short_put"])

/** Mirrors PortfolioService._get_equity_unrealized_pnl — mark-to-market on a single-leg equity trade. */
export function computeEquityLivePnl(trade: Trade, quotes: QuoteMap): number | null {
  if (trade.status !== "open" || trade.fill_price === null || trade.fill_quantity === null) return null
  const ltp = quotes[trade.security.ticker]?.last_price
  if (ltp === null || ltp === undefined) return null
  return (ltp - trade.fill_price) * trade.fill_quantity
}

/** Mirrors OptionsTradeService.get_unrealized_pnl — sums mark-to-market across each OPEN leg, short legs profit when price falls. */
export function computeOptionsLivePnl(position: OptionsPosition, quotes: QuoteMap): number | null {
  const openLegs = position.legs.filter((leg) => leg.status === "open" && leg.entry_fill_price !== null && leg.entry_fill_quantity !== null)
  if (!openLegs.length) return null

  let total = 0
  for (const leg of openLegs) {
    const ltp = quotes[leg.ticker]?.last_price
    if (ltp === null || ltp === undefined) return null
    const entry = leg.entry_fill_price as number
    const qty = leg.entry_fill_quantity as number
    total += SHORT_ROLES.has(leg.role) ? (entry - ltp) * qty : (ltp - entry) * qty
  }
  return total
}
