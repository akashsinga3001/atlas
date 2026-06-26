"use client"

import { usePortfolioStats, useEquityCurve } from "@/libraries/hooks/usePortfolio"
import { useTrades } from "@/libraries/hooks/useTrades"
import PageHeader from "@/components/layout/PageHeader"
import Card from "@/components/ui/Card"
import Stat from "@/components/ui/Stat"
import Badge from "@/components/ui/Badge"
import Skeleton from "@/components/ui/Skeleton"
import EmptyState from "@/components/ui/EmptyState"
import { PieChart } from "lucide-react"
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"

function formatCurrency(value: number | null) {
    if (value === null) return "—"
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value)
}

function formatPct(value: number | null) {
    if (value === null) return "—"
    const sign = value > 0 ? "+" : ""
    return `${sign}${value.toFixed(2)}%`
}

export default function PortfolioPage() {
    const { data: stats, isLoading: statsLoading } = usePortfolioStats()
    const { data: curve, isLoading: curveLoading } = useEquityCurve()
    const { data: trades, isLoading: tradesLoading } = useTrades("closed")

    return (
        <div className="flex flex-col gap-8">
            <PageHeader title="Portfolio" subtitle="Historical performance" />

            {/* Stats grid */}
            <div className="grid grid-cols-5 gap-4">
                {statsLoading ? (
                    [...Array(5)].map((_, i) => <Skeleton key={i} className="h-20" />)
                ) : (
                    <>
                        <Card>
                            <Stat label="Total Trades" value={stats?.total_trades ?? "—"} mono={false} />
                        </Card>
                        <Card>
                            <Stat label="Win Rate" value={stats?.win_rate !== null ? `${stats?.win_rate}%` : "—"} />
                        </Card>
                        <Card>
                            <Stat label="Avg Hold" value={stats?.avg_holding_days !== null ? `${stats?.avg_holding_days}d` : "—"} />
                        </Card>
                        <Card>
                            <Stat label="Best Trade" value={formatPct(stats?.best_trade_pct ?? null)} />
                        </Card>
                        <Card>
                            <Stat label="Total P&L" value={formatCurrency(stats?.total_pnl ?? null)} />
                        </Card>
                    </>
                )}
            </div>

            {/* Equity curve */}
            <Card>
                <p className="text-xs uppercase tracking-widest text-secondary font-medium mb-4">Equity Curve</p>
                {curveLoading && <Skeleton className="h-48 w-full" />}
                {!curveLoading && (!curve || curve.length === 0) && <EmptyState icon={PieChart} title="No closed trades yet" description="The equity curve will appear once trades are closed" />}
                {!curveLoading && curve && curve.length > 0 && (
                    <ResponsiveContainer width="100%" height={200}>
                        <AreaChart data={curve}>
                            <defs>
                                <linearGradient id="pnlGradient" x1="0" y1="0" x2="0" y2="1">
                                    <stop offset="5%" stopColor="#D4A017" stopOpacity={0.2} />
                                    <stop offset="95%" stopColor="#D4A017" stopOpacity={0} />
                                </linearGradient>
                            </defs>
                            <XAxis dataKey="date" tick={{ fill: "#888", fontSize: 11 }} tickLine={false} axisLine={false} />
                            <YAxis tick={{ fill: "#888", fontSize: 11 }} tickLine={false} axisLine={false} tickFormatter={(v) => `₹${(v / 1000).toFixed(0)}k`} />
                            <Tooltip contentStyle={{ background: "#111", border: "1px solid #222", borderRadius: 8 }} labelStyle={{ color: "#888" }} itemStyle={{ color: "#D4A017" }} formatter={(v) => [formatCurrency(v as number), "Cumulative P&L"]} />
                            <Area type="monotone" dataKey="cumulative_pnl" stroke="#D4A017" strokeWidth={2} fill="url(#pnlGradient)" dot={false} />
                        </AreaChart>
                    </ResponsiveContainer>
                )}
            </Card>

            {/* Closed trades table */}
            <Card>
                <p className="text-xs uppercase tracking-widest text-secondary font-medium mb-4">Trade History</p>
                {tradesLoading && (
                    <div className="flex flex-col gap-3">
                        {[...Array(5)].map((_, i) => (
                            <Skeleton key={i} className="h-12 w-full" />
                        ))}
                    </div>
                )}
                {!tradesLoading && (!trades || trades.length === 0) && <EmptyState icon={PieChart} title="No closed trades" description="Closed trades will appear here" />}
                {!tradesLoading && trades && trades.length > 0 && (
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border text-left">
                                {["Ticker", "Entry", "Exit", "Entry Price", "Exit Price", "P&L", "P&L %", "Exit Reason"].map((h) => (
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
                                    <td className="py-3 pr-6 text-secondary font-mono">{trade.exit_date ?? "—"}</td>
                                    <td className="py-3 pr-6 font-mono">{trade.fill_price ? `₹${trade.fill_price.toFixed(2)}` : "—"}</td>
                                    <td className="py-3 pr-6 font-mono">{trade.exit_price ? `₹${trade.exit_price.toFixed(2)}` : "—"}</td>
                                    <td className={`py-3 pr-6 font-mono ${trade.pnl !== null && trade.pnl >= 0 ? "text-green-400" : "text-red-400"}`}>{formatCurrency(trade.pnl)}</td>
                                    <td className={`py-3 pr-6 font-mono ${trade.pnl_pct !== null && trade.pnl_pct >= 0 ? "text-green-400" : "text-red-400"}`}>{formatPct(trade.pnl_pct)}</td>
                                    <td className="py-3 pr-6">
                                        <Badge label={trade.exit_reason ?? "—"} variant="muted" />
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
