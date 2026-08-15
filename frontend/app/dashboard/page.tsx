"use client"

import { useMemo, useState } from "react"
import { useTrades } from "@/libraries/hooks/useTrades"
import { usePortfolioStats, useEquityCurve, usePortfolioAnalytics } from "@/libraries/hooks/usePortfolio"
import { useMarketSentiment, useMarketSentimentHistory } from "@/libraries/hooks/useMarket"
import { useSignals } from "@/libraries/hooks/useSignals"
import { useLivePnL } from "@/libraries/hooks/useLivePnL"
import { usePriceFlash } from "@/libraries/hooks/usePriceFlash"
import { useCountUp } from "@/libraries/hooks/useCountUp"
import Card from "@/components/ui/Card"
import MiniRing from "@/components/ui/MiniRing"
import KpiTile from "@/components/ui/KpiTile"
import Skeleton from "@/components/ui/Skeleton"
import Badge from "@/components/ui/Badge"
import MissionClock from "@/components/ui/MissionClock"
import { motion } from "framer-motion"
import { TrendingUp, TrendingDown, Minus, Clock, AlertTriangle, Layers, Zap, LogOut, Wallet, Target, History, Flame, Radio, Activity, ArrowUpRight, ArrowDownRight, BarChart2, BarChart3, BarChart4, type LucideIcon } from "lucide-react"
import { Trade } from "@/libraries/types/trade"
import { Signal } from "@/libraries/types/signal"
import { AreaChart, Area, BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, LabelList, PieChart, Pie } from "recharts"
import { formatINR, FY_START } from "@/libraries/utils/format"
import { PortfolioStats, PortfolioAnalytics } from "@/libraries/types/portfolio"
import { MarketSentiment } from "@/libraries/types/market"

type SortKey = "pnl" | "days_left" | "stop_dist" | "invested"

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
    { key: "pnl", label: "P&L %" },
    { key: "days_left", label: "Days Left" },
    { key: "stop_dist", label: "Stop Dist." },
    { key: "invested", label: "Invested" }
]

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

function daysUntil(dateStr: string) {
    return Math.ceil((new Date(dateStr).getTime() - Date.now()) / 86400000)
}

function daysBetween(a: string, b: string) {
    return Math.floor((new Date(b).getTime() - new Date(a).getTime()) / 86400000)
}

function today() {
    return new Date().toISOString().slice(0, 10)
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

// --- KPI tile strip ---------------------------------------------------------

function KpiStrip({ stats, openTrades, curve, isLoading }: { stats: PortfolioStats | undefined; openTrades: Trade[] | undefined; curve: { pnl: number }[] | undefined; isLoading: boolean }) {
    const deployed = openTrades?.reduce((s, t) => s + (t.invested_value ?? 0), 0) ?? 0
    const streak = curve ? computeStreak(curve) : { count: 0, type: null }
    const winRate = stats?.win_rate ?? null

    const tiles = [
        { icon: Layers, iconColor: "var(--color-secondary)", label: "Open Positions", value: isLoading ? "-" : String(stats?.open_trades ?? 0) },
        { icon: Wallet, iconColor: "var(--color-secondary)", label: "Deployed", value: isLoading ? "-" : formatINR(deployed, true) },
        { icon: Target, iconColor: "#4ade80", label: "Win Rate", value: isLoading ? "-" : winRate != null ? `${winRate}%` : "-", valueColor: winRate != null ? (winRate >= 50 ? "text-green-400" : "text-red-400") : undefined, ring: winRate ?? 0, ringColor: "#4ade80" },
        { icon: History, iconColor: "var(--color-secondary)", label: "Closed Trades", value: isLoading ? "-" : String(stats?.closed_trades ?? 0) },
        { icon: Clock, iconColor: "var(--color-secondary)", label: "Avg Hold", value: isLoading ? "-" : stats?.avg_holding_days != null ? `${stats.avg_holding_days}d` : "-" },
        { icon: Flame, iconColor: streak.type === "win" ? "#4ade80" : streak.type === "loss" ? "#f87171" : "var(--color-secondary)", label: "Streak", value: isLoading ? "-" : streak.count > 0 ? `${streak.count}${streak.type === "win" ? "W" : "L"}` : "-", valueColor: streak.type === "win" ? "text-green-400" : streak.type === "loss" ? "text-red-400" : undefined },
        { icon: TrendingUp, iconColor: "#4ade80", label: "Best Trade", value: isLoading ? "-" : stats?.best_trade_pct != null ? `+${stats.best_trade_pct.toFixed(1)}%` : "-", valueColor: "text-green-400" },
        { icon: TrendingDown, iconColor: "#f87171", label: "Worst Trade", value: isLoading ? "-" : stats?.worst_trade_pct != null ? `${stats.worst_trade_pct.toFixed(1)}%` : "-", valueColor: "text-red-400" }
    ]

    return (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.4, ease }} className="grid grid-cols-4 md:grid-cols-8 gap-2">
            {tiles.map((t, i) => (
                <KpiTile key={t.label} {...t} />
            ))}
        </motion.div>
    )
}

// --- Open Positions ? full table row (holdings-style) ---------------------??

