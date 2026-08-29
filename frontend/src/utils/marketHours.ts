// Derives NSE market session state client-side from the known trading calendar (09:15-15:30 IST,
// weekdays) — not a backend field, but not fabricated data either: same trading-hours assumption
// the backend's own job scheduling already relies on.

export type MarketSession = "open" | "pre-market" | "post-market" | "closed"

export function getMarketSession(now: Date = new Date()): MarketSession {
  const ist = new Date(now.toLocaleString("en-US", { timeZone: "Asia/Kolkata" }))
  const day = ist.getDay()
  if (day === 0 || day === 6) return "closed"

  const minutes = ist.getHours() * 60 + ist.getMinutes()
  if (minutes < 9 * 60) return "closed"
  if (minutes < 9 * 60 + 15) return "pre-market"
  if (minutes <= 15 * 60 + 30) return "open"
  return "post-market"
}
