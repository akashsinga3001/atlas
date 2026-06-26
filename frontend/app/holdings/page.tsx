"use client"

import { useTrades } from "@/libraries/hooks/useTrades"
import Skeleton from "@/components/ui/Skeleton"
import { motion } from "framer-motion"
import { TrendingUp, TrendingDown, Minus, Clock } from "lucide-react"
import { Trade } from "@/libraries/types/trade"

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

function formatINR(value: number | null | undefined, compact = false) {
    if (value === null || value === undefined) return "—"
    const abs = Math.abs(value)
    const sign = value < 0 ? "-" : value > 0 ? "+" : ""
    if (compact) {
        if (abs >= 100000) return `${sign}₹${(abs / 100000).toFixed(2)}L`
        if (abs >= 1000) return `${sign}₹${(abs / 1000).toFixed(1)}K`
        return `${sign}₹${abs.toFixed(0)}`
    }
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value)
}

function daysUntil(dateStr: string) {
    const diff = new Date(dateStr).getTime() - Date.now()
    return Math.ceil(diff / 86400000)
}

function PositionCard({ trade, index }: { trade: Trade; index: number }) {
    const pnlUp = trade.pnl !== null ? trade.pnl > 0 : null
    const pnlColor = pnlUp === null ? "text-secondary" : pnlUp ? "text-green-400" : "text-red-400"
    const pnlBg = pnlUp === null ? "" : pnlUp ? "bg-green-400/5 border-green-400/10" : "bg-red-400/5 border-red-400/10"
    const PnlIcon = pnlUp === null ? Minus : pnlUp ? TrendingUp : TrendingDown
    const daysLeft = trade.timeout_date ? daysUntil(trade.timeout_date) : null
    const timeoutUrgent = daysLeft !== null && daysLeft <= 5

    return (
        <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.06, duration: 0.4, ease }}>
            <div className={`flex flex-col gap-4 p-5 rounded-2xl border ${pnlBg || "bg-surface2 border-white/4"} hover:border-white/10 transition-colors`}>
                {/* Header row */}
                <div className="flex items-start justify-between gap-4">
                    <div className="flex flex-col gap-0.5">
                        <span className="text-lg font-bold text-primary tracking-tight leading-none">{trade.security.ticker}</span>
                        <span className="text-[11px] text-muted">
                            {trade.security.sector ?? ""}
                            {trade.security.industry ? ` · ${trade.security.industry}` : ""}
                        </span>
                    </div>
                    <div className="flex flex-col items-end gap-0.5">
                        <div className={`flex items-center gap-1.5 text-2xl font-bold font-mono ${pnlColor}`}>
                            <PnlIcon size={18} strokeWidth={2.5} />
                            {trade.pnl_pct !== null ? `${trade.pnl_pct > 0 ? "+" : ""}${trade.pnl_pct.toFixed(2)}%` : "—"}
                        </div>
                        <span className={`text-sm font-mono font-semibold ${pnlColor}`}>{formatINR(trade.pnl, true)}</span>
                    </div>
                </div>

                {/* Divider */}
                <div style={{ borderTop: "1px solid rgba(255,255,255,0.05)" }} />

                {/* Stats row */}
                <div className="grid grid-cols-3 gap-4">
                    <div className="flex flex-col gap-1">
                        <span className="text-[10px] uppercase tracking-[0.12em] text-secondary">Entry Price</span>
                        <span className="text-sm font-mono font-semibold text-primary">₹{trade.fill_price?.toFixed(2) ?? "—"}</span>
                    </div>
                    <div className="flex flex-col gap-1">
                        <span className="text-[10px] uppercase tracking-[0.12em] text-secondary">Quantity</span>
                        <span className="text-sm font-mono font-semibold text-primary">{trade.fill_quantity ?? "—"}</span>
                    </div>
                    <div className="flex flex-col gap-1">
                        <span className="text-[10px] uppercase tracking-[0.12em] text-secondary">Invested</span>
                        <span className="text-sm font-mono font-semibold text-primary">{formatINR(trade.invested_value, true)}</span>
                    </div>
                </div>

                {/* Footer */}
                <div className="flex items-center justify-between">
                    <span className="text-[10px] text-muted font-mono">Entered {trade.entry_date}</span>
                    <div className={`flex items-center gap-1.5 text-[10px] font-mono ${timeoutUrgent ? "text-amber-400" : "text-muted"}`}>
                        <Clock size={10} />
                        {daysLeft !== null ? `${daysLeft}d left · ${trade.timeout_date}` : trade.timeout_date}
                    </div>
                </div>
            </div>
        </motion.div>
    )
}