function PositionTableRow({ trade, index, totalInvested, livePrice }: { trade: Trade; index: number; totalInvested: number; livePrice?: number | null }) {
    const currentPrice = livePrice ?? null
    const livePnl = currentPrice && trade.fill_price && trade.fill_quantity ? (currentPrice - trade.fill_price) * trade.fill_quantity : trade.pnl
    const livePnlPct = currentPrice && trade.fill_price ? ((currentPrice - trade.fill_price) / trade.fill_price) * 100 : trade.pnl_pct
    const liveValue = currentPrice && trade.fill_quantity ? currentPrice * trade.fill_quantity : trade.invested_value !== null && trade.pnl !== null ? (trade.invested_value ?? 0) + (trade.pnl ?? 0) : trade.invested_value

    const pnlUp = livePnl !== null ? livePnl > 0 : null
    const pnlColor = pnlUp === null ? "text-secondary" : pnlUp ? "text-green-400" : "text-red-400"
    const PnlIcon = pnlUp === null ? Minus : pnlUp ? TrendingUp : TrendingDown
    const flashClass = usePriceFlash(currentPrice)

    const daysHeld = trade.entry_date ? daysBetween(trade.entry_date, today()) : null
    const totalDays = trade.entry_date && trade.timeout_date ? daysBetween(trade.entry_date, trade.timeout_date) : null
    const daysLeft = trade.timeout_date ? daysBetween(today(), trade.timeout_date) : null
    const progress = daysHeld !== null && totalDays !== null && totalDays > 0 ? Math.min((daysHeld / totalDays) * 100, 100) : null

    const progressColor = progress === null ? "var(--color-muted)" : progress >= 85 ? "#f87171" : progress >= 60 ? "#fbbf24" : "#4ade80"
    const daysLeftUrgent = daysLeft !== null && daysLeft <= 5

    const weight = totalInvested > 0 && trade.invested_value ? (trade.invested_value / totalInvested) * 100 : null

    const stopPrice = trade.state?.["current_stop"] as number | undefined
    const distPct = stopPrice && currentPrice ? ((currentPrice - stopPrice) / currentPrice) * 100 : stopPrice && trade.fill_price ? ((trade.fill_price - stopPrice) / trade.fill_price) * 100 : null
    const distColor = distPct !== null ? (distPct < 3 ? "text-red-400" : distPct < 6 ? "text-amber-400" : "text-secondary") : "text-secondary"

    const pnlBadgeBg = pnlUp === null ? "var(--color-surface2)" : pnlUp ? "rgba(74,222,128,0.1)" : "rgba(248,113,113,0.1)"
    const accentColor = pnlUp === null ? "transparent" : pnlUp ? "#4ade80" : "#f87171"

    return (
        <motion.tr initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: index * 0.05, duration: 0.3 }} className={`group transition-colors border-b border-border ${pnlUp ? "hover:bg-green-400/3" : "hover:bg-red-400/3"}`}>
            <td className="py-5 pr-6 pl-5 relative">
                <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full" style={{ background: accentColor, opacity: 0.6 }} />
                <div className="flex flex-col gap-1">
                    <span className="text-base font-bold text-primary tracking-tight whitespace-nowrap">{trade.security.ticker}</span>
                    <span className="text-[11px] text-muted truncate max-w-[180px]">{[trade.security.sector, trade.security.industry].filter(Boolean).join(" ·")}</span>
                </div>
            </td>
            <td className="py-5 pr-8 font-mono text-xs text-secondary whitespace-nowrap">
                <div className="flex flex-col gap-0.5">
                    <span className="text-primary font-semibold">₹{trade.fill_price?.toFixed(2) ?? "-"}</span>
                    <span className="text-muted">
                        qty {trade.fill_quantity ?? "-"} ·{weight !== null ? `${weight.toFixed(1)}%` : "-"} wt
                    </span>
                </div>
            </td>
            <td className="py-5 pr-8 font-mono text-sm whitespace-nowrap">
                {currentPrice ? (
                    <span className={`flex items-center gap-1.5 text-primary font-semibold ${flashClass}`}>
                        <Radio size={9} className="text-success" />₹{currentPrice.toFixed(2)}
                    </span>
                ) : (
                    <span className="text-muted">-</span>
                )}
            </td>
            <td className="py-5 pr-8 whitespace-nowrap">
                <div className="inline-flex items-center gap-3 rounded-xl px-3.5 py-2" style={{ background: pnlBadgeBg }}>
                    <div className={`flex items-center gap-1.5 text-base font-bold font-mono ${pnlColor}`}>
                        <PnlIcon size={14} strokeWidth={2.5} />
                        {livePnlPct !== null ? `${livePnlPct > 0 ? "+" : ""}${livePnlPct.toFixed(2)}%` : "-"}
                    </div>
                    <span className={`text-xs font-mono font-semibold ${pnlColor} opacity-80`}>{formatINR(livePnl, true)}</span>
                </div>
            </td>
            <td className="py-5 pr-8 whitespace-nowrap">
                <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-mono font-semibold text-red-400">{stopPrice ? `₹${stopPrice.toFixed(2)}` : "-"}</span>
                    {distPct !== null && <span className={`text-[11px] font-mono ${distColor}`}>{distPct.toFixed(1)}% away</span>}
                </div>
            </td>
            <td className="py-5 pr-8 font-mono text-sm font-semibold text-primary whitespace-nowrap">{formatINR(liveValue, true)}</td>
            <td className="py-5 pr-5">
                <div className="flex flex-col gap-1.5 min-w-[150px]">
                    <div className="flex items-center justify-between gap-2">
                        <span className="text-[11px] font-mono text-muted whitespace-nowrap">{daysHeld !== null ? `${daysHeld}d held` : "-"}</span>
                        <span className={`text-[11px] font-mono font-semibold whitespace-nowrap ${daysLeftUrgent ? "text-red-400" : "text-muted"}`}>{daysLeft !== null ? `${daysLeft}d left` : "-"}</span>
                    </div>
                    <div className="h-1.5 rounded-full overflow-hidden bg-border">
                        {progress !== null && <div className="h-1.5 rounded-full transition-all" style={{ width: `${progress}%`, background: progressColor, opacity: 0.8 }} />}
                    </div>
                </div>
            </td>
        </motion.tr>
    )
}

// --- Chart tooltip ---------------------------------------------------------?

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: { value: number }[]; label?: string }) => {
    if (!active || !payload?.length) return null
    const pnl = payload[0]?.value ?? 0
    return (
        <div className="rounded-xl px-3 py-2 text-xs" style={{ background: "var(--color-tooltip)", border: "1px solid var(--color-border)", boxShadow: "var(--shadow-large)" }}>
            <div className="font-mono mb-1 text-secondary">{label}</div>
            <div className={`font-bold font-mono ${pnl >= 0 ? "text-green-400" : "text-red-400"}`}>{formatINR(pnl, true)}</div>
        </div>
    )
}

