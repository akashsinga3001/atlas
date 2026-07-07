"use client"

import { useMemo } from "react"
import { useTrades } from "@/libraries/hooks/useTrades"
import { usePortfolioStats, useEquityCurve, usePortfolioAnalytics } from "@/libraries/hooks/usePortfolio"
import { useSignals } from "@/libraries/hooks/useSignals"
import { useLivePnL } from "@/libraries/hooks/useLivePnL"
import { usePriceFlash } from "@/libraries/hooks/usePriceFlash"
import { useCountUp } from "@/libraries/hooks/useCountUp"
import Card from "@/components/ui/Card"
import MiniRing from "@/components/ui/MiniRing"
import KpiTile from "@/components/ui/KpiTile"
import Skeleton from "@/components/ui/Skeleton"
import Badge from "@/components/ui/Badge"
import HudCorners from "@/components/ui/HudCorners"
import MissionClock from "@/components/ui/MissionClock"
import { motion } from "framer-motion"
import { TrendingUp, TrendingDown, Minus, Clock, AlertTriangle, Layers, Zap, LogOut, Wallet, Target, History, Flame } from "lucide-react"
import { Trade } from "@/libraries/types/trade"
import { Signal } from "@/libraries/types/signal"
import { AreaChart, Area, BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, LabelList, PieChart, Pie } from "recharts"
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

// ── KPI tile strip — icon + number tiles instead of a bordered stat table ──

function KpiStrip({ stats, openTrades, curve, isLoading }: { stats: PortfolioStats | undefined; openTrades: Trade[] | undefined; curve: { pnl: number }[] | undefined; isLoading: boolean }) {
    const deployed = openTrades?.reduce((s, t) => s + (t.invested_value ?? 0), 0) ?? 0
    const streak = curve ? computeStreak(curve) : { count: 0, type: null }
    const winRate = stats?.win_rate ?? null

    const tiles = [
        { icon: Layers, iconColor: "var(--color-accent)", label: "Open Positions", value: isLoading ? "—" : String(stats?.open_trades ?? 0) },
        { icon: Wallet, iconColor: "var(--color-accent)", label: "Deployed", value: isLoading ? "—" : formatINR(deployed, true) },
        { icon: Target, iconColor: "#4ade80", label: "Win Rate", value: isLoading ? "—" : winRate != null ? `${winRate}%` : "—", valueColor: winRate != null ? (winRate >= 50 ? "text-green-400" : "text-red-400") : undefined, ring: winRate ?? 0, ringColor: "#4ade80" },
        { icon: History, iconColor: "var(--color-secondary)", label: "Closed Trades", value: isLoading ? "—" : String(stats?.closed_trades ?? 0) },
        { icon: Clock, iconColor: "var(--color-secondary)", label: "Avg Hold", value: isLoading ? "—" : stats?.avg_holding_days != null ? `${stats.avg_holding_days}d` : "—" },
        { icon: Flame, iconColor: streak.type === "win" ? "#4ade80" : streak.type === "loss" ? "#f87171" : "var(--color-secondary)", label: "Streak", value: isLoading ? "—" : streak.count > 0 ? `${streak.count}${streak.type === "win" ? "W" : "L"}` : "—", valueColor: streak.type === "win" ? "text-green-400" : streak.type === "loss" ? "text-red-400" : undefined },
        { icon: TrendingUp, iconColor: "#4ade80", label: "Best Trade", value: isLoading ? "—" : stats?.best_trade_pct != null ? `+${stats.best_trade_pct.toFixed(1)}%` : "—", valueColor: "text-green-400" },
        { icon: TrendingDown, iconColor: "#f87171", label: "Worst Trade", value: isLoading ? "—" : stats?.worst_trade_pct != null ? `${stats.worst_trade_pct.toFixed(1)}%` : "—", valueColor: "text-red-400" }
    ]

    return (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.4, ease }} className="grid grid-cols-4 md:grid-cols-8 gap-2">
            {tiles.map((t, i) => (
                <KpiTile key={t.label} {...t} />
            ))}
        </motion.div>
    )
}

// ── Open Positions (compact row) ───────────────────────────────────────────