export default function HoldingsPage() {
    const { data: trades, isLoading } = useTrades("open")

    const totalInvested = trades?.reduce((s, t) => s + (t.invested_value ?? 0), 0) ?? 0
    const totalPnl = trades?.reduce((s, t) => s + (t.pnl ?? 0), 0) ?? 0
    const count = trades?.length ?? 0
    const winners = trades?.filter((t) => (t.pnl ?? 0) > 0).length ?? 0

    return (
        <div className="flex flex-col gap-6">
            {/* Hero */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between">
                <div>
                    <p className="text-[10px] uppercase tracking-[0.2em] text-secondary mb-1">Positions</p>
                    <h1 className="text-4xl font-bold tracking-tight text-primary leading-none">Holdings</h1>
                </div>
                <div className="flex flex-col items-end gap-1">
                    <span className="text-[10px] uppercase tracking-[0.15em] text-secondary">Unrealised P&amp;L</span>
                    {isLoading ? <Skeleton className="h-12 w-36" /> : <span className={`text-5xl font-bold font-mono leading-none ${totalPnl >= 0 ? "text-green-400" : "text-red-400"}`}>{formatINR(totalPnl, true)}</span>}
                </div>
            </motion.div>

            {/* Stat strip */}
            <div className="grid grid-cols-4 gap-3">
                {[
                    { label: "Open Positions", value: isLoading ? "—" : String(count) },
                    { label: "Total Invested", value: isLoading ? "—" : formatINR(totalInvested, true) },
                    { label: "In Profit", value: isLoading ? "—" : String(winners), sub: count > 0 ? `${count - winners} at loss` : undefined },
                    { label: "Avg Return", value: isLoading ? "—" : count > 0 ? `${((trades?.reduce((s, t) => s + (t.pnl_pct ?? 0), 0) ?? 0) / count).toFixed(2)}%` : "—" }
                ].map(({ label, value, sub }, i) => (
                    <motion.div key={label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07, duration: 0.4, ease }}>
                        <div className="flex flex-col gap-1.5 px-5 py-4 rounded-xl bg-surface2 border border-white/4">
                            <span className="text-[10px] uppercase tracking-[0.15em] text-secondary font-medium">{label}</span>
                            <span className="text-2xl font-bold text-primary font-mono leading-none">{value}</span>
                            {sub && <span className="text-[10px] text-muted">{sub}</span>}
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Position cards */}
            {isLoading && (
                <div className="grid grid-cols-2 gap-3">
                    {[...Array(4)].map((_, i) => (
                        <Skeleton key={i} className="h-48 rounded-2xl" />
                    ))}
                </div>
            )}
            {!isLoading && (!trades || trades.length === 0) && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>
                    <div className="py-20 text-center rounded-2xl bg-surface2 border border-white/4">
                        <TrendingUp size={32} className="text-muted mx-auto mb-4" strokeWidth={1.5} />
                        <p className="text-sm font-medium text-primary mb-1">No open positions</p>
                        <p className="text-xs text-secondary">Trades will appear here once entered</p>
                    </div>
                </motion.div>
            )}
            {!isLoading && trades && trades.length > 0 && (
                <div className="grid grid-cols-2 gap-3">
                    {trades.map((trade, i) => (
                        <PositionCard key={trade.id} trade={trade} index={i} />
                    ))}
                </div>
            )}
        </div>
    )
}