// --- Win / loss donut ------------------------------------------------------??

function WinLossDonut({ trades, isLoading }: { trades: Trade[] | undefined; isLoading: boolean }) {
    const wins = (trades ?? []).filter((t) => (t.pnl ?? 0) > 0).length
    const losses = (trades ?? []).filter((t) => (t.pnl ?? 0) <= 0 && t.pnl !== null).length
    const total = wins + losses
    const winRate = total > 0 ? Math.round((wins / total) * 100) : null
    const data = [
        { name: "Win", value: wins, color: "#4ade80" },
        { name: "Loss", value: losses, color: "#f87171" }
    ]

    return (
        <Card padding="sm" className="flex flex-col gap-2">
            <span className="text-xs font-medium text-secondary">Win / Loss</span>
            {isLoading ? (
                <Skeleton className="rounded-lg" style={{ height: 160 }} />
            ) : total === 0 ? (
                <div className="flex items-center justify-center text-xs text-muted" style={{ height: 160 }}>
                    No closed trades yet
                </div>
            ) : (
                <div className="relative flex items-center gap-4">
                    <div style={{ width: 140, height: 140 }} className="relative shrink-0">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie data={data} dataKey="value" nameKey="name" innerRadius={42} outerRadius={66} paddingAngle={3} stroke="none">
                                    {data.map((d, i) => (
                                        <Cell key={i} fill={d.color} />
                                    ))}
                                </Pie>
                            </PieChart>
                        </ResponsiveContainer>
                        <div className="absolute inset-0 flex items-center justify-center">
                            <span className="text-xl font-bold font-mono text-primary">{winRate}%</span>
                        </div>
                    </div>
                    <div className="flex flex-col gap-1.5">
                        <div className="flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#4ade80" }} />
                            <span className="text-[11px] text-secondary">{wins} wins</span>
                        </div>
                        <div className="flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full" style={{ background: "#f87171" }} />
                            <span className="text-[11px] text-secondary">{losses} losses</span>
                        </div>
                    </div>
                </div>
            )}
        </Card>
    )
}

// --- Monthly P&L bars ------------------------------------------------------?