function PositionRow({ trade, index, livePrice }: { trade: Trade; index: number; livePrice?: number | null }) {
    const entry = trade.fill_price
    const current = livePrice ?? entry
    const livePnl = current && entry && trade.fill_quantity ? (current - entry) * trade.fill_quantity : trade.pnl
    const livePnlPct = current && entry ? ((current - entry) / entry) * 100 : trade.pnl_pct
    const pnlUp = livePnlPct !== null ? livePnlPct > 0 : null
    const pnlColor = pnlUp === null ? "text-secondary" : pnlUp ? "text-green-400" : "text-red-400"
    const PnlIcon = pnlUp === null ? Minus : pnlUp ? TrendingUp : TrendingDown
    const flashClass = usePriceFlash(livePrice)
    const accentColor = pnlUp === null ? "transparent" : pnlUp ? "#4ade80" : "#f87171"

    const stop = trade.state?.["current_stop"] as number | undefined
    const distPct = stop && current ? ((current - stop) / current) * 100 : null
    const riskDotClass = distPct === null ? "" : distPct < 3 ? "hud-dot-error" : distPct < 6 ? "hud-dot-warn" : "hud-dot-live"
    const riskUrgent = distPct !== null && distPct < 3

    const msDay = 86400000
    const entryTime = trade.entry_date ? new Date(trade.entry_date).getTime() : null
    const timeoutTime = trade.timeout_date ? new Date(trade.timeout_date).getTime() : null
    const daysHeld = entryTime ? Math.floor((Date.now() - entryTime) / msDay) : null
    const totalDays = entryTime && timeoutTime ? Math.floor((timeoutTime - entryTime) / msDay) : null
    const daysLeft = timeoutTime ? Math.ceil((timeoutTime - Date.now()) / msDay) : null
    const elapsedPct = daysHeld !== null && totalDays ? Math.min((daysHeld / totalDays) * 100, 100) : null
    const ringColor = elapsedPct === null ? "var(--color-accent)" : elapsedPct >= 85 ? "#f87171" : elapsedPct >= 60 ? "#fbbf24" : "#4ade80"
    const ringValue = elapsedPct !== null ? Math.max(100 - elapsedPct, 2) : 0

    return (
        <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.05, duration: 0.3, ease }}>
            <div className="group relative flex flex-col gap-1.5 py-2.5 px-3 hud-panel card-hover">
                <HudCorners opacity={0.35} />
                <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full transition-opacity duration-150" style={{ background: accentColor, opacity: 0.6 }} />
                <div className="absolute top-1.5 right-1.5">
                    <MiniRing value={ringValue} max={100} size={22} strokeWidth={2} color={ringColor} label={daysLeft !== null ? String(daysLeft) : undefined} />
                </div>

                <div className="flex items-center gap-1.5 pr-6">
                    <span className="text-xs font-bold text-primary tracking-tight truncate">{trade.security.ticker}</span>
                    {riskDotClass && <span className={`hud-dot ${riskDotClass} ${riskUrgent ? "live-pulse" : ""} shrink-0`} />}
                </div>

                <div className="flex items-center justify-between">
                    <span className="text-[10px] font-mono text-muted whitespace-nowrap">
                        ₹{entry?.toFixed(2) ?? "—"}
                        {livePrice && <span className={`text-accent ml-1 ${flashClass}`}>→ ₹{livePrice.toFixed(2)}</span>}
                    </span>
                </div>

                <div className="flex items-center justify-between">
                    <div className={`flex items-center gap-0.5 text-xs font-bold font-mono ${pnlColor}`}>
                        <PnlIcon size={10} strokeWidth={2.5} />
                        {livePnlPct !== null ? `${livePnlPct > 0 ? "+" : ""}${livePnlPct.toFixed(2)}%` : "—"}
                    </div>
                    <span className={`text-[10px] font-mono font-semibold ${pnlColor} opacity-80`}>{formatINR(livePnl, true)}</span>
                </div>

                <div className="flex items-center justify-between text-[9px] font-mono text-muted border-t border-white/5 pt-1.5">
                    <span className="text-red-400/70">{stop ? `stop ₹${stop.toFixed(2)}` : "—"}</span>
                    <span className={daysLeft !== null && daysLeft <= 5 ? "text-red-400 font-semibold" : "text-muted"}>{daysLeft !== null ? `${daysLeft}d left` : "—"}</span>
                </div>
            </div>
        </motion.div>
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

