"use client"

import { useTrades } from "@/libraries/hooks/useTrades"
import PageHeader from "@/components/layout/PageHeader"
import Card from "@/components/ui/Card"
import Badge from "@/components/ui/Badge"
import Skeleton from "@/components/ui/Skeleton"
import EmptyState from "@/components/ui/EmptyState"
import { TrendingUp } from "lucide-react"

function formatCurrency(value: number | null) {
    if (value === null) return "—"
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value)
}

function formatPct(value: number | null) {
    if (value === null) return "—"
    const sign = value > 0 ? "+" : ""
    return `${sign}${value.toFixed(2)}%`
}

function pctColor(value: number | null) {
    if (value === null) return "text-secondary"
    return value >= 0 ? "text-green-400" : "text-red-400"
}

export default function HoldingsPage() {
    const { data: trades, isLoading, isError } = useTrades("open")

    return (
        <div>
            <PageHeader title="Holdings" subtitle="All open positions" />
            <Card>
                {isLoading && (
                    <div className="flex flex-col gap-3 p-2">
                        {[...Array(5)].map((_, i) => (
                            <Skeleton key={i} className="h-12 w-full" />
                        ))}
                    </div>
                )}
                {isError && <EmptyState icon={TrendingUp} title="Failed to load holdings" description="Check that the backend is running" />}
                {!isLoading && !isError && trades?.length === 0 && <EmptyState icon={TrendingUp} title="No open positions" description="Trades will appear here once entered" />}
                {!isLoading && !isError && trades && trades.length > 0 && (
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border text-left">
                                {["Ticker", "Entry Date", "Qty", "Entry Price", "Invested", "P&L", "P&L %", "Timeout", "Status"].map((h) => (
                                    <th key={h} className="pb-3 pr-6 text-xs text-secondary uppercase tracking-wider font-medium">
                                        {h}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {trades.map((trade) => (
                                <tr key={trade.id} className="border-b border-border last:border-0 hover:bg-surface2 transition-colors">
                                    <td className="py-3 pr-6 font-medium text-primary">{trade.security.ticker}</td>
                                    <td className="py-3 pr-6 text-secondary font-mono">{trade.entry_date}</td>
                                    <td className="py-3 pr-6 text-secondary font-mono">{trade.fill_quantity ?? "—"}</td>
                                    <td className="py-3 pr-6 font-mono">{trade.fill_price ? `₹${trade.fill_price.toFixed(2)}` : "—"}</td>
                                    <td className="py-3 pr-6 font-mono">{formatCurrency(trade.invested_value)}</td>
                                    <td className={`py-3 pr-6 font-mono ${pctColor(trade.pnl)}`}>{formatCurrency(trade.pnl)}</td>
                                    <td className={`py-3 pr-6 font-mono ${pctColor(trade.pnl_pct)}`}>{formatPct(trade.pnl_pct)}</td>
                                    <td className="py-3 pr-6 text-secondary font-mono">{trade.timeout_date}</td>
                                    <td className="py-3">
                                        <Badge label={trade.status} variant="green" />
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </Card>
        </div>
    )
}
