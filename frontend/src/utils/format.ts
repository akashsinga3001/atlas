export function formatCurrency(value: number | null | undefined, options: { compact?: boolean; signed?: boolean } = {}): string {
  if (value === null || value === undefined) return "—"
  const formatter = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: options.compact ? 1 : 0,
    notation: options.compact ? "compact" : "standard",
  })
  const formatted = formatter.format(value)
  return options.signed && value > 0 ? `+${formatted}` : formatted
}

export function formatPercent(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined) return "—"
  const sign = value > 0 ? "+" : ""
  return `${sign}${value.toFixed(digits)}%`
}

export function formatNumber(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined) return "—"
  return new Intl.NumberFormat("en-IN", { maximumFractionDigits: digits }).format(value)
}

// Every date/time in Atlas is IST market time — pin it explicitly rather than relying on the
// viewing browser's local timezone, which silently shifts every displayed timestamp by up to
// 5.5 hours for any viewer (or CI/server session) not itself set to Asia/Kolkata.
const IST_TIME_ZONE = "Asia/Kolkata"

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "—"
  return date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric", timeZone: IST_TIME_ZONE })
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "—"
  return date.toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit", timeZone: IST_TIME_ZONE })
}

/** Today's calendar date in IST as YYYY-MM-DD — never the viewing browser's local/UTC date,
 * which can be a different calendar day than IST for roughly 5.5 hours after UTC midnight. */
export function todayIST(): string {
  const parts = new Intl.DateTimeFormat("en-CA", { timeZone: IST_TIME_ZONE, year: "numeric", month: "2-digit", day: "2-digit" }).formatToParts(new Date())
  const get = (type: string) => parts.find((p) => p.type === type)?.value
  return `${get("year")}-${get("month")}-${get("day")}`
}

/** Tone for P&L-style values — used to drive StatusPill/text coloring consistently across the app. */
export function pnlTone(value: number | null | undefined): "positive" | "negative" | "inactive" {
  if (value === null || value === undefined || value === 0) return "inactive"
  return value > 0 ? "positive" : "negative"
}
