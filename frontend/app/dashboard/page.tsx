"use client"

import { useTrades } from "@/libraries/hooks/useTrades"
import { usePortfolioStats, useEquityCurve, usePortfolioAnalytics } from "@/libraries/hooks/usePortfolio"
import { useSignals } from "@/libraries/hooks/useSignals"
import { useLivePnL } from "@/libraries/hooks/useLivePnL"
import { usePriceFlash } from "@/libraries/hooks/usePriceFlash"
import { useCountUp } from "@/libraries/hooks/useCountUp"
import Card from "@/components/ui/Card"
import MiniRing from "@/components/ui/MiniRing"
import Skeleton from "@/components/ui/Skeleton"
import Badge from "@/components/ui/Badge"
import { motion } from "framer-motion"
import { TrendingUp, TrendingDown, Minus, Clock, AlertTriangle } from "lucide-react"
import { Trade } from "@/libraries/types/trade"
import { Signal } from "@/libraries/types/signal"
import { AreaChart, Area, BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, LabelList } from "recharts"
import { useMemo } from "react"
import { formatINR, FY_START } from "@/libraries/utils/format"
import { PortfolioStats, PortfolioAnalytics } from "@/libraries/types/portfolio"

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

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

function StatStrip({ stats, openTrades, curve, isLoading }: { stats: PortfolioStats | undefined; openTrades: Trade[] | undefined; curve: { pnl: number }[] | undefined; isLoading: boolean }) {
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

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) => {
    if (!active || !payload?.length) return null
    const pnl = payload[0]?.value ?? 0
    return (
        <div className="rounded-xl px-3 py-2 text-xs" style={{ background: "#161616", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="font-mono mb-1 text-secondary">{label}</div>
            <div className={`font-bold font-mono ${pnl >= 0 ? "text-green-400" : "text-red-400"}`}>{formatINR(pnl, true)}</div>
        </div>
    )
}

// ── FY Stats ───────────────────────────────────────────────────────────────

function FYStrip({ trades, isLoading }: { trades: Trade[] | undefined; isLoading: boolean }) {
    const fyStart = FY_START
    const fyTrades = useMemo(() => (trades ?? []).filter((t) => t.exit_date && t.exit_date >= fyStart), [trades, fyStart])
    const fyPnl = fyTrades.reduce((s, t) => s + (t.pnl ?? 0), 0)
    const fyWins = fyTrades.filter((t) => (t.pnl ?? 0) > 0).length
    const fyWinRate = fyTrades.length > 0 ? Math.round((fyWins / fyTrades.length) * 100) : null
    const fyAvg = fyTrades.length > 0 ? fyPnl / fyTrades.length : null
    const fyPnlColor = fyPnl >= 0 ? "text-green-400" : "text-red-400"

    const items = [
        { label: "FY P&L", value: isLoading ? "—" : formatINR(fyPnl, true), color: isLoading ? undefined : fyPnlColor },
        { label: "FY Trades", value: isLoading ? "—" : String(fyTrades.length) },
        { label: "FY Win Rate", value: isLoading ? "—" : fyWinRate !== null ? `${fyWinRate}%` : "—", color: fyWinRate !== null ? (fyWinRate >= 50 ? "text-green-400" : "text-red-400") : undefined },
        { label: "FY Avg / Trade", value: isLoading ? "—" : fyAvg !== null ? formatINR(fyAvg, true) : "—", color: fyAvg !== null ? (fyAvg >= 0 ? "text-green-400" : "text-red-400") : undefined }
    ]

    return (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15, duration: 0.4, ease }}>
            <div className="flex items-center rounded-2xl overflow-hidden" style={{ background: "var(--color-surface)", border: "1px solid rgba(255,255,255,0.05)" }}>
                <div className="flex items-center gap-1.5 px-5 py-3.5 shrink-0" style={{ borderRight: "1px solid rgba(255,255,255,0.05)" }}>
                    <span className="text-[9px] uppercase tracking-[0.18em] font-semibold" style={{ color: "var(--color-accent)", opacity: 0.7 }}>
                        FY
                    </span>
                </div>
                {items.map(({ label, value, color }, i) => (
                    <div key={label} className="flex-1 flex flex-col gap-0.5 px-5 py-3" style={{ borderRight: i < items.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none" }}>
                        <span className="text-[10px] uppercase tracking-[0.12em] font-medium text-secondary">{label}</span>
                        <span className={`text-lg font-bold font-mono leading-none ${color ?? "text-primary"}`}>{value}</span>
                    </div>
                ))}
            </div>
        </motion.div>
    )
}

// ── Monthly P&L bars ───────────────────────────────────────────────────────

function MonthlyBars({ trades, isLoading }: { trades: Trade[] | undefined; isLoading: boolean }) {
    const data = useMemo(() => {
        const map: Record<string, number> = {}
        for (const t of trades ?? []) {
            if (!t.exit_date || t.pnl === null) continue
            const key = t.exit_date.slice(0, 7) // "YYYY-MM"
            map[key] = (map[key] ?? 0) + t.pnl
        }
        // Last 12 months
        const result = []
        const now = new Date()
        for (let i = 11; i >= 0; i--) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
            const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`
            const label = d.toLocaleString("en", { month: "short" }).toUpperCase()
            result.push({ key, label, pnl: map[key] ?? null })
        }
        return result
    }, [trades])

    const hasAny = data.some((d) => d.pnl !== null)

    return (
        <Card padding="md" className="flex flex-col gap-3">
            <span className="text-[10px] uppercase tracking-[0.15em] font-medium text-secondary">Monthly P&amp;L</span>
            {isLoading && <Skeleton className="rounded-lg" style={{ height: 110 }} />}
            {!isLoading && !hasAny && (
                <div className="flex items-center justify-center" style={{ height: 110 }}>
                    <p className="text-xs text-secondary">No closed trades</p>
                </div>
            )}
            {!isLoading && hasAny && (
                <div style={{ height: 110 }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }} barCategoryGap="20%">
                            <XAxis dataKey="label" tick={{ fontSize: 9, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} />
                            <YAxis hide />
                            <Tooltip
                                cursor={{ fill: "rgba(255,255,255,0.03)" }}
                                content={({ active, payload }) => {
                                    if (!active || !payload?.length) return null
                                    const d = payload[0]?.payload
                                    return (
                                        <div className="rounded-lg px-2.5 py-2 text-xs" style={{ background: "#161616", border: "1px solid rgba(255,255,255,0.08)" }}>
                                            <div className="text-secondary font-mono mb-1">{d.key}</div>
                                            <div className={`font-bold font-mono ${(d.pnl ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>{formatINR(d.pnl, true)}</div>
                                        </div>
                                    )
                                }}
                            />
                            <ReferenceLine y={0} stroke="rgba(255,255,255,0.06)" />
                            <Bar dataKey="pnl" radius={[3, 3, 0, 0]}>
                                {data.map((d, i) => (
                                    <Cell key={i} fill={d.pnl === null ? "rgba(255,255,255,0.04)" : d.pnl >= 0 ? "rgba(74,222,128,0.55)" : "rgba(248,113,113,0.55)"} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}
        </Card>
    )
}

// ── Bottom rows ────────────────────────────────────────────────────────────

function PositionRow({ trade, index, livePrice }: { trade: Trade; index: number; livePrice?: number | null }) {
    const livePnlPct = livePrice && trade.fill_price ? ((livePrice - trade.fill_price) / trade.fill_price) * 100 : trade.pnl_pct
    const pnlUp = livePnlPct !== null ? livePnlPct > 0 : null
    const pnlColor = pnlUp === null ? "text-secondary" : pnlUp ? "text-green-400" : "text-red-400"
    const PnlIcon = pnlUp === null ? Minus : pnlUp ? TrendingUp : TrendingDown
    const flashClass = usePriceFlash(livePrice)

    return (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05, duration: 0.3, ease }}>
            <div className="group relative flex items-center justify-between py-3 px-4 rounded-xl bg-surface2 border border-white/4 hover:border-white/8 transition-colors">
                <span className="absolute left-0 inset-y-0 w-0.5 rounded-l-xl rounded-r-sm opacity-0 group-hover:opacity-100 transition-opacity duration-150" style={{ background: "var(--color-accent)" }} />
                <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-bold text-primary">{trade.security.ticker}</span>
                    <span className="text-[10px] font-mono text-muted">
                        ₹{trade.fill_price?.toFixed(2) ?? "—"} · {trade.fill_quantity ?? "—"} qty
                        {livePrice && <span className="text-accent ml-1.5">→ ₹{livePrice.toFixed(2)}</span>}
                    </span>
                </div>
                <div className="flex flex-col items-end gap-0.5">
                    <div className={`flex items-center gap-1 text-sm font-bold font-mono ${pnlColor} ${flashClass}`}>
                        <PnlIcon size={12} strokeWidth={2.5} />
                        {livePnlPct !== null ? `${livePnlPct > 0 ? "+" : ""}${livePnlPct.toFixed(2)}%` : "—"}
                    </div>
                    {(() => {
                        const stop = trade.state?.["current_stop"] as number | undefined
                        return stop ? <span className="text-[10px] font-mono text-red-400/70">stop ₹{stop.toFixed(2)}</span> : null
                    })()}
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

// ── Analytics strip ───────────────────────────────────────────────────

function AnalyticsStrip({ stats, isLoading }: { stats: PortfolioStats | undefined; isLoading: boolean }) {
    const items = [
        {
            label: "Sharpe Ratio",
            value: isLoading ? "—" : stats?.sharpe_ratio != null ? stats.sharpe_ratio.toFixed(2) : "—",
            color: stats?.sharpe_ratio != null ? (stats.sharpe_ratio >= 1 ? "text-green-400" : stats.sharpe_ratio >= 0 ? "text-amber-400" : "text-red-400") : undefined,
            hint: "Annualized, trade-level"
        },
        {
            label: "Max Drawdown",
            value: isLoading ? "—" : stats?.max_drawdown_pct != null ? `${stats.max_drawdown_pct.toFixed(1)}%` : "—",
            color: stats?.max_drawdown_pct != null ? (stats.max_drawdown_pct <= 10 ? "text-green-400" : stats.max_drawdown_pct <= 25 ? "text-amber-400" : "text-red-400") : undefined,
            hint: "Peak-to-trough P&L"
        },
        {
            label: "Profit Factor",
            value: isLoading ? "—" : stats?.profit_factor != null ? stats.profit_factor.toFixed(2) : "—",
            color: stats?.profit_factor != null ? (stats.profit_factor >= 2 ? "text-green-400" : stats.profit_factor >= 1 ? "text-amber-400" : "text-red-400") : undefined,
            hint: "Gross profit / gross loss"
        },
        {
            label: "Avg Win",
            value: isLoading ? "—" : stats?.avg_win_pct != null ? `+${stats.avg_win_pct.toFixed(2)}%` : "—",
            color: "text-green-400",
            hint: undefined
        },
        {
            label: "Avg Loss",
            value: isLoading ? "—" : stats?.avg_loss_pct != null ? `${stats.avg_loss_pct.toFixed(2)}%` : "—",
            color: "text-red-400",
            hint: undefined
        }
    ]

    return (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18, duration: 0.4, ease }}>
            <div className="flex items-center rounded-2xl overflow-hidden" style={{ background: "var(--color-surface)", border: "1px solid rgba(255,255,255,0.05)" }}>
                <div className="flex items-center gap-1.5 px-5 py-3.5 shrink-0" style={{ borderRight: "1px solid rgba(255,255,255,0.05)" }}>
                    <span className="text-[9px] uppercase tracking-[0.18em] font-semibold" style={{ color: "var(--color-accent)", opacity: 0.7 }}>
                        Analytics
                    </span>
                </div>
                {items.map(({ label, value, color, hint }, i) => (
                    <div key={label} className="flex-1 flex flex-col gap-0.5 px-5 py-3" style={{ borderRight: i < items.length - 1 ? "1px solid rgba(255,255,255,0.05)" : "none" }}>
                        <span className="text-[10px] uppercase tracking-[0.12em] font-medium text-secondary">{label}</span>
                        <span className={`text-lg font-bold font-mono leading-none ${color ?? "text-primary"}`}>{value}</span>
                        {hint && <span className="text-[9px] text-muted mt-0.5">{hint}</span>}
                    </div>
                ))}
            </div>
        </motion.div>
    )
}

// ── Return distribution ────────────────────────────────────────────────

function ReturnDistribution({ analytics, isLoading }: { analytics: PortfolioAnalytics | undefined; isLoading: boolean }) {
    const data = analytics?.return_distribution ?? []
    const hasAny = data.some((d) => d.count > 0)

    return (
        <Card padding="md" className="flex flex-col gap-3">
            <span className="text-[10px] uppercase tracking-[0.15em] font-medium text-secondary">Return Distribution</span>
            {isLoading && <Skeleton className="rounded-lg" style={{ height: 110 }} />}
            {!isLoading && !hasAny && (
                <div className="flex items-center justify-center" style={{ height: 110 }}>
                    <p className="text-xs text-secondary">No closed trades</p>
                </div>
            )}
            {!isLoading && hasAny && (
                <div style={{ height: 110 }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data} margin={{ top: 12, right: 4, bottom: 0, left: 0 }} barCategoryGap="15%">
                            <XAxis dataKey="bucket" tick={{ fontSize: 8, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} interval={0} />
                            <YAxis hide />
                            <Tooltip
                                cursor={{ fill: "rgba(255,255,255,0.03)" }}
                                content={({ active, payload }) => {
                                    if (!active || !payload?.length) return null
                                    const d = payload[0]?.payload
                                    return (
                                        <div className="rounded-lg px-2.5 py-2 text-xs" style={{ background: "#161616", border: "1px solid rgba(255,255,255,0.08)" }}>
                                            <div className="text-secondary font-mono mb-1">{d.bucket}</div>
                                            <div className="font-bold font-mono text-primary">
                                                {d.count} trade{d.count !== 1 ? "s" : ""}
                                            </div>
                                        </div>
                                    )
                                }}
                            />
                            <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                                <LabelList dataKey="count" position="top" style={{ fontSize: 9, fill: "var(--color-muted)" }} formatter={(v: unknown) => ((v as number) > 0 ? String(v) : "")} />
                                {data.map((d, i) => (
                                    <Cell key={i} fill={d.count === 0 ? "rgba(255,255,255,0.04)" : d.is_win ? "rgba(74,222,128,0.55)" : "rgba(248,113,113,0.55)"} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}
        </Card>
    )
}

// ── Sector performance ─────────────────────────────────────────────────

function SectorPerformance({ analytics, isLoading }: { analytics: PortfolioAnalytics | undefined; isLoading: boolean }) {
    const data = (analytics?.sector_performance ?? []).slice(0, 6)

    return (
        <Card padding="md" className="flex flex-col gap-3">
            <span className="text-[10px] uppercase tracking-[0.15em] font-medium text-secondary">Sector Performance</span>
            {isLoading && <Skeleton className="rounded-lg" style={{ height: 130 }} />}
            {!isLoading && data.length === 0 && (
                <div className="flex items-center justify-center" style={{ height: 130 }}>
                    <p className="text-xs text-secondary">No closed trades</p>
                </div>
            )}
            {!isLoading && data.length > 0 && (
                <div className="flex flex-col gap-2.5" style={{ minHeight: 130 }}>
                    {data.map((s) => {
                        const wr = s.win_rate ?? 0
                        const avgUp = s.avg_return != null && s.avg_return >= 0
                        return (
                            <div key={s.sector} className="flex flex-col gap-1">
                                <div className="flex items-center justify-between">
                                    <span className="text-xs text-secondary truncate pr-3">{s.sector}</span>
                                    <div className="flex items-center gap-3 shrink-0">
                                        <span className={`text-[10px] font-mono font-semibold ${avgUp ? "text-green-400" : "text-red-400"}`}>{s.avg_return != null ? `${s.avg_return > 0 ? "+" : ""}${s.avg_return.toFixed(1)}%` : "—"}</span>
                                        <span className="text-[10px] font-mono text-muted w-12 text-right">{wr}% WR</span>
                                    </div>
                                </div>
                                <div className="h-0.5 rounded-full" style={{ background: "rgba(255,255,255,0.06)" }}>
                                    <div className="h-0.5 rounded-full" style={{ width: `${wr}%`, background: wr >= 60 ? "#4ade80" : wr >= 40 ? "#fbbf24" : "#f87171", opacity: 0.7 }} />
                                </div>
                            </div>
                        )
                    })}
                </div>
            )}
        </Card>
    )
}

// ── Page ───────────────────────────────────────────────────────────────────

export default function DashboardPage() {
    const { data: openTrades, isLoading: openLoading } = useTrades("open")
    const { data: closedTrades, isLoading: closedLoading } = useTrades("closed")
    const { data: stats, isLoading: statsLoading } = usePortfolioStats()
    const { data: curve, isLoading: curveLoading } = useEquityCurve()
    const { data: analytics, isLoading: analyticsLoading } = usePortfolioAnalytics()
    const { data: signals, isLoading: signalsLoading } = useSignals()
    const liveQuotes = useLivePnL(openTrades?.map((t) => t.security.ticker) ?? [])

    const latestSignalDate = signals && signals.length > 0 ? signals[0].observed_at.slice(0, 10) : null
    const latestSignals = latestSignalDate ? (signals?.filter((s) => s.observed_at.slice(0, 10) === latestSignalDate) ?? []) : []

    const pnlPositive = !stats?.total_pnl || stats.total_pnl >= 0
    const chartColor = pnlPositive ? "#4ade80" : "#f87171"
    const pnlColor = stats?.total_pnl != null ? (stats.total_pnl >= 0 ? "text-green-400" : "text-red-400") : "text-secondary"
    const pnlAnimated = useCountUp(stats?.total_pnl ?? 0)

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
                    {statsLoading ? <Skeleton className="h-12 w-36" /> : <span className={`text-5xl font-bold font-mono leading-none ${pnlColor}`}>{formatINR(pnlAnimated, true)}</span>}
                </div>
            </motion.div>

            {/* Stat strip */}
            <StatStrip stats={stats} openTrades={openTrades} curve={curve} isLoading={statsLoading || openLoading || curveLoading} />

            {/* FY summary */}
            <FYStrip trades={closedTrades} isLoading={closedLoading} />

            {/* Analytics strip */}
            <AnalyticsStrip stats={stats} isLoading={statsLoading} />

            {/* 2-column: [equity curve + monthly bars] + right sidebar */}
            <div className="grid gap-4" style={{ gridTemplateColumns: "1fr 300px" }}>
                {/* Left: charts stacked */}
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2, duration: 0.5 }} className="flex flex-col gap-4">
                    <Card padding="md" className="flex flex-col gap-4">
                        <div className="flex items-center justify-between">
                            <span className="text-[10px] uppercase tracking-[0.15em] font-medium text-secondary">Equity Curve</span>
                            {!curveLoading && curve && <span className="text-[10px] font-mono text-muted">{curve.length} trades</span>}
                        </div>
                        {curveLoading && <Skeleton className="rounded-lg" style={{ height: 240 }} />}
                        {!curveLoading && (!curve || curve.length === 0) && (
                            <div className="flex items-center justify-center" style={{ height: 240 }}>
                                <p className="text-sm text-secondary">No closed trades yet</p>
                            </div>
                        )}
                        {!curveLoading && curve && curve.length > 0 && (
                            <div style={{ height: 240 }}>
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
                    <MonthlyBars trades={closedTrades} isLoading={closedLoading} />
                    <ReturnDistribution analytics={analytics} isLoading={analyticsLoading} />
                    <SectorPerformance analytics={analytics} isLoading={analyticsLoading} />
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
                        {!openLoading &&
                            (() => {
                                const livePnl =
                                    openTrades?.reduce((sum, t) => {
                                        const lp = liveQuotes[t.security.ticker]?.last_price
                                        if (lp && t.fill_price && t.fill_quantity) return sum + (lp - t.fill_price) * t.fill_quantity
                                        return sum + (t.pnl ?? 0)
                                    }, 0) ?? 0
                                const up = livePnl >= 0
                                return (
                                    <span className={`text-[10px] font-mono font-semibold ${up ? "text-green-400" : "text-red-400"}`}>
                                        {livePnl > 0 ? "+" : ""}
                                        {formatINR(livePnl, true)}
                                    </span>
                                )
                            })()}
                    </div>
                    {openLoading && [...Array(2)].map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
                    {!openLoading && (!openTrades || openTrades.length === 0) && <div className="py-8 text-center text-sm text-secondary rounded-xl bg-surface2 border border-white/4">No open positions</div>}
                    {openTrades?.map((t, i) => (
                        <PositionRow key={t.id} trade={t} index={i} livePrice={liveQuotes[t.security.ticker]?.last_price ?? null} />
                    ))}
                </div>

                <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between px-1">
                        <div className="flex items-center gap-2">
                            <span className="text-[10px] uppercase tracking-[0.15em] font-medium text-secondary">Latest Signals</span>
                            {latestSignalDate && <span className="text-[10px] font-mono text-muted">{latestSignalDate}</span>}
                        </div>
                        {!signalsLoading && <span className="text-[10px] font-mono text-muted">{latestSignals.length} signals</span>}
                    </div>
                    {signalsLoading && [...Array(2)].map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
                    {!signalsLoading && latestSignals.length === 0 && <div className="py-8 text-center text-sm text-secondary rounded-xl bg-surface2 border border-white/4">No signals yet</div>}
                    {latestSignals.map((s, i) => (
                        <SignalRow key={s.id} signal={s} index={i} />
                    ))}
                </div>
            </div>
        </div>
    )
}
