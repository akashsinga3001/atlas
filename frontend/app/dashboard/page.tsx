"use client"

import { useTrades } from "@/libraries/hooks/useTrades"
import { usePortfolioStats, useEquityCurve } from "@/libraries/hooks/usePortfolio"
import { useSignals } from "@/libraries/hooks/useSignals"
import Card from "@/components/ui/Card"
import MiniRing from "@/components/ui/MiniRing"
import Skeleton from "@/components/ui/Skeleton"
import Badge from "@/components/ui/Badge"
import { motion } from "framer-motion"
import { TrendingUp, TrendingDown, Minus, Clock, AlertTriangle } from "lucide-react"
import { Trade } from "@/libraries/types/trade"
import { Signal } from "@/libraries/types/signal"
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

function daysUntil(dateStr: string) {
    return Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86400000)
}

function computeStreak(curve: { pnl: number }[]) {
    if (!curve || curve.length === 0) return { count: 0, type: null as "win" | "loss" | null }
    const type = curve[curve.length - 1].pnl >= 0 ? "win" : "loss"
    let count = 0
    for (let i = curve.length - 1; i >= 0; i--) {
        if ((type === "win" && curve[i].pnl >= 0) || (type === "loss" && curve[i].pnl < 0)) count++
        else break
    }
    return { count, type }
}

// ── Stat strip ─────────────────────────────────────────────────────────────

function StatStrip({ stats, openTrades, curve, isLoading }: { stats: any; openTrades: Trade[] | undefined; curve: any[] | undefined; isLoading: boolean }) {
    const deployed = openTrades?.reduce((s, t) => s + (t.invested_value ?? 0), 0) ?? 0
    const streak = curve ? computeStreak(curve) : { count: 0, type: null }

    const items = [
        { label: "Open Positions", value: isLoading ? "—" : String(stats?.open_trades ?? 0), ring: stats?.open_trades && stats?.total_trades ? (stats.open_trades / stats.total_trades) * 100 : 0, ringColor: "var(--color-accent)" },
        { label: "Capital Deployed", value: isLoading ? "—" : formatINR(deployed, true) },
        { label: "Win Rate", value: isLoading ? "—" : stats?.win_rate != null ? `${stats.win_rate}%` : "—", ring: stats?.win_rate ?? 0, ringColor: "#4ade80" },
        { label: "Closed Trades", value: isLoading ? "—" : String(stats?.closed_trades ?? 0) },
        { label: "Avg Hold", value: isLoading ? "—" : stats?.avg_holding_days != null ? `${stats.avg_holding_days}d` : "—" },
        { label: "Streak", value: isLoading ? "—" : streak.count > 0 ? `${streak.count} ${streak.type === "win" ? "W" : "L"}` : "—", streakType: streak.type }
    ]

    return (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.4, ease }}>
            <div className="flex items-center rounded-2xl overflow-hidden" style={{ background: "var(--color-surface)", border: "1px solid rgba(255,255,255,0.05)" }}>
                {items.map(({ label, value, ring, ringColor, streakType }, i) => (
                    <div key={label} className="flex-1 flex items-center justify-between px-5 py-4" style={{ borderRight: i < items.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none" }}>
                        <div className="flex flex-col gap-1">
                            <span className="text-[10px] uppercase tracking-[0.12em] font-medium text-secondary">{label}</span>
                            <span className={`text-xl font-bold font-mono leading-none ${streakType === "win" ? "text-green-400" : streakType === "loss" ? "text-red-400" : "text-primary"}`}>{value}</span>
                        </div>
                        {ring !== undefined && ring > 0 && <MiniRing value={ring} max={100} size={34} strokeWidth={3} color={ringColor} label="" />}
                    </div>
                ))}
            </div>
        </motion.div>
    )
}

// ── Right sidebar widgets ──────────────────────────────────────────────────