function MonthlyBars({ trades, isLoading }: { trades: Trade[] | undefined; isLoading: boolean }) {
    const data = useMemo(() => {
        const map: Record<string, number> = {}
        for (const t of trades ?? []) {
            if (!t.exit_date || t.pnl === null) continue
            const key = t.exit_date.slice(0, 7)
            map[key] = (map[key] ?? 0) + t.pnl
        }
        const result = []
        const now = new Date()
        for (let i = 5; i >= 0; i--) {
            const d = new Date(now.getFullYear(), now.getMonth() - i, 1)
            const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`
            const label = d.toLocaleString("en", { month: "short" }).toUpperCase()
            result.push({ key, label, pnl: map[key] ?? null })
        }
        return result
    }, [trades])

    const hasAny = data.some((d) => d.pnl !== null)

    return (
        <Card padding="sm" className="flex flex-col gap-2">
            <span className="text-xs font-medium text-secondary">Monthly P&amp;L</span>
            {isLoading && <Skeleton className="rounded-lg" style={{ height: 220 }} />}
            {!isLoading && !hasAny && (
                <div className="flex items-center justify-center text-xs text-muted" style={{ height: 220 }}>
                    No monthly data
                </div>
            )}
            {!isLoading && hasAny && (
                <div style={{ height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }} barCategoryGap="25%">
                            <XAxis dataKey="label" tick={{ fontSize: 8, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} />
                            <YAxis hide />
                            <Tooltip
                                cursor={{ fill: "var(--color-surface2)" }}
                                content={({ active, payload }) => {
                                    if (!active || !payload?.length) return null
                                    const d = payload[0]?.payload
                                    return (
                                        <div className="rounded-lg px-2.5 py-2 text-xs" style={{ background: "var(--color-tooltip)", border: "1px solid var(--color-border)", boxShadow: "var(--shadow-large)" }}>
                                            <div className="text-secondary font-mono mb-1">{d.key}</div>
                                            <div className={`font-bold font-mono ${(d.pnl ?? 0) >= 0 ? "text-green-400" : "text-red-400"}`}>{formatINR(d.pnl, true)}</div>
                                        </div>
                                    )
                                }}
                            />
                            <ReferenceLine y={0} stroke="var(--color-border)" />
                            <Bar dataKey="pnl" radius={[3, 3, 0, 0]}>
                                {data.map((d, i) => (
                                    <Cell key={i} fill={d.pnl === null ? "var(--color-border)" : d.pnl >= 0 ? "rgba(74,222,128,0.55)" : "rgba(248,113,113,0.55)"} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}
        </Card>
    )
}

// --- Return distribution ---------------------------------------------------?

function ReturnDistribution({ analytics, isLoading }: { analytics: PortfolioAnalytics | undefined; isLoading: boolean }) {
    const data = analytics?.return_distribution ?? []
    const hasAny = data.some((d) => d.count > 0)

    return (
        <Card padding="sm" className="flex flex-col gap-2">
            <span className="text-xs font-medium text-secondary">Distribution</span>
            {isLoading && <Skeleton className="rounded-lg" style={{ height: 220 }} />}
            {!isLoading && !hasAny && (
                <div className="flex items-center justify-center text-xs text-muted" style={{ height: 220 }}>
                    No distribution yet
                </div>
            )}
            {!isLoading && hasAny && (
                <div style={{ height: 220 }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data} margin={{ top: 10, right: 0, bottom: 0, left: 0 }} barCategoryGap="15%">
                            <XAxis dataKey="bucket" tick={{ fontSize: 7, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} interval={0} />
                            <YAxis hide />
                            <Tooltip
                                cursor={{ fill: "var(--color-surface2)" }}
                                content={({ active, payload }) => {
                                    if (!active || !payload?.length) return null
                                    const d = payload[0]?.payload
                                    return (
                                        <div className="rounded-lg px-2.5 py-2 text-xs" style={{ background: "var(--color-tooltip)", border: "1px solid var(--color-border)", boxShadow: "var(--shadow-large)" }}>
                                            <div className="text-secondary font-mono mb-1">{d.bucket}</div>
                                            <div className="font-bold font-mono text-primary">
                                                {d.count} trade{d.count !== 1 ? "s" : ""}
                                            </div>
                                        </div>
                                    )
                                }}
                            />
                            <Bar dataKey="count" radius={[3, 3, 0, 0]}>
                                <LabelList dataKey="count" position="top" style={{ fontSize: 8, fill: "var(--color-muted)" }} formatter={(v: unknown) => ((v as number) > 0 ? String(v) : "")} />
                                {data.map((d, i) => (
                                    <Cell key={i} fill={d.count === 0 ? "var(--color-border)" : d.is_win ? "rgba(74,222,128,0.55)" : "rgba(248,113,113,0.55)"} />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            )}
        </Card>
    )
}

// --- Sector performance ---------------------------------------------------??

function SectorPerformance({ analytics, isLoading }: { analytics: PortfolioAnalytics | undefined; isLoading: boolean }) {
    const data = (analytics?.sector_performance ?? []).slice(0, 4)

    return (
        <Card padding="sm" className="flex flex-col gap-2">
            <span className="text-xs font-medium text-secondary">Sector Win Rate</span>
            {isLoading && <Skeleton className="rounded-lg" style={{ height: 220 }} />}
            {!isLoading && data.length === 0 && (
                <div className="flex items-center justify-center text-xs text-muted" style={{ height: 220 }}>
                    No sector data yet
                </div>
            )}
            {!isLoading && data.length > 0 && (
                <div className="flex flex-col gap-2" style={{ minHeight: 220 }}>
                    {data.map((s) => {
                        const wr = s.win_rate ?? 0
                        return (
                            <div key={s.sector} className="flex flex-col gap-1">
                                <div className="flex items-center justify-between">
                                    <span className="text-[11px] text-secondary truncate pr-3">{s.sector}</span>
                                    <span className="text-[10px] font-mono text-muted shrink-0">{wr}%</span>
                                </div>
                                <div className="h-0.5 rounded-full bg-border">
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

// --- Sector exposure ------------------------------------------------------??

const SECTOR_COLORS = ["#60a5fa", "#4ade80", "#fbbf24", "#f87171", "#a78bfa", "#22d3ee", "#fb923c", "#f472b6"]

function SectorExposure({ trades }: { trades: Trade[] | undefined }) {
    const sectors: Record<string, number> = {}
    ;(trades ?? []).forEach((t) => {
        const s = t.security.sector ?? "Other"
        sectors[s] = (sectors[s] || 0) + (t.invested_value ?? 0)
    })
    const entries = Object.entries(sectors)
        .sort((a, b) => b[1] - a[1])
        .slice(0, 4)
    const total = entries.reduce((s, [, v]) => s + v, 0)
    const data = entries.map(([sector, value], i) => ({ sector, value, color: SECTOR_COLORS[i % SECTOR_COLORS.length] }))

    return (
        <Card padding="sm" className="flex flex-col gap-2">
            <span className="text-xs font-medium text-secondary">Exposure</span>
            {data.length === 0 ? (
                <div className="flex items-center justify-center text-xs text-muted" style={{ height: 220 }}>
                    No exposure data
                </div>
            ) : (
                <div className="flex items-center gap-4" style={{ height: 220 }}>
                    <div style={{ width: 160, height: 160 }} className="shrink-0">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie data={data} dataKey="value" nameKey="sector" innerRadius={40} outerRadius={74} paddingAngle={2} stroke="none">
                                    {data.map((d, i) => (
                                        <Cell key={i} fill={d.color} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    content={({ active, payload }) => {
                                        if (!active || !payload?.length) return null
                                        const d = payload[0]?.payload
                                        return (
                                            <div className="rounded-lg px-2.5 py-2 text-xs" style={{ background: "var(--color-tooltip)", border: "1px solid var(--color-border)", boxShadow: "var(--shadow-large)" }}>
                                                <div className="text-secondary mb-1">{d.sector}</div>
                                                <div className="font-bold font-mono text-primary">{formatINR(d.value, true)}</div>
                                            </div>
                                        )
                                    }}
                                />
                            </PieChart>
                        </ResponsiveContainer>
                    </div>
                    <div className="flex flex-col gap-1 flex-1 min-w-0">
                        {data.map((d) => (
                            <div key={d.sector} className="flex items-center justify-between gap-2">
                                <div className="flex items-center gap-1.5 min-w-0">
                                    <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: d.color }} />
                                    <span className="text-[10px] text-secondary truncate">{d.sector}</span>
                                </div>
                                <span className="text-[10px] font-mono text-muted shrink-0">{total > 0 ? `${((d.value / total) * 100).toFixed(0)}%` : "-"}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </Card>
    )
}

// --- Market sentiment -------------------------------------------------------

const SENTIMENT_ZONES = [
    { max: 20, color: "#f87171" },
    { max: 40, color: "#fb923c" },
    { max: 60, color: "#9ca3af" },
    { max: 80, color: "#86efac" },
    { max: 100, color: "#4ade80" }
]

function sentimentColor(score: number | null) {
    if (score === null) return "var(--color-muted)"
    return SENTIMENT_ZONES.find((z) => score <= z.max)?.color ?? "#4ade80"
}

function polarPoint(cx: number, cy: number, r: number, angleDeg: number) {
    const rad = (angleDeg * Math.PI) / 180
    return { x: cx + r * Math.cos(rad), y: cy - r * Math.sin(rad) }
}

function scoreToAngle(score: number) {
    return 180 - (Math.min(Math.max(score, 0), 100) / 100) * 180
}

function SentimentGauge({ score, color, size = 148 }: { score: number; color: string; size?: number }) {
    const cx = size / 2
    const cy = size / 2
    const r = size / 2 - 12
    const needle = polarPoint(cx, cy, r - 10, scoreToAngle(score))

    return (
        <svg width={size} height={size / 2 + 14} viewBox={`0 0 ${size} ${size / 2 + 14}`}>
            {SENTIMENT_ZONES.map((z, i) => {
                const prevMax = i === 0 ? 0 : SENTIMENT_ZONES[i - 1].max
                const p1 = polarPoint(cx, cy, r, scoreToAngle(prevMax))
                const p2 = polarPoint(cx, cy, r, scoreToAngle(z.max))
                return <path key={z.max} d={`M ${p1.x} ${p1.y} A ${r} ${r} 0 0 1 ${p2.x} ${p2.y}`} stroke={z.color} strokeWidth={9} strokeLinecap="round" fill="none" opacity={0.9} />
            })}
            <line x1={cx} y1={cy} x2={needle.x} y2={needle.y} stroke="white" strokeWidth={2} strokeLinecap="round" style={{ transition: "all 0.8s cubic-bezier(0.23,1,0.32,1)" }} />
            <circle cx={cx} cy={cy} r={4} fill="white" />
        </svg>
    )
}

function statColor(kind: "ratio" | "pct" | "high" | "low", value: number | null) {
    if (value === null) return "var(--color-muted)"
    if (kind === "ratio") return value >= 1 ? "#4ade80" : "#f87171"
    if (kind === "pct") return value >= 50 ? "#4ade80" : "#f87171"
    if (kind === "high") return "#4ade80"
    return "#f87171"
}

function SentimentStatTile({ label, icon: Icon, value, color, fillPct }: { label: string; icon: LucideIcon; value: string; color: string; fillPct: number | null }) {
    return (
        <div className="relative flex flex-col gap-1.5 px-3 py-2.5 rounded-[var(--radius-card)] overflow-hidden bg-surface border border-border">
            <Icon size={40} strokeWidth={1.2} style={{ color, opacity: 0.1, position: "absolute", bottom: -8, right: -6, pointerEvents: "none" }} />
            <span className="text-[10px] font-medium text-secondary uppercase tracking-wide">{label}</span>
            <span className="text-lg font-semibold leading-none" style={{ color }}>
                {value}
            </span>
            <div className="h-1 rounded-full overflow-hidden bg-border">
                {fillPct !== null && <div className="h-1 rounded-full transition-all" style={{ width: `${Math.min(Math.max(fillPct, 0), 100)}%`, background: color, opacity: 0.85 }} />}
            </div>
        </div>
    )
}

function MarketSentimentCard({ sentiment, history, isLoading }: { sentiment: MarketSentiment | undefined; history: MarketSentiment[] | undefined; isLoading: boolean }) {
    const score = sentiment?.regime_score ?? null
    const color = sentimentColor(score)
    const animatedScore = useCountUp(score ?? 0)

    const ratio = sentiment?.advance_decline_ratio ?? null
    const highs = sentiment?.new_highs_count ?? null
    const lows = sentiment?.new_lows_count ?? null
    const hlTotal = (highs ?? 0) + (lows ?? 0)

    const stats = [
        { label: "Adv / Decl", icon: Activity, value: ratio != null ? ratio.toFixed(2) : "-", color: statColor("ratio", ratio), fillPct: ratio != null ? (ratio / (1 + ratio)) * 100 : null },
        { label: "> EMA20", icon: BarChart2, value: sentiment?.pct_above_ema20 != null ? `${sentiment.pct_above_ema20.toFixed(0)}%` : "-", color: statColor("pct", sentiment?.pct_above_ema20 ?? null), fillPct: sentiment?.pct_above_ema20 ?? null },
        { label: "> EMA50", icon: BarChart3, value: sentiment?.pct_above_ema50 != null ? `${sentiment.pct_above_ema50.toFixed(0)}%` : "-", color: statColor("pct", sentiment?.pct_above_ema50 ?? null), fillPct: sentiment?.pct_above_ema50 ?? null },
        { label: "> EMA200", icon: BarChart4, value: sentiment?.pct_above_ema200 != null ? `${sentiment.pct_above_ema200.toFixed(0)}%` : "-", color: statColor("pct", sentiment?.pct_above_ema200 ?? null), fillPct: sentiment?.pct_above_ema200 ?? null },
        { label: "New Highs", icon: ArrowUpRight, value: highs != null ? String(highs) : "-", color: statColor("high", highs), fillPct: hlTotal > 0 ? ((highs ?? 0) / hlTotal) * 100 : null },
        { label: "New Lows", icon: ArrowDownRight, value: lows != null ? String(lows) : "-", color: statColor("low", lows), fillPct: hlTotal > 0 ? ((lows ?? 0) / hlTotal) * 100 : null }
    ]

    const trend = (history ?? []).filter((h) => h.regime_score != null).map((h) => ({ date: h.candle_timestamp.slice(5, 10), score: h.regime_score as number }))

    return (
        <Card padding="sm" className="flex flex-col gap-3">
            <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-secondary">Market Sentiment</span>
                {sentiment?.candle_timestamp && <span className="text-[9px] font-mono text-muted">{sentiment.candle_timestamp.slice(0, 10)}</span>}
            </div>
            {isLoading && <Skeleton className="rounded-lg" style={{ height: 130 }} />}
            {!isLoading && !sentiment?.regime_score && (
                <div className="flex items-center justify-center text-xs text-muted" style={{ height: 130 }}>
                    No sentiment data yet
                </div>
            )}
            {!isLoading && sentiment?.regime_score != null && (
                <div className="flex items-center gap-6">
                    <div className="flex flex-col items-center shrink-0" style={{ width: 148 }}>
                        <SentimentGauge score={score!} color={color} />
                        <span className="text-3xl font-bold font-mono leading-none -mt-3" style={{ color }}>
                            {Math.round(animatedScore)}
                        </span>
                        <span className="text-[11px] font-semibold uppercase tracking-wide mt-1" style={{ color }}>
                            {sentiment.label ?? "-"}
                        </span>
                    </div>

                    <div className="w-px self-stretch bg-border" />

                    <div className="grid grid-cols-3 gap-2 flex-1">
                        {stats.map((s) => (
                            <SentimentStatTile key={s.label} label={s.label} icon={s.icon} value={s.value} color={s.color} fillPct={s.fillPct} />
                        ))}
                    </div>

                    {trend.length > 1 && (
                        <>
                            <div className="w-px self-stretch hidden lg:block bg-border" />
                            <div className="hidden lg:flex flex-col gap-1 shrink-0" style={{ width: 170 }}>
                                <span className="text-[9px] font-mono uppercase tracking-[0.1em] text-muted">Trend ({trend.length}d)</span>
                                <div style={{ height: 56 }}>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <AreaChart data={trend} margin={{ top: 4, right: 0, bottom: 0, left: 0 }}>
                                            <defs>
                                                <linearGradient id="sentimentTrendGrad" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="0%" stopColor={color} stopOpacity={0.35} />
                                                    <stop offset="100%" stopColor={color} stopOpacity={0} />
                                                </linearGradient>
                                            </defs>
                                            <ReferenceLine y={50} stroke="var(--color-border)" strokeDasharray="3 3" />
                                            <Tooltip
                                                content={({ active, payload }) => {
                                                    if (!active || !payload?.length) return null
                                                    const d = payload[0]?.payload
                                                    return (
                                                        <div className="rounded-lg px-2.5 py-1.5 text-xs" style={{ background: "var(--color-tooltip)", border: "1px solid var(--color-border)", boxShadow: "var(--shadow-large)" }}>
                                                            <div className="text-secondary font-mono">{d.date}</div>
                                                            <div className="font-bold font-mono text-primary">{Math.round(d.score)}</div>
                                                        </div>
                                                    )
                                                }}
                                            />
                                            <Area type="monotone" dataKey="score" stroke={color} strokeWidth={1.5} fill="url(#sentimentTrendGrad)" dot={false} />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>
                        </>
                    )}
                </div>
            )}
        </Card>
    )
}

// --- Expiring soon ---------------------------------------------------------?

function ExpiringSoon({ trades, className }: { trades: Trade[] | undefined; className?: string }) {
    const expiring = (trades ?? [])
        .filter((t) => t.timeout_date)
        .map((t) => ({ ...t, daysLeft: daysUntil(t.timeout_date) }))
        .filter((t) => t.daysLeft <= 7)
        .sort((a, b) => a.daysLeft - b.daysLeft)

    return (
        <div className={`flex flex-col gap-3 px-4 py-4 bg-surface border border-border rounded-[var(--radius-card)] ${className ?? ""}`}>
            <div className="flex items-center gap-1.5">
                <AlertTriangle size={11} className="text-warning" strokeWidth={2} />
                <span className="text-xs font-medium text-secondary">Expiring Soon</span>
            </div>
            {expiring.length === 0 ? (
                <p className="text-xs text-muted">Nothing expiring within 7 days</p>
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

// --- Recent exits (table) ---------------------------------------------------?

function RecentExits({ trades, isLoading }: { trades: Trade[] | undefined; isLoading: boolean }) {
    const recent = (trades ?? []).slice(0, 6)
    return (
        <Card padding="sm" className="flex flex-col gap-2">
            <span className="text-xs font-medium text-secondary">Recent Exits</span>
            {isLoading && <Skeleton className="rounded-lg" style={{ height: 160 }} />}
            {!isLoading && recent.length === 0 && (
                <div className="flex flex-col items-center justify-center gap-2" style={{ height: 160 }}>
                    <LogOut size={20} className="text-muted" strokeWidth={1.5} />
                    <p className="text-xs text-muted">No exits yet</p>
                </div>
            )}
            {!isLoading && recent.length > 0 && (
                <table className="w-full text-xs">
                    <thead>
                        <tr className="border-b border-border">
                            {["Ticker", "Exit Date", "P&L", "Reason"].map((h) => (
                                <th key={h} className="text-left pb-2 text-[10px] font-medium text-secondary uppercase tracking-wide">
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {recent.map((t) => {
                            const up = t.pnl_pct != null ? t.pnl_pct >= 0 : null
                            return (
                                <tr key={t.id} className="border-b border-border last:border-0">
                                    <td className="py-2 font-semibold text-primary">{t.security.ticker}</td>
                                    <td className="py-2 text-muted">{t.exit_date ?? "-"}</td>
                                    <td className={`py-2 font-semibold ${up === null ? "text-secondary" : up ? "text-success" : "text-danger"}`}>{t.pnl_pct != null ? `${t.pnl_pct > 0 ? "+" : ""}${t.pnl_pct.toFixed(1)}%` : "-"}</td>
                                    <td className="py-2 text-muted truncate max-w-[110px]">{t.exit_reason ?? "-"}</td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            )}
        </Card>
    )
}

// --- Latest signals (table) ------------------------------------------------??

function LatestSignals({ signals, date, isLoading }: { signals: Signal[]; date: string | null; isLoading: boolean }) {
    return (
        <Card padding="sm" className="flex flex-col gap-2">
            <div className="flex items-center justify-between">
                <span className="text-xs font-medium text-secondary">Latest Signals</span>
                {date && <span className="text-[10px] text-muted">{date}</span>}
            </div>
            {isLoading && <Skeleton className="rounded-lg" style={{ height: 160 }} />}
            {!isLoading && signals.length === 0 && (
                <div className="flex flex-col items-center justify-center gap-2" style={{ height: 160 }}>
                    <Zap size={20} className="text-muted" strokeWidth={1.5} />
                    <p className="text-xs text-muted">No signals today</p>
                </div>
            )}
            {!isLoading && signals.length > 0 && (
                <table className="w-full text-xs">
                    <thead>
                        <tr className="border-b border-border">
                            {["Ticker", "Time", "Status", "Fill"].map((h) => (
                                <th key={h} className="text-left pb-2 text-[10px] font-medium text-secondary uppercase tracking-wide">
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {signals.slice(0, 6).map((s) => {
                            const entered = s.signal_status === "entered"
                            return (
                                <tr key={s.id} className="border-b border-border last:border-0">
                                    <td className="py-2 font-semibold text-primary">{s.security.ticker}</td>
                                    <td className="py-2 text-muted">{s.observed_at.slice(11, 16)}</td>
                                    <td className="py-2">
                                        <Badge label={s.signal_status.toUpperCase()} variant={entered ? "green" : "muted"} />
                                    </td>
                                    <td className="py-2 text-muted">{entered && s.trade_fill_price ? `₹${s.trade_fill_price.toFixed(2)}` : "-"}</td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            )}
        </Card>
    )
}

// --- Page ------------------------------------------------------------------?

export default function DashboardPage() {
    const [sortKey, setSortKey] = useState<SortKey>("pnl")
    const { data: openTrades, isLoading: openLoading } = useTrades("open")
    const { data: closedTrades, isLoading: closedLoading } = useTrades("closed")
    const { data: stats, isLoading: statsLoading } = usePortfolioStats()
    const { data: curve, isLoading: curveLoading } = useEquityCurve()
    const { data: analytics, isLoading: analyticsLoading } = usePortfolioAnalytics()
    const { data: signals, isLoading: signalsLoading } = useSignals()
    const { data: sentiment, isLoading: sentimentLoading } = useMarketSentiment()
    const { data: sentimentHistory } = useMarketSentimentHistory(30)
    const liveQuotes = useLivePnL(openTrades?.map((t) => t.security.ticker) ?? [])

    const latestSignalDate = signals && signals.length > 0 ? signals[0].observed_at.slice(0, 10) : null
    const latestSignals = latestSignalDate ? (signals?.filter((s) => s.observed_at.slice(0, 10) === latestSignalDate) ?? []) : []

    const liveTotalPnl =
        openTrades?.reduce((sum, t) => {
            const lp = liveQuotes[t.security.ticker]?.last_price
            if (lp && t.fill_price && t.fill_quantity) return sum + (lp - t.fill_price) * t.fill_quantity
            return sum + (t.pnl ?? 0)
        }, 0) ?? 0

    const combinedPnl = (stats?.total_pnl ?? 0) + liveTotalPnl
    const pnlPositive = combinedPnl >= 0
    const chartColor = pnlPositive ? "#4ade80" : "#f87171"
    const pnlColor = combinedPnl >= 0 ? "text-green-400" : "text-red-400"
    const pnlAnimated = useCountUp(combinedPnl)

    const totalInvested = openTrades?.reduce((s, t) => s + (t.invested_value ?? 0), 0) ?? 0

    const sortedTrades = [...(openTrades ?? [])].sort((a, b) => {
        const lp = (t: Trade) => liveQuotes[t.security.ticker]?.last_price ?? null
        if (sortKey === "pnl") {
            const pa = lp(a) && a.fill_price ? ((lp(a)! - a.fill_price) / a.fill_price) * 100 : (a.pnl_pct ?? -Infinity)
            const pb = lp(b) && b.fill_price ? ((lp(b)! - b.fill_price) / b.fill_price) * 100 : (b.pnl_pct ?? -Infinity)
            return pa - pb
        }
        if (sortKey === "days_left") {
            const da = a.timeout_date ? Math.ceil((new Date(a.timeout_date).getTime() - Date.now()) / 86400000) : Infinity
            const db = b.timeout_date ? Math.ceil((new Date(b.timeout_date).getTime() - Date.now()) / 86400000) : Infinity
            return da - db
        }
        if (sortKey === "stop_dist") {
            const stopDist = (t: Trade) => {
                const stop = t.state?.["current_stop"] as number | undefined
                const price = lp(t) ?? t.fill_price
                if (!stop || !price) return Infinity
                return ((price - stop) / price) * 100
            }
            const da = stopDist(a),
                db = stopDist(b)
            if (!isFinite(da) && !isFinite(db)) return 0
            return da - db
        }
        const iv = (t: Trade) => t.invested_value ?? (t.fill_price ?? 0) * (t.fill_quantity ?? 0)
        if (sortKey === "invested") return iv(b) - iv(a)
        return 0
    })

    return (
        <div className="flex flex-col gap-4">
            {/* Hero */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between">
                <div className="flex flex-col gap-2">
                    <p className="text-xs text-secondary mb-1">Mission Control</p>
                    <h1 className="text-4xl font-bold tracking-tight text-primary leading-none">Dashboard</h1>
                    <MissionClock />
                </div>
                <div className="flex flex-col items-end gap-1 px-5 py-4 bg-surface border border-border rounded-[var(--radius-card)]">
                    <span className="text-xs text-secondary">
                        Total P&amp;L <span className="opacity-50">(closed + open)</span>
                    </span>
                    {statsLoading ? <Skeleton className="h-12 w-36" /> : <span className={`text-5xl font-bold leading-none ${pnlColor}`}>{formatINR(pnlAnimated, true)}</span>}
                    {liveTotalPnl !== 0 && !statsLoading && (
                        <span className="text-[11px] text-secondary">
                            {formatINR(stats?.total_pnl, true)} closed ·<span className={liveTotalPnl >= 0 ? "text-success/70" : "text-danger/70"}>{formatINR(liveTotalPnl, true)} open</span>
                        </span>
                    )}
                </div>
            </motion.div>

            {/* Market Sentiment */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.08, duration: 0.4, ease }}>
                <MarketSentimentCard sentiment={sentiment} history={sentimentHistory} isLoading={sentimentLoading} />
            </motion.div>

            {/* KPI tile strip */}
            <KpiStrip stats={stats} openTrades={openTrades} curve={curve} isLoading={statsLoading || openLoading || curveLoading} />

            {/* Equity Curve (dominant) + Win/Loss donut + Expiring Soon rail */}
            <div className="grid gap-3" style={{ gridTemplateColumns: "1fr 280px" }}>
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15, duration: 0.5 }}>
                    <Card padding="md" className="flex flex-col gap-4">
                        <div className="flex items-center justify-between">
                            <span className="text-xs font-medium text-secondary">Equity Curve</span>
                            {!curveLoading && curve && <span className="text-[10px] text-muted">{curve.length} trades</span>}
                        </div>
                        {curveLoading && <Skeleton className="rounded-lg" style={{ height: 460 }} />}
                        {!curveLoading && (!curve || curve.length === 0) && (
                            <div className="flex flex-col items-center justify-center gap-2" style={{ height: 460 }}>
                                <TrendingUp size={28} className="text-muted" strokeWidth={1.5} />
                                <p className="text-sm font-medium text-secondary">No equity curve yet</p>
                                <p className="text-xs text-muted">Appears after first closed trade</p>
                            </div>
                        )}
                        {!curveLoading && curve && curve.length > 0 && (
                            <div style={{ height: 460 }}>
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
                                        <ReferenceLine y={0} stroke="var(--color-border)" strokeDasharray="4 4" />
                                        <Tooltip content={<CustomTooltip />} />
                                        <Area type="monotone" dataKey="cumulative_pnl" stroke={chartColor} strokeWidth={2} fill="url(#curveGrad)" dot={false} />
                                    </AreaChart>
                                </ResponsiveContainer>
                            </div>
                        )}
                    </Card>
                </motion.div>

                <motion.div initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2, duration: 0.4, ease }} className="flex flex-col gap-3">
                    <WinLossDonut trades={closedTrades} isLoading={closedLoading} />
                    <ExpiringSoon trades={openTrades} className="flex-1" />
                </motion.div>
            </div>

            {/* Open Positions ? full holdings-style table */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2, duration: 0.4, ease }}>
                <div className="flex flex-col gap-3">
                    <div className="flex items-center justify-between px-1">
                        <span className="text-xs font-medium text-secondary">Open Positions</span>
                        {!openLoading && <span className={`text-[11px] font-semibold ${liveTotalPnl >= 0 ? "text-success" : "text-danger"}`}>{formatINR(liveTotalPnl, true)}</span>}
                    </div>
                    {openLoading && (
                        <div className="flex flex-col gap-2">
                            {[...Array(3)].map((_, i) => (
                                <Skeleton key={i} className="h-14 rounded-lg" />
                            ))}
                        </div>
                    )}
                    {!openLoading && (!openTrades || openTrades.length === 0) && (
                        <div className="py-12 flex flex-col items-center gap-2 rounded-[var(--radius-card)] bg-surface2 border border-border">
                            <Layers size={22} className="text-muted" strokeWidth={1.5} />
                            <p className="text-sm font-medium text-secondary">No open positions</p>
                            <p className="text-xs text-muted">Entered trades will appear here</p>
                        </div>
                    )}
                    {!openLoading && openTrades && openTrades.length > 0 && (
                        <>
                            {openTrades.length > 1 && (
                                <div className="flex items-center gap-2 px-1">
                                    <span className="text-[11px] text-muted">Sort by</span>
                                    {SORT_OPTIONS.map((opt) => (
                                        <button key={opt.key} onClick={() => setSortKey(opt.key)} className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-150 border ${sortKey === opt.key ? "bg-primary text-bg border-primary" : "bg-transparent text-secondary border-border hover:text-primary hover:border-muted"}`}>
                                            {opt.label}
                                        </button>
                                    ))}
                                </div>
                            )}
                            <Card padding="sm">
                                <div className="overflow-x-auto">
                                    <table className="w-full text-sm">
                                        <thead>
                                            <tr className="border-b border-border">
                                                {["Ticker", "Entry x Qty x Wt", "Current", "P&L", "Stop", "Curr. Value", "Holding Period"].map((h) => (
                                                    <th key={h} className="py-3 pr-8 first:pl-5 text-[10px] text-secondary uppercase tracking-wide font-medium text-left whitespace-nowrap">
                                                        {h}
                                                    </th>
                                                ))}
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {sortedTrades.map((trade, i) => (
                                                <PositionTableRow key={trade.id} trade={trade} index={i} totalInvested={totalInvested} livePrice={liveQuotes[trade.security.ticker]?.last_price ?? null} />
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </Card>
                        </>
                    )}
                </div>
            </motion.div>

            {/* Dense analytics grid ? 4 small varied widgets side by side */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25, duration: 0.4, ease }} className="grid grid-cols-4 gap-3">
                <MonthlyBars trades={closedTrades} isLoading={closedLoading} />
                <ReturnDistribution analytics={analytics} isLoading={analyticsLoading} />
                <SectorPerformance analytics={analytics} isLoading={analyticsLoading} />
                <SectorExposure trades={openTrades} />
            </motion.div>

            {/* Activity tables ? Recent Exits + Latest Signals */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.4, ease }} className="grid grid-cols-2 gap-3">
                <RecentExits trades={closedTrades} isLoading={closedLoading} />
                <LatestSignals signals={latestSignals} date={latestSignalDate} isLoading={signalsLoading} />
            </motion.div>
        </div>
    )
}
