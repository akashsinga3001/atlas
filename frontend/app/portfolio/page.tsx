"use client"

import { usePortfolioStats, useEquityCurve } from "@/libraries/hooks/usePortfolio"
import { useTrades } from "@/libraries/hooks/useTrades"
import Card from "@/components/ui/Card"
import Badge from "@/components/ui/Badge"
import Skeleton from "@/components/ui/Skeleton"
import { motion } from "framer-motion"
import { TrendingUp, TrendingDown, Minus } from "lucide-react"
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

function formatINR(value: number | null | undefined, compact = false) {
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

function pctColor(value: number | null | undefined) {
    if (value === null || value === undefined) return "text-secondary"
    return value >= 0 ? "text-green-400" : "text-red-400"
}

const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    const pnl = payload[0]?.value
    const tradePnl = payload[0]?.payload?.pnl
    return (
        <div className="rounded-xl px-3 py-2.5 text-xs" style={{ background: "#161616", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="text-secondary font-mono mb-2">{label}</div>
            <div className={`font-bold font-mono text-sm ${pnl >= 0 ? "text-green-400" : "text-red-400"}`}>{formatINR(pnl, true)}</div>
            {tradePnl !== undefined && <div className={`text-[10px] font-mono mt-0.5 ${tradePnl >= 0 ? "text-green-400/70" : "text-red-400/70"}`}>Trade: {formatINR(tradePnl, true)}</div>}
        </div>
    )
}

export default function PortfolioPage() {
    const { data: stats, isLoading: statsLoading } = usePortfolioStats()
    const { data: curve, isLoading: curveLoading } = useEquityCurve()
    const { data: trades, isLoading: tradesLoading } = useTrades("closed")

    const pnlPositive = !stats?.total_pnl || stats.total_pnl >= 0
    const chartColor = pnlPositive ? "#4ade80" : "#f87171"
    const pnlColor = stats?.total_pnl !== undefined && stats?.total_pnl !== null ? (stats.total_pnl >= 0 ? "text-green-400" : "text-red-400") : "text-secondary"

    return (
        <div className="flex flex-col gap-6">

            {/* Hero */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between">
                <div>
                    <p className="text-[10px] uppercase tracking-[0.2em] text-secondary mb-1">Performance</p>
                    <h1 className="text-4xl font-bold tracking-tight text-primary leading-none">Portfolio</h1>
                </div>
                <div className="flex flex-col items-end gap-1">
                    <span className="text-[10px] uppercase tracking-[0.15em] text-secondary">Total P&amp;L</span>
                    {statsLoading ? <Skeleton className="h-12 w-36" /> : <span className={`text-5xl font-bold font-mono leading-none ${pnlColor}`}>{formatINR(stats?.total_pnl, true)}</span>}
                </div>
            </motion.div>

            {/* Equity curve — hero of this page, full width */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.5, ease }}>
                <Card padding="md" className="flex flex-col gap-4">
                    <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase tracking-[0.15em] text-secondary font-medium">Equity Curve</span>
                        {!curveLoading && curve && <span className="text-[10px] text-muted font-mono">{curve.length} closed trades</span>}
                    </div>
                    {curveLoading && <Skeleton className="rounded-lg" style={{ height: 300 }} />}
                    {!curveLoading && (!curve || curve.length === 0) && (
                        <div className="flex items-center justify-center" style={{ height: 300 }}>
                            <p className="text-sm text-secondary">No closed trades yet</p>
                        </div>
                    )}
                    {!curveLoading && curve && curve.length > 0 && (
                        <div style={{ height: 300 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={curve} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                                    <defs>
                                        <linearGradient id="curveGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor={chartColor} stopOpacity={0.25} />
                                            <stop offset="100%" stopColor={chartColor} stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} tickFormatter={v => v?.slice(5)} />
                                    <YAxis tick={{ fontSize: 10, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} tickFormatter={v => formatINR(v, true)} width={64} />
                                    <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Area type="monotone" dataKey="cumulative_pnl" stroke={chartColor} strokeWidth={2} fill="url(#curveGrad)" dot={false} />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </Card>
            </motion.div>

            {/* Stats strip — horizontal, below chart */}
            <div className="grid grid-cols-5 gap-3">
                {[
                    { label: "Closed Trades", value: statsLoading ? "—" : String(stats?.closed_trades ?? 0) },
                    { label: "Win Rate", value: statsLoading ? "—" : stats?.win_rate !== null && stats?.win_rate !== undefined ? `${stats.win_rate}%` : "—" },
                    { label: "Avg Hold", value: statsLoading ? "—" : stats?.avg_holding_days !== null && stats?.avg_holding_days !== undefined ? `${stats.avg_holding_days}d` : "—" },
                    { label: "Avg Win", value: statsLoading ? "—" : stats?.avg_win_pct !== null && stats?.avg_win_pct !== undefined ? `+${stats.avg_win_pct.toFixed(2)}%` : "—" },
                    { label: "Avg Loss", value: statsLoading ? "—" : stats?.avg_loss_pct !== null && stats?.avg_loss_pct !== undefined ? `${stats.avg_loss_pct.toFixed(2)}%` : "—" }
                ].map(({ label, value }, i) => (
                    <motion.div key={label} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 + i * 0.05, duration: 0.35, ease }}>
                        <div className="flex flex-col gap-1.5 px-4 py-4 rounded-xl bg-surface2 border border-white/4">
                            <span className="text-[10px] uppercase tracking-[0.15em] text-secondary font-medium">{label}</span>
                            <span className="text-xl font-bold text-primary font-mono leading-none">{value}</span>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Trade history */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35, duration: 0.4, ease }}>
                <Card padding="sm">
                    <div className="px-4 pt-3 pb-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <span className="text-[10px] uppercase tracking-[0.15em] text-secondary font-medium">Trade History</span>
                    </div>
                    {tradesLoading && <div className="flex flex-col gap-2 p-3">{[...Array(5)].map((_, i) => <Skeleton key={i} className="h-14 rounded-lg" />)}</div>}
                    {!tradesLoading && (!trades || trades.length === 0) && (
                        <div className="py-16 text-center">
                            <p className="text-sm font-medium text-primary mb-1">No closed trades</p>
                            <p className="text-xs text-secondary">Closed trades will appear here</p>
                        </div>
                    )}
                    {!tradesLoading && trades && trades.length > 0 && (
                        <table className="w-full text-sm">
                            <thead>
                                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                                    {["Ticker", "Entry", "Exit", "Entry ₹", "Exit ₹", "P&L", "P&L %", "Days", "Reason"].map(h => (
                                        <th key={h} className="py-3 pr-6 first:pl-4 text-[10px] text-secondary uppercase tracking-[0.12em] font-medium text-left">{h}</th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {trades.map((trade, i) => {
                                    const pnlUp = trade.pnl !== null ? trade.pnl >= 0 : null
                                    const PnlIcon = pnlUp === null ? Minus : pnlUp ? TrendingUp : TrendingDown
                                    const days = trade.exit_date && trade.entry_date ? Math.round((new Date(trade.exit_date).getTime() - new Date(trade.entry_date).getTime()) / 86400000) : null
                                    return (
                                        <motion.tr key={trade.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 + i * 0.03, duration: 0.3 }} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                                            <td className="py-3.5 pr-6 pl-4">
                                                <div className="flex flex-col gap-0.5">
                                                    <span className="font-bold text-primary tracking-tight">{trade.security.ticker}</span>
                                                    <span className="text-[10px] text-muted">{trade.security.sector ?? ""}</span>
                                                </div>
                                            </td>
                                            <td className="py-3.5 pr-6 text-secondary font-mono text-xs">{trade.entry_date}</td>
                                            <td className="py-3.5 pr-6 text-secondary font-mono text-xs">{trade.exit_date ?? "—"}</td>
                                            <td className="py-3.5 pr-6 font-mono text-primary">₹{trade.fill_price?.toFixed(2) ?? "—"}</td>
                                            <td className="py-3.5 pr-6 font-mono text-primary">{trade.exit_price ? `₹${trade.exit_price.toFixed(2)}` : "—"}</td>
                                            <td className={`py-3.5 pr-6 font-mono font-semibold ${pctColor(trade.pnl)}`}>{formatINR(trade.pnl)}</td>
                                            <td className={`py-3.5 pr-6 font-mono font-semibold ${pctColor(trade.pnl_pct)}`}>
                                                <div className="flex items-center gap-1">
                                                    <PnlIcon size={11} strokeWidth={2.5} />
                                                    {trade.pnl_pct !== null ? `${trade.pnl_pct > 0 ? "+" : ""}${trade.pnl_pct.toFixed(2)}%` : "—"}
                                                </div>
                                            </td>
                                            <td className="py-3.5 pr-6 text-secondary font-mono text-xs">{days !== null ? `${days}d` : "—"}</td>
                                            <td className="py-3.5 pr-4"><Badge label={trade.exit_reason?.toUpperCase() ?? "—"} variant="muted" /></td>
                                        </motion.tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    )}
                </Card>
            </motion.div>
        </div>
    )
}
