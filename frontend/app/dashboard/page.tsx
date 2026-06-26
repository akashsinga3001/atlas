"use client"

import { useTrades } from "@/libraries/hooks/useTrades"
import { usePortfolioStats, useEquityCurve } from "@/libraries/hooks/usePortfolio"
import { useSignals } from "@/libraries/hooks/useSignals"
import Card from "@/components/ui/Card"
import MiniRing from "@/components/ui/MiniRing"
import Skeleton from "@/components/ui/Skeleton"
import Badge from "@/components/ui/Badge"
import { motion } from "framer-motion"
import { TrendingUp, TrendingDown, Clock, Minus } from "lucide-react"
import { Trade } from "@/libraries/types/trade"
import { Signal } from "@/libraries/types/signal"
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer } from "recharts"

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
    return `${sign}₹${abs.toLocaleString("en-IN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`
}

function PositionRow({ trade, index }: { trade: Trade; index: number }) {
    const pnlUp = trade.pnl !== null ? trade.pnl > 0 : null
    const pnlColor = pnlUp === null ? "text-secondary" : pnlUp ? "text-green-400" : "text-red-400"
    const PnlIcon = pnlUp === null ? Minus : pnlUp ? TrendingUp : TrendingDown

    return (
        <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.05, duration: 0.35, ease }}>
            <div className="flex items-center justify-between py-3 px-4 rounded-xl bg-surface2 border border-white/4 hover:border-white/8 transition-colors">
                <div className="flex flex-col gap-0.5 min-w-0">
                    <span className="text-sm font-bold text-primary tracking-tight">{trade.security.ticker}</span>
                    <span className="text-xs text-muted font-mono">
                        ₹{trade.fill_price?.toFixed(2) ?? "—"} · {trade.fill_quantity ?? "—"} qty
                    </span>
                </div>
                <div className="flex flex-col items-end gap-0.5 shrink-0">
                    <div className={`flex items-center gap-1 text-sm font-bold font-mono ${pnlColor}`}>
                        <PnlIcon size={12} strokeWidth={2.5} />
                        {trade.pnl_pct !== null ? `${trade.pnl_pct > 0 ? "+" : ""}${trade.pnl_pct.toFixed(2)}%` : "—"}
                    </div>
                    <div className="flex items-center gap-1 text-[10px] text-muted">
                        <Clock size={9} />
                        <span className="font-mono">{trade.timeout_date}</span>
                    </div>
                </div>
            </div>
        </motion.div>
    )
}

function SignalRow({ signal, index }: { signal: Signal; index: number }) {
    const entered = signal.signal_status === "entered"
    return (
        <motion.div initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.05, duration: 0.35, ease }}>
            <div className="flex items-center justify-between py-3 px-4 rounded-xl bg-surface2 border border-white/4 hover:border-white/8 transition-colors">
                <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-bold text-primary tracking-tight">{signal.security.ticker}</span>
                    <span className="text-xs text-muted font-mono">{signal.observed_at.slice(11, 16)}</span>
                </div>
                <div className="flex flex-col items-end gap-1">
                    <Badge label={signal.signal_status.toUpperCase()} variant={entered ? "green" : "muted"} />
                    {entered && signal.trade_fill_price && <span className="text-[10px] text-secondary font-mono">₹{signal.trade_fill_price.toFixed(2)}</span>}
                </div>
            </div>
        </motion.div>
    )
}

function StatCard({ label, value, sub, ring, ringMax, ringColor, index }: { label: string; value: string; sub?: string; ring?: number; ringMax?: number; ringColor?: string; index: number }) {
    return (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.08, duration: 0.4, ease }}>
            <div className="flex items-center justify-between px-5 py-4 rounded-xl bg-surface2 border border-white/4">
                <div className="flex flex-col gap-1">
                    <span className="text-[10px] uppercase tracking-[0.15em] text-secondary font-medium">{label}</span>
                    <span className="text-2xl font-bold text-primary font-mono leading-none">{value}</span>
                    {sub && <span className="text-[10px] text-muted">{sub}</span>}
                </div>
                {ring !== undefined && <MiniRing value={ring} max={ringMax ?? 100} size={44} strokeWidth={3.5} color={ringColor ?? "var(--color-accent)"} label={`${Math.round(ring)}%`} />}
            </div>
        </motion.div>
    )
}

const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    const pnl = payload[0]?.value
    const isPos = pnl >= 0
    return (
        <div className="card-base px-3 py-2 text-xs">
            <div className="text-secondary mb-1 font-mono">{label}</div>
            <div className={`font-bold font-mono ${isPos ? "text-green-400" : "text-red-400"}`}>{formatINR(pnl, true)}</div>
        </div>
    )
}

