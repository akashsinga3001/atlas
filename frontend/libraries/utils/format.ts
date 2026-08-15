export function formatINR(value: number | null | undefined, compact = false): string {
    if (value === null || value === undefined) return "—"
    const abs = Math.abs(value)
    const sign = value < 0 ? "-" : value > 0 ? "+" : ""
    if (compact) {
        if (abs >= 10000000) return `${sign}₹${(abs / 10000000).toFixed(1)}Cr`
        if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(2)}L`
        if (abs >= 1000) return `${sign}₹${(abs / 1000).toFixed(1)}K`
        return `${sign}₹${abs.toFixed(0)}`
    }
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value)
}

export function pctColor(value: number | null | undefined): string {
    if (value === null || value === undefined) return "text-secondary"
    return value >= 0 ? "text-success" : "text-danger"
}

/** India financial year start (Apr 1). Returns YYYY-MM-DD string. */
export const FY_START: string = (() => {
    const now = new Date()
    const y = now.getFullYear()
    return now >= new Date(`${y}-04-01`) ? `${y}-04-01` : `${y - 1}-04-01`
})()