function ExpiringSoon({ trades }: { trades: Trade[] | undefined }) {
    const expiring = (trades ?? [])
        .filter((t) => t.timeout_date)
        .map((t) => ({ ...t, daysLeft: daysUntil(t.timeout_date) }))
        .filter((t) => t.daysLeft <= 7)
        .sort((a, b) => a.daysLeft - b.daysLeft)

    return (
        <div className="flex flex-col gap-3 px-4 py-4 rounded-xl bg-surface2 border border-white/4">
            <div className="flex items-center gap-1.5">
                <AlertTriangle size={11} className="text-amber-400" strokeWidth={2} />
                <span className="text-[10px] uppercase tracking-[0.12em] font-medium text-secondary">Expiring Soon</span>
            </div>
            {expiring.length === 0 ? (
                <p className="text-xs text-muted">No positions expiring this week</p>
            ) : (
                <div className="flex flex-col gap-2">
                    {expiring.map((t) => (
                        <div key={t.id} className="flex items-center justify-between">
                            <span className="text-sm font-bold text-primary">{t.security.ticker}</span>
                            <div className={`flex items-center gap-1.5 text-xs font-mono font-bold ${t.daysLeft <= 2 ? "text-red-400" : t.daysLeft <= 5 ? "text-amber-400" : "text-secondary"}`}>
                                <Clock size={10} />
                                {t.daysLeft}d
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}

function SectorExposure({ trades }: { trades: Trade[] | undefined }) {
    const sectors: Record<string, number> = {}
    ;(trades ?? []).forEach((t) => {
        const s = t.security.sector ?? "Other"
        sectors[s] = (sectors[s] || 0) + (t.invested_value ?? 0)
    })
    const entries = Object.entries(sectors)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 5)
    const max = Math.max(...entries.map((e) => e[1]), 1)

    return (
        <div className="flex flex-col gap-3 px-4 py-4 rounded-xl bg-surface2 border border-white/4">
            <span className="text-[10px] uppercase tracking-[0.12em] font-medium text-secondary">Sector Exposure</span>
            {entries.length === 0 ? (
                <p className="text-xs text-muted">No open positions</p>
            ) : (
                <div className="flex flex-col gap-3">
                    {entries.map(([sector, value]) => (
                        <div key={sector} className="flex flex-col gap-1.5">
                            <div className="flex items-center justify-between">
                                <span className="text-xs text-secondary truncate pr-3">{sector}</span>
                                <span className="text-[10px] font-mono text-muted shrink-0">{formatINR(value, true)}</span>
                            </div>
                            <div className="h-0.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                                <div className="h-0.5 rounded-full" style={{ width: `${(value / max) * 100}%`, background: "var(--color-accent)", opacity: 0.6 }} />
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}

function RecentExits({ trades, isLoading }: { trades: Trade[] | undefined; isLoading: boolean }) {
    const recent = (trades ?? []).slice(0, 5)
    return (
        <div className="flex flex-col flex-1 gap-3 px-4 py-4 rounded-xl bg-surface2 border border-white/4">
            <span className="text-[10px] uppercase tracking-[0.12em] font-medium text-secondary">Recent Exits</span>
            {isLoading && (
                <div className="flex flex-col gap-2">
                    {[...Array(3)].map((_, i) => (
                        <Skeleton key={i} className="h-7 rounded-lg" />
                    ))}
                </div>
            )}
            {!isLoading && recent.length === 0 && <p className="text-xs text-muted text-center flex flex-1 flex-col justify-center">No closed trades yet</p>}
            {!isLoading && recent.length > 0 && (
                <div className="flex flex-col gap-2">
                    {recent.map((t) => {
                        const up = t.pnl_pct != null ? t.pnl_pct >= 0 : null
                        return (
                            <div key={t.id} className="flex items-center justify-between gap-3">
                                <div className="min-w-0">
                                    <span className="text-sm font-bold text-primary">{t.security.ticker}</span>
                                    {t.exit_reason && <span className="text-[10px] ml-2 text-muted">{t.exit_reason}</span>}
                                </div>
                                <span className={`text-sm font-mono font-bold shrink-0 ${up === null ? "text-secondary" : up ? "text-green-400" : "text-red-400"}`}>{t.pnl_pct != null ? `${t.pnl_pct > 0 ? "+" : ""}${t.pnl_pct.toFixed(1)}%` : "—"}</span>
                            </div>
                        )
                    })}
                </div>
            )}
        </div>
    )
}

// ── Chart tooltip ──────────────────────────────────────────────────────────

const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null
    const pnl = payload[0]?.value
    return (
        <div className="rounded-xl px-3 py-2 text-xs" style={{ background: "#161616", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="font-mono mb-1 text-secondary">{label}</div>
            <div className={`font-bold font-mono ${pnl >= 0 ? "text-green-400" : "text-red-400"}`}>{formatINR(pnl, true)}</div>
        </div>
    )
}

// ── Bottom rows ────────────────────────────────────────────────────────────

function PositionRow({ trade, index }: { trade: Trade; index: number }) {
    const pnlUp = trade.pnl !== null ? trade.pnl > 0 : null
    const pnlColor = pnlUp === null ? "text-secondary" : pnlUp ? "text-green-400" : "text-red-400"
    const PnlIcon = pnlUp === null ? Minus : pnlUp ? TrendingUp : TrendingDown

    return (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05, duration: 0.3, ease }}>
            <div className="flex items-center justify-between py-3 px-4 rounded-xl bg-surface2 border border-white/4 hover:border-white/8 transition-colors">
                <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-bold text-primary">{trade.security.ticker}</span>
                    <span className="text-[10px] font-mono text-muted">
                        ₹{trade.fill_price?.toFixed(2) ?? "—"} · {trade.fill_quantity ?? "—"} qty
                    </span>
                </div>
                <div className="flex flex-col items-end gap-0.5">
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
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05, duration: 0.3, ease }}>
            <div className="flex items-center justify-between py-3 px-4 rounded-xl bg-surface2 border border-white/4">
                <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-bold text-primary">{signal.security.ticker}</span>
                    <span className="text-[10px] font-mono text-muted">{signal.observed_at.slice(11, 16)}</span>
                </div>
                <div className="flex flex-col items-end gap-1.5">
                    <Badge label={signal.signal_status.toUpperCase()} variant={entered ? "green" : "muted"} />
                    {entered && signal.trade_fill_price && <span className="text-[10px] font-mono text-secondary">₹{signal.trade_fill_price.toFixed(2)}</span>}
                </div>
            </div>
        </motion.div>
    )
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function DashboardPage() {
    const { data: openTrades, isLoading: openLoading } = useTrades("open")
    const { data: closedTrades, isLoading: closedLoading } = useTrades("closed")
    const { data: stats, isLoading: statsLoading } = usePortfolioStats()
    const { data: curve, isLoading: curveLoading } = useEquityCurve()
    const { data: signals, isLoading: signalsLoading } = useSignals()

    const todayStr = new Date().toISOString().slice(0, 10)
    const todaySignals = signals?.filter((s) => s.observed_at.slice(0, 10) === todayStr) ?? []

    const pnlPositive = !stats?.total_pnl || stats.total_pnl >= 0
    const chartColor = pnlPositive ? "#4ade80" : "#f87171"
    const pnlColor = stats?.total_pnl != null ? (stats.total_pnl >= 0 ? "text-green-400" : "text-red-400") : "text-secondary"

    return (
        <div className="flex flex-col gap-5">
            {/* Hero */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between">
                <div>
                    <p className="text-[10px] uppercase tracking-[0.2em] text-secondary mb-1">Mission Control</p>
                    <h1 className="text-4xl font-bold tracking-tight text-primary leading-none">Dashboard</h1>
                </div>
                <div className="flex flex-col items-end gap-1">
                    <span className="text-[10px] uppercase tracking-[0.15em] text-secondary">Total P&amp;L</span>
                    {statsLoading ? <Skeleton className="h-12 w-36" /> : <span className={`text-5xl font-bold font-mono leading-none ${pnlColor}`}>{formatINR(stats?.total_pnl, true)}</span>}
                </div>
            </motion.div>

            {/* Stat strip */}
            <StatStrip stats={stats} openTrades={openTrades} curve={curve} isLoading={statsLoading || openLoading || curveLoading} />

            {/* 2-column: equity curve + right sidebar */}
            <div className="grid gap-4" style={{ gridTemplateColumns: "1fr 300px" }}>
                {/* Equity curve */}
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2, duration: 0.5 }}>
                    <Card padding="md" className="flex flex-col gap-4 h-full">
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] uppercase tracking-[0.15em] font-medium text-secondary">Equity Curve</span>
                            {!curveLoading && curve && <span className="text-[10px] font-mono text-muted">{curve.length} trades</span>}
                        </div>
                        {curveLoading && <Skeleton className="flex-1 rounded-lg" style={{ minHeight: 280 }} />}
                        {!curveLoading && (!curve || curve.length === 0) && (
                            <div className="flex-1 flex items-center justify-center" style={{ minHeight: 280 }}>
                                <p className="text-sm text-secondary">No closed trades yet</p>
                            </div>
                        )}
                        {!curveLoading && curve && curve.length > 0 && (
                            <div className="flex-1" style={{ minHeight: 280 }}>
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
                                        <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                                        <Tooltip content={<CustomTooltip />} />
                                        <Area type="monotone" dataKey="cumulative_pnl" stroke={chartColor} strokeWidth={2} fill="url(#curveGrad)" dot={false} />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        )}
                    </Card>
                </motion.div>

                {/* Right sidebar */}
                <motion.div initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.25, duration: 0.4, ease }} className="flex flex-col gap-3">
                    <ExpiringSoon trades={openTrades} />
                    <SectorExposure trades={openTrades} />
                    <RecentExits trades={closedTrades} isLoading={closedLoading} />
                </motion.div>
            </div>

            {/* Bottom: open positions + today's signals */}
            <div className="grid grid-cols-2 gap-4">
                <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between px-1">
                        <span className="text-[10px] uppercase tracking-[0.15em] font-medium text-secondary">Open Positions</span>
                        {!openLoading && <span className="text-[10px] font-mono text-muted">{openTrades?.length ?? 0} active</span>}
                    </div>
                    {openLoading && [...Array(2)].map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
                    {!openLoading && (!openTrades || openTrades.length === 0) && <div className="py-8 text-center text-sm text-secondary rounded-xl bg-surface2 border border-white/4">No open positions</div>}
                    {openTrades?.map((t, i) => (
                        <PositionRow key={t.id} trade={t} index={i} />
                    ))}
                </div>

                <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between px-1">
                        <span className="text-[10px] uppercase tracking-[0.15em] font-medium text-secondary">Today&apos;s Signals</span>
                        {!signalsLoading && <span className="text-[10px] font-mono text-muted">{todaySignals.length} signals</span>}
                    </div>
                    {signalsLoading && [...Array(2)].map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
                    {!signalsLoading && todaySignals.length === 0 && <div className="py-8 text-center text-sm text-secondary rounded-xl bg-surface2 border border-white/4">No signals today</div>}
                    {todaySignals.map((s, i) => (
                        <SignalRow key={s.id} signal={s} index={i} />
                    ))}
                </div>
            </div>
        </div>
    )
}
