export function formatCurrency(value: number | null | undefined, options: { compact?: boolean } = {}): string {
  if (value === null || value === undefined) return "—"
  const formatter = new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: options.compact ? 1 : 0,
    notation: options.compact ? "compact" : "standard",
  })
  return formatter.format(value)
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

export function formatDate(value: string | null | undefined): string {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "—"
  return date.toLocaleDateString("en-IN", { day: "2-digit", month: "short", year: "numeric" })
}

export function formatDateTime(value: string | null | undefined): string {
  if (!value) return "—"
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return "—"
  return date.toLocaleString("en-IN", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" })
}

/** Tone for P&L-style values — used to drive StatusPill/text coloring consistently across the app. */
export function pnlTone(value: number | null | undefined): "positive" | "negative" | "inactive" {
  if (value === null || value === undefined || value === 0) return "inactive"
  return value > 0 ? "positive" : "negative"
}