export default function DashboardPage() {
    const { data: trades, isLoading: tradesLoading } = useTrades("open")
    const { data: stats, isLoading: statsLoading } = usePortfolioStats()
    const { data: curve, isLoading: curveLoading } = useEquityCurve()
    const { data: signals, isLoading: signalsLoading } = useSignals()

    const todayStr = new Date().toISOString().slice(0, 10)
    const todaySignals = signals?.filter((s) => s.observed_at.slice(0, 10) === todayStr) ?? []

    const pnlColor = stats?.total_pnl !== null && stats?.total_pnl !== undefined ? (stats.total_pnl >= 0 ? "text-green-400" : "text-red-400") : "text-accent"

    const chartColor = stats?.total_pnl !== null && stats?.total_pnl !== undefined && stats.total_pnl < 0 ? "#f87171" : "#4ade80"

    return (
        <div className="flex flex-col gap-6 h-full">
            {/* Hero bar */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between">
                <div>
                    <p className="text-[10px] uppercase tracking-[0.2em] text-secondary mb-1">Mission Control</p>
                    <h1 className="text-4xl font-bold tracking-tight text-primary leading-none">Dashboard</h1>
                </div>
                <div className="flex flex-col items-end gap-1">
                    <span className="text-[10px] uppercase tracking-[0.15em] text-secondary">Total P&amp;L</span>
                    {statsLoading ? <Skeleton className="h-10 w-32" /> : <span className={`text-5xl font-bold font-mono leading-none ${pnlColor}`}>{formatINR(stats?.total_pnl ?? null, true)}</span>}
                </div>
            </motion.div>

            {/* Main grid: left stats column + right chart */}
            <div className="grid gap-4" style={{ gridTemplateColumns: "240px 1fr" }}>
                {/* Left: stat cards stacked */}
                <div className="flex flex-col gap-3">
                    {statsLoading ? (
                        [...Array(4)].map((_, i) => <Skeleton key={i} className="h-20 rounded-xl" />)
                    ) : (
                        <>
                            <StatCard index={0} label="Open Positions" value={String(stats?.open_trades ?? 0)} sub={`of ${stats?.total_trades ?? 0} total`} ring={stats?.total_trades ? (stats.open_trades / stats.total_trades) * 100 : 0} ringMax={100} ringColor="var(--color-accent)" />
                            <StatCard index={1} label="Win Rate" value={stats?.win_rate !== null && stats?.win_rate !== undefined ? `${stats.win_rate}%` : "—"} sub={`${stats?.closed_trades ?? 0} closed trades`} ring={stats?.win_rate ?? 0} ringMax={100} ringColor="#4ade80" />
                            <StatCard index={2} label="Avg Hold" value={stats?.avg_holding_days !== null && stats?.avg_holding_days !== undefined ? `${stats.avg_holding_days}d` : "—"} sub="per trade" />
                            <StatCard index={3} label="Avg Win" value={stats?.avg_win_pct !== null && stats?.avg_win_pct !== undefined ? `+${stats.avg_win_pct.toFixed(2)}%` : "—"} sub={`Avg Loss: ${stats?.avg_loss_pct !== null && stats?.avg_loss_pct !== undefined ? `${stats.avg_loss_pct.toFixed(2)}%` : "—"}`} />
                        </>
                    )}
                </div>

                {/* Right: equity curve */}
                <Card padding="md" className="flex flex-col gap-3">
                    <div className="flex items-center justify-between">
                        <span className="text-[10px] uppercase tracking-[0.15em] text-secondary font-medium">Equity Curve</span>
                        {!curveLoading && curve && <span className="text-[10px] text-muted font-mono">{curve.length} trades</span>}
                    </div>
                    {curveLoading && <Skeleton className="flex-1 rounded-lg" />}
                    {!curveLoading && (!curve || curve.length === 0) && (
                        <div className="flex-1 flex items-center justify-center">
                            <span className="text-sm text-secondary">No closed trades yet</span>
                        </div>
                    )}
                    {!curveLoading && curve && curve.length > 0 && (
                        <div className="flex-1 min-h-0" style={{ height: 220 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={curve} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
                                    <defs>
                                        <linearGradient id="curveGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor={chartColor} stopOpacity={0.2} />
                                            <stop offset="100%" stopColor={chartColor} stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} tickFormatter={(v) => v?.slice(5)} />
                                    <YAxis tick={{ fontSize: 10, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} tickFormatter={(v) => formatINR(v, true)} width={60} />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Area type="monotone" dataKey="cumulative_pnl" stroke={chartColor} strokeWidth={2} fill="url(#curveGrad)" dot={false} />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </Card>
            </div>

            {/* Bottom: positions + signals */}
            <div className="grid grid-cols-2 gap-4">
                {/* Open Positions */}
                <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between px-1">
                        <span className="text-[10px] uppercase tracking-[0.15em] text-secondary font-medium">Open Positions</span>
                        {!tradesLoading && <span className="text-[10px] text-muted font-mono">{trades?.length ?? 0} active</span>}
                    </div>
                    {tradesLoading && [...Array(2)].map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
                    {!tradesLoading && (!trades || trades.length === 0) && <div className="py-6 text-center text-sm text-secondary bg-surface2 rounded-xl border border-white/4">No open positions</div>}
                    {trades?.map((t, i) => (
                        <PositionRow key={t.id} trade={t} index={i} />
                    ))}
                </div>

                {/* Today's Signals */}
                <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between px-1">
                        <span className="text-[10px] uppercase tracking-[0.15em] text-secondary font-medium">Today&apos;s Signals</span>
                        {!signalsLoading && <span className="text-[10px] text-muted font-mono">{todaySignals.length} signals</span>}
                    </div>
                    {signalsLoading && [...Array(2)].map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
                    {!signalsLoading && todaySignals.length === 0 && <div className="py-6 text-center text-sm text-secondary bg-surface2 rounded-xl border border-white/4">No signals today</div>}
                    {todaySignals.map((s, i) => (
                        <SignalRow key={s.id} signal={s} index={i} />
                    ))}
                </div>
            </div>
        </div>
    )
}