// ── Win / loss donut ────────────────────────────────────────────────────────

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
        <Card padding="sm" className="relative flex flex-col gap-2 hud-panel">
            <HudCorners opacity={0.3} />
            <span className="hud-label">Win / Loss</span>
            {isLoading ? (
                <Skeleton className="rounded-lg" style={{ height: 96 }} />
            ) : total === 0 ? (
                <div className="flex items-center justify-center text-xs text-muted" style={{ height: 96 }}>
                    No closed trades yet
                </div>
            ) : (
                <div className="relative flex items-center gap-3">
                    <div style={{ width: 88, height: 88 }} className="relative shrink-0">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie data={data} dataKey="value" nameKey="name" innerRadius={28} outerRadius={42} paddingAngle={3} stroke="none">
                                    {data.map((d, i) => (
                                        <Cell key={i} fill={d.color} />
                                    ))}
                                </Pie>
                            </PieChart>
                        </ResponsiveContainer>
                        <div className="absolute inset-0 flex items-center justify-center">
                            <span className="text-sm font-bold font-mono text-primary">{winRate}%</span>
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

// ── Monthly P&L bars ───────────────────────────────────────────────────────

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
        <Card padding="sm" className="relative flex flex-col gap-2 hud-panel">
            <HudCorners opacity={0.3} />
            <span className="hud-label">Monthly P&amp;L</span>
            {isLoading && <Skeleton className="rounded-lg" style={{ height: 96 }} />}
            {!isLoading && !hasAny && (
                <div className="flex items-center justify-center text-xs text-muted" style={{ height: 96 }}>
                    No monthly data
                </div>
            )}
            {!isLoading && hasAny && (
                <div style={{ height: 96 }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data} margin={{ top: 4, right: 0, bottom: 0, left: 0 }} barCategoryGap="25%">
                            <XAxis dataKey="label" tick={{ fontSize: 8, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} />
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

// ── Return distribution ────────────────────────────────────────────────────

function ReturnDistribution({ analytics, isLoading }: { analytics: PortfolioAnalytics | undefined; isLoading: boolean }) {
    const data = analytics?.return_distribution ?? []
    const hasAny = data.some((d) => d.count > 0)

    return (
        <Card padding="sm" className="relative flex flex-col gap-2 hud-panel">
            <HudCorners opacity={0.3} />
            <span className="hud-label">Distribution</span>
            {isLoading && <Skeleton className="rounded-lg" style={{ height: 96 }} />}
            {!isLoading && !hasAny && (
                <div className="flex items-center justify-center text-xs text-muted" style={{ height: 96 }}>
                    No distribution yet
                </div>
            )}
            {!isLoading && hasAny && (
                <div style={{ height: 96 }}>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data} margin={{ top: 10, right: 0, bottom: 0, left: 0 }} barCategoryGap="15%">
                            <XAxis dataKey="bucket" tick={{ fontSize: 7, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} interval={0} />
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
                                <LabelList dataKey="count" position="top" style={{ fontSize: 8, fill: "var(--color-muted)" }} formatter={(v: unknown) => ((v as number) > 0 ? String(v) : "")} />
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

// ── Sector performance ─────────────────────────────────────────────────────

function SectorPerformance({ analytics, isLoading }: { analytics: PortfolioAnalytics | undefined; isLoading: boolean }) {
    const data = (analytics?.sector_performance ?? []).slice(0, 4)

    return (
        <Card padding="sm" className="relative flex flex-col gap-2 hud-panel">
            <HudCorners opacity={0.3} />
            <span className="hud-label">Sector Win Rate</span>
            {isLoading && <Skeleton className="rounded-lg" style={{ height: 96 }} />}
            {!isLoading && data.length === 0 && (
                <div className="flex items-center justify-center text-xs text-muted" style={{ height: 96 }}>
                    No sector data yet
                </div>
            )}
            {!isLoading && data.length > 0 && (
                <div className="flex flex-col gap-2" style={{ minHeight: 96 }}>
                    {data.map((s) => {
                        const wr = s.win_rate ?? 0
                        return (
                            <div key={s.sector} className="flex flex-col gap-1">
                                <div className="flex items-center justify-between">
                                    <span className="text-[11px] text-secondary truncate pr-3">{s.sector}</span>
                                    <span className="text-[10px] font-mono text-muted shrink-0">{wr}%</span>
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

// ── Sector exposure ────────────────────────────────────────────────────────

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
        <Card padding="sm" className="relative flex flex-col gap-2 hud-panel">
            <HudCorners opacity={0.3} />
            <span className="hud-label">Exposure</span>
            {data.length === 0 ? (
                <div className="flex items-center justify-center text-xs text-muted" style={{ height: 96 }}>
                    No exposure data
                </div>
            ) : (
                <div className="flex items-center gap-3">
                    <div style={{ width: 76, height: 76 }} className="shrink-0">
                        <ResponsiveContainer width="100%" height="100%">
                            <PieChart>
                                <Pie data={data} dataKey="value" nameKey="sector" innerRadius={20} outerRadius={36} paddingAngle={2} stroke="none">
                                    {data.map((d, i) => (
                                        <Cell key={i} fill={d.color} />
                                    ))}
                                </Pie>
                                <Tooltip
                                    content={({ active, payload }) => {
                                        if (!active || !payload?.length) return null
                                        const d = payload[0]?.payload
                                        return (
                                            <div className="rounded-lg px-2.5 py-2 text-xs" style={{ background: "#161616", border: "1px solid rgba(255,255,255,0.08)" }}>
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
                                <span className="text-[10px] font-mono text-muted shrink-0">{total > 0 ? `${((d.value / total) * 100).toFixed(0)}%` : "—"}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </Card>
    )
}

// ── Expiring soon ──────────────────────────────────────────────────────────

function ExpiringSoon({ trades, className }: { trades: Trade[] | undefined; className?: string }) {
    const expiring = (trades ?? [])
        .filter((t) => t.timeout_date)
        .map((t) => ({ ...t, daysLeft: daysUntil(t.timeout_date) }))
        .filter((t) => t.daysLeft <= 7)
        .sort((a, b) => a.daysLeft - b.daysLeft)

    return (
        <div className={`relative flex flex-col gap-3 px-4 py-4 hud-panel ${className ?? ""}`}>
            <HudCorners opacity={0.3} />
            <div className="flex items-center gap-1.5">
                <AlertTriangle size={11} className="text-amber-400" strokeWidth={2} />
                <span className="font-mono text-[10px] uppercase tracking-[0.12em] font-medium text-secondary">Expiring Soon</span>
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

// ── Recent exits (table) ────────────────────────────────────────────────────

function RecentExits({ trades, isLoading }: { trades: Trade[] | undefined; isLoading: boolean }) {
    const recent = (trades ?? []).slice(0, 6)
    return (
        <Card padding="sm" className="relative flex flex-col gap-2 hud-panel">
            <HudCorners opacity={0.3} />
            <span className="hud-label">Recent Exits</span>
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
                        <tr className="border-b border-white/5">
                            {["Ticker", "Exit Date", "P&L", "Reason"].map((h) => (
                                <th key={h} className="text-left pb-2 hud-label-sm text-[9px] font-medium">
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {recent.map((t) => {
                            const up = t.pnl_pct != null ? t.pnl_pct >= 0 : null
                            return (
                                <tr key={t.id} className="border-b border-white/5 last:border-0">
                                    <td className="py-2 font-bold text-primary">{t.security.ticker}</td>
                                    <td className="py-2 font-mono text-muted">{t.exit_date ?? "—"}</td>
                                    <td className={`py-2 font-mono font-bold ${up === null ? "text-secondary" : up ? "text-green-400" : "text-red-400"}`}>{t.pnl_pct != null ? `${t.pnl_pct > 0 ? "+" : ""}${t.pnl_pct.toFixed(1)}%` : "—"}</td>
                                    <td className="py-2 text-muted truncate max-w-[110px]">{t.exit_reason ?? "—"}</td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
            )}
        </Card>
    )
}

// ── Latest signals (table) ──────────────────────────────────────────────────

function LatestSignals({ signals, date, isLoading }: { signals: Signal[]; date: string | null; isLoading: boolean }) {
    return (
        <Card padding="sm" className="relative flex flex-col gap-2 hud-panel">
            <HudCorners opacity={0.3} />
            <div className="flex items-center justify-between">
                <span className="hud-label">Latest Signals</span>
                {date && <span className="text-[9px] font-mono text-muted">{date}</span>}
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
                        <tr className="border-b border-white/5">
                            {["Ticker", "Time", "Status", "Fill"].map((h) => (
                                <th key={h} className="text-left pb-2 hud-label-sm text-[9px] font-medium">
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {signals.slice(0, 6).map((s) => {
                            const entered = s.signal_status === "entered"
                            return (
                                <tr key={s.id} className="border-b border-white/5 last:border-0">
                                    <td className="py-2 font-bold text-primary">{s.security.ticker}</td>
                                    <td className="py-2 font-mono text-muted">{s.observed_at.slice(11, 16)}</td>
                                    <td className="py-2">
                                        <Badge label={s.signal_status.toUpperCase()} variant={entered ? "green" : "muted"} />
                                    </td>
                                    <td className="py-2 font-mono text-muted">{entered && s.trade_fill_price ? `₹${s.trade_fill_price.toFixed(2)}` : "—"}</td>
                                </tr>
                            )
                        })}
                    </tbody>
                </table>
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

    return (
        <div className="flex flex-col gap-4">
            {/* Hero */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between">
                <div className="flex flex-col gap-2">
                    <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-secondary mb-1">Mission Control</p>
                    <h1 className="text-4xl font-bold tracking-tight text-primary leading-none">Dashboard</h1>
                    <MissionClock />
                </div>
                <div className="relative flex flex-col items-end gap-1 px-5 py-4 hud-panel">
                    <HudCorners opacity={0.35} />
                    <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-secondary">
                        Total P&amp;L <span className="normal-case tracking-normal opacity-50">(closed + open)</span>
                    </span>
                    {statsLoading ? <Skeleton className="h-12 w-36" /> : <span className={`text-5xl font-bold font-mono leading-none ${pnlColor}`}>{formatINR(pnlAnimated, true)}</span>}
                    {liveTotalPnl !== 0 && !statsLoading && (
                        <span className="text-[10px] font-mono text-secondary">
                            {formatINR(stats?.total_pnl, true)} closed · <span className={liveTotalPnl >= 0 ? "text-green-400/70" : "text-red-400/70"}>{formatINR(liveTotalPnl, true)} open</span>
                        </span>
                    )}
                </div>
            </motion.div>

            {/* KPI tile strip */}
            <KpiStrip stats={stats} openTrades={openTrades} curve={curve} isLoading={statsLoading || openLoading || curveLoading} />

            {/* Equity Curve (dominant) + Win/Loss donut + Expiring Soon rail */}
            <div className="grid gap-3" style={{ gridTemplateColumns: "1fr 260px" }}>
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15, duration: 0.5 }}>
                    <Card padding="md" className="relative flex flex-col gap-4 hud-panel">
                        <HudCorners />
                        <div className="flex items-center justify-between">
                            <span className="hud-label">Equity Curve</span>
                            {!curveLoading && curve && <span className="text-[10px] font-mono text-muted">{curve.length} trades</span>}
                        </div>
                        {curveLoading && <Skeleton className="rounded-lg" style={{ height: 260 }} />}
                        {!curveLoading && (!curve || curve.length === 0) && (
                            <div className="flex flex-col items-center justify-center gap-2" style={{ height: 260 }}>
                                <TrendingUp size={28} className="text-muted" strokeWidth={1.5} />
                                <p className="text-sm font-medium text-secondary">No equity curve yet</p>
                                <p className="text-xs text-muted">Appears after first closed trade</p>
                            </div>
                        )}
                        {!curveLoading && curve && curve.length > 0 && (
                            <div style={{ height: 260 }}>
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

                <motion.div initial={{ opacity: 0, x: 12 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.2, duration: 0.4, ease }} className="flex flex-col gap-3">
                    <WinLossDonut trades={closedTrades} isLoading={closedLoading} />
                    <ExpiringSoon trades={openTrades} className="flex-1" />
                </motion.div>
            </div>

            {/* Open Positions — surfaced early */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2, duration: 0.4, ease }}>
                <div className="flex flex-col gap-2">
                    <div className="flex items-center justify-between px-1">
                        <span className="hud-label">Open Positions</span>
                        {!openLoading && <span className={`text-[10px] font-mono font-semibold ${liveTotalPnl >= 0 ? "text-green-400" : "text-red-400"}`}>{formatINR(liveTotalPnl, true)}</span>}
                    </div>
                    {openLoading && [...Array(2)].map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
                    {!openLoading && (!openTrades || openTrades.length === 0) && (
                        <div className="py-8 flex flex-col items-center gap-2 rounded-xl bg-surface2 border border-white/4">
                            <Layers size={22} className="text-muted" strokeWidth={1.5} />
                            <p className="text-sm font-medium text-secondary">No open positions</p>
                            <p className="text-xs text-muted">Entered trades will appear here</p>
                        </div>
                    )}
                    {openTrades && openTrades.length > 0 && (
                        <div className="grid grid-cols-4 gap-2">
                            {openTrades.map((t, i) => (
                                <PositionRow key={t.id} trade={t} index={i} livePrice={liveQuotes[t.security.ticker]?.last_price ?? null} />
                            ))}
                        </div>
                    )}
                </div>
            </motion.div>

            {/* Dense analytics grid — 4 small varied widgets side by side */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25, duration: 0.4, ease }} className="grid grid-cols-4 gap-3">
                <MonthlyBars trades={closedTrades} isLoading={closedLoading} />
                <ReturnDistribution analytics={analytics} isLoading={analyticsLoading} />
                <SectorPerformance analytics={analytics} isLoading={analyticsLoading} />
                <SectorExposure trades={openTrades} />
            </motion.div>

            {/* Activity tables — Recent Exits + Latest Signals */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.4, ease }} className="grid grid-cols-2 gap-3">
                <RecentExits trades={closedTrades} isLoading={closedLoading} />
                <LatestSignals signals={latestSignals} date={latestSignalDate} isLoading={signalsLoading} />
            </motion.div>
        </div>
    )
}
