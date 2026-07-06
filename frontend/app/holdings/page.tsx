"use client"

import { useState } from "react"
import { useTrades } from "@/libraries/hooks/useTrades"
import { useLivePnL } from "@/libraries/hooks/useLivePnL"
import Skeleton from "@/components/ui/Skeleton"
import Card from "@/components/ui/Card"
import HudCorners from "@/components/ui/HudCorners"
import { motion } from "framer-motion"
import { TrendingUp, TrendingDown, Minus, Radio } from "lucide-react"
import { Trade } from "@/libraries/types/trade"
import { formatINR } from "@/libraries/utils/format"
import { usePriceFlash } from "@/libraries/hooks/usePriceFlash"

type SortKey = "pnl" | "days_left" | "stop_dist" | "invested"

const SORT_OPTIONS: { key: SortKey; label: string }[] = [
    { key: "pnl", label: "P&L %" },
    { key: "days_left", label: "Days Left" },
    { key: "stop_dist", label: "Stop Dist." },
    { key: "invested", label: "Invested" }
]

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

function daysBetween(a: string, b: string) {
    return Math.floor((new Date(b).getTime() - new Date(a).getTime()) / 86400000)
}

function today() {
    return new Date().toISOString().slice(0, 10)
}

function getLivePnl(trade: Trade, liveQuotes: Record<string, { last_price: number | null }>) {
    const currentPrice = liveQuotes[trade.security.ticker]?.last_price ?? null
    const pnl = currentPrice && trade.fill_price && trade.fill_quantity ? (currentPrice - trade.fill_price) * trade.fill_quantity : trade.pnl
    const pnlPct = currentPrice && trade.fill_price ? ((currentPrice - trade.fill_price) / trade.fill_price) * 100 : trade.pnl_pct
    return { pnl, pnlPct }
}

function PositionTableRow({ trade, index, totalInvested, livePrice }: { trade: Trade; index: number; totalInvested: number; livePrice?: number | null }) {
    const currentPrice = livePrice ?? null
    const livePnl = currentPrice && trade.fill_price && trade.fill_quantity ? (currentPrice - trade.fill_price) * trade.fill_quantity : trade.pnl
    const livePnlPct = currentPrice && trade.fill_price ? ((currentPrice - trade.fill_price) / trade.fill_price) * 100 : trade.pnl_pct
    const liveValue = currentPrice && trade.fill_quantity ? currentPrice * trade.fill_quantity : trade.invested_value !== null && trade.pnl !== null ? trade.invested_value + trade.pnl : trade.invested_value

    const pnlUp = livePnl !== null ? livePnl > 0 : null
    const pnlColor = pnlUp === null ? "text-secondary" : pnlUp ? "text-green-400" : "text-red-400"
    const PnlIcon = pnlUp === null ? Minus : pnlUp ? TrendingUp : TrendingDown
    const flashClass = usePriceFlash(currentPrice)

    const daysHeld = trade.entry_date ? daysBetween(trade.entry_date, today()) : null
    const totalDays = trade.entry_date && trade.timeout_date ? daysBetween(trade.entry_date, trade.timeout_date) : null
    const daysLeft = trade.timeout_date ? daysBetween(today(), trade.timeout_date) : null
    const progress = daysHeld !== null && totalDays !== null && totalDays > 0 ? Math.min((daysHeld / totalDays) * 100, 100) : null

    const progressColor = progress === null ? "#555" : progress >= 85 ? "#f87171" : progress >= 60 ? "#fbbf24" : "#4ade80"
    const daysLeftUrgent = daysLeft !== null && daysLeft <= 5

    const weight = totalInvested > 0 && trade.invested_value ? (trade.invested_value / totalInvested) * 100 : null

    const stopPrice = trade.state?.["current_stop"] as number | undefined
    const distPct = stopPrice && currentPrice ? ((currentPrice - stopPrice) / currentPrice) * 100 : stopPrice && trade.fill_price ? ((trade.fill_price - stopPrice) / trade.fill_price) * 100 : null
    const distColor = distPct !== null ? (distPct < 3 ? "text-red-400" : distPct < 6 ? "text-amber-400" : "text-secondary") : "text-secondary"

    const pnlBadgeBg = pnlUp === null ? "rgba(255,255,255,0.04)" : pnlUp ? "rgba(74,222,128,0.1)" : "rgba(248,113,113,0.1)"
    const accentColor = pnlUp === null ? "transparent" : pnlUp ? "#4ade80" : "#f87171"

    return (
        <motion.tr initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: index * 0.05, duration: 0.3 }} className={`group transition-colors ${pnlUp ? "hover:bg-green-400/3" : "hover:bg-red-400/3"}`} style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <td className="py-5 pr-6 pl-5 relative">
                <span className="absolute left-0 top-2 bottom-2 w-1 rounded-r-full" style={{ background: accentColor, opacity: 0.6 }} />
                <div className="flex flex-col gap-1">
                    <span className="text-base font-bold text-primary tracking-tight whitespace-nowrap">{trade.security.ticker}</span>
                    <span className="text-[11px] text-muted truncate max-w-[180px]">{[trade.security.sector, trade.security.industry].filter(Boolean).join(" · ")}</span>
                </div>
            </td>
            <td className="py-5 pr-8 font-mono text-xs text-secondary whitespace-nowrap">
                <div className="flex flex-col gap-0.5">
                    <span className="text-primary font-semibold">₹{trade.fill_price?.toFixed(2) ?? "—"}</span>
                    <span className="text-muted">
                        qty {trade.fill_quantity ?? "—"} · {weight !== null ? `${weight.toFixed(1)}%` : "—"} wt
                    </span>
                </div>
            </td>
            <td className="py-5 pr-8 font-mono text-sm whitespace-nowrap">
                {currentPrice ? (
                    <span className={`flex items-center gap-1.5 text-primary font-semibold ${flashClass}`}>
                        <Radio size={9} className="text-green-400 live-pulse" />₹{currentPrice.toFixed(2)}
                    </span>
                ) : (
                    <span className="text-muted">—</span>
                )}
            </td>
            <td className="py-5 pr-8 whitespace-nowrap">
                <div className="inline-flex items-center gap-3 rounded-xl px-3.5 py-2" style={{ background: pnlBadgeBg }}>
                    <div className={`flex items-center gap-1.5 text-base font-bold font-mono ${pnlColor}`}>
                        <PnlIcon size={14} strokeWidth={2.5} />
                        {livePnlPct !== null ? `${livePnlPct > 0 ? "+" : ""}${livePnlPct.toFixed(2)}%` : "—"}
                    </div>
                    <span className={`text-xs font-mono font-semibold ${pnlColor} opacity-80`}>{formatINR(livePnl, true)}</span>
                </div>
            </td>
            <td className="py-5 pr-8 whitespace-nowrap">
                <div className="flex flex-col gap-0.5">
                    <span className="text-sm font-mono font-semibold text-red-400">{stopPrice ? `₹${stopPrice.toFixed(2)}` : "—"}</span>
                    {distPct !== null && <span className={`text-[11px] font-mono ${distColor}`}>{distPct.toFixed(1)}% away</span>}
                </div>
            </td>
            <td className="py-5 pr-8 font-mono text-sm font-semibold text-primary whitespace-nowrap">{formatINR(liveValue, true)}</td>
            <td className="py-5 pr-5">
                <div className="flex flex-col gap-1.5 min-w-[150px]">
                    <div className="flex items-center justify-between gap-2">
                        <span className="text-[11px] font-mono text-muted whitespace-nowrap">{daysHeld !== null ? `${daysHeld}d held` : "—"}</span>
                        <span className={`text-[11px] font-mono font-semibold whitespace-nowrap ${daysLeftUrgent ? "text-red-400" : "text-muted"}`}>{daysLeft !== null ? `${daysLeft}d left` : "—"}</span>
                    </div>
                    <div className="h-1.5 rounded-full overflow-hidden" style={{ background: "rgba(255,255,255,0.06)" }}>
                        {progress !== null && <div className="h-1.5 rounded-full transition-all" style={{ width: `${progress}%`, background: progressColor, opacity: 0.8 }} />}
                    </div>
                </div>
            </td>
        </motion.tr>
    )
}

export default function HoldingsPage() {
    const [sortKey, setSortKey] = useState<SortKey>("pnl")
    const { data: trades, isLoading } = useTrades("open")
    const tickers = trades?.map((t) => t.security.ticker) ?? []
    const liveQuotes = useLivePnL(tickers)

    const sortedTrades = [...(trades ?? [])].sort((a, b) => {
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
                return stop && price ? ((price - stop) / price) * 100 : Infinity
            }
            return stopDist(a) - stopDist(b)
        }
        if (sortKey === "invested") return (b.invested_value ?? 0) - (a.invested_value ?? 0)
        return 0
    })

    const totalInvested = trades?.reduce((s, t) => s + (t.invested_value ?? 0), 0) ?? 0
    const liveTotalPnl =
        trades?.reduce((t, trade) => {
            const q = liveQuotes[trade.security.ticker]
            if (q?.last_price && trade.fill_price && trade.fill_quantity) {
                return t + (q.last_price - trade.fill_price) * trade.fill_quantity
            }
            return t + (trade.pnl ?? 0)
        }, 0) ?? 0
    const totalPnl = liveTotalPnl
    const count = trades?.length ?? 0
    const winners = trades?.filter((t) => (getLivePnl(t, liveQuotes).pnl ?? 0) > 0).length ?? 0
    const avgReturn = count > 0 ? (trades?.reduce((s, t) => s + (getLivePnl(t, liveQuotes).pnlPct ?? 0), 0) ?? 0) / count : null
    const bestTrade = trades?.reduce(
        (best, t) => {
            const pct = getLivePnl(t, liveQuotes).pnlPct
            const bestPct = best ? getLivePnl(best, liveQuotes).pnlPct : null
            return (pct ?? -Infinity) > (bestPct ?? -Infinity) ? t : best
        },
        null as Trade | null
    )
    const worstTrade = trades?.reduce(
        (worst, t) => {
            const pct = getLivePnl(t, liveQuotes).pnlPct
            const worstPct = worst ? getLivePnl(worst, liveQuotes).pnlPct : null
            return (pct ?? Infinity) < (worstPct ?? Infinity) ? t : worst
        },
        null as Trade | null
    )
    const bestPnlPct = bestTrade ? getLivePnl(bestTrade, liveQuotes).pnlPct : null
    const worstPnlPct = worstTrade ? getLivePnl(worstTrade, liveQuotes).pnlPct : null

    return (
        <div className="flex flex-col gap-6">
            {/* Hero */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between">
                <div>
                    <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-secondary mb-1">Positions</p>
                    <h1 className="text-4xl font-bold tracking-tight text-primary leading-none">Holdings</h1>
                </div>
                <div className="relative flex flex-col items-end gap-1 px-5 py-4 hud-panel">
                    <HudCorners opacity={0.35} />
                    <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-secondary">Unrealised P&amp;L</span>
                    {isLoading ? <Skeleton className="h-12 w-36" /> : <span className={`text-5xl font-bold font-mono leading-none ${totalPnl >= 0 ? "text-green-400" : "text-red-400"}`}>{formatINR(totalPnl, true)}</span>}
                </div>
            </motion.div>

            {/* Stat strip */}
            <div className="grid grid-cols-6 gap-3">
                {[
                    { label: "Positions", value: isLoading ? "—" : String(count) },
                    { label: "Total Invested", value: isLoading ? "—" : formatINR(totalInvested, true) },
                    { label: "In Profit", value: isLoading ? "—" : String(winners), sub: count > 0 ? `${count - winners} at loss` : undefined },
                    { label: "Avg Return", value: isLoading ? "—" : avgReturn !== null ? `${avgReturn > 0 ? "+" : ""}${avgReturn.toFixed(2)}%` : "—", color: avgReturn !== null ? (avgReturn >= 0 ? "text-green-400" : "text-red-400") : undefined },
                    { label: "Best", value: isLoading ? "—" : bestPnlPct != null ? `${bestPnlPct > 0 ? "+" : ""}${bestPnlPct.toFixed(1)}%` : "—", sub: bestTrade?.security.ticker, color: "text-green-400" },
                    { label: "Worst", value: isLoading ? "—" : worstPnlPct != null ? `${worstPnlPct.toFixed(1)}%` : "—", sub: worstTrade?.security.ticker, color: worstPnlPct !== null && worstPnlPct < 0 ? "text-red-400" : "text-green-400" }
                ].map(({ label, value, sub, color }, i) => (
                    <motion.div key={label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05, duration: 0.4, ease }} className="h-full">
                        <div className="flex flex-col gap-1.5 px-4 py-4 rounded-xl bg-surface2 border border-white/4 h-full justify-center">
                            <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-secondary font-medium">{label}</span>
                            <span className="flex items-baseline gap-1.5">
                                <span className={`text-xl font-bold font-mono leading-none ${color ?? "text-primary"}`}>{value}</span>
                                {sub && <span className="text-[10px] text-muted truncate">{sub}</span>}
                            </span>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Sort controls */}
            {!isLoading && trades && trades.length > 1 && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="flex items-center gap-2">
                    <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-muted">Sort by</span>
                    {SORT_OPTIONS.map((opt) => (
                        <button key={opt.key} onClick={() => setSortKey(opt.key)} className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-150 border ${sortKey === opt.key ? "bg-accent/10 text-accent border-accent/30" : "bg-transparent text-secondary border-white/8 hover:text-primary hover:border-white/20"}`}>
                            {opt.label}
                        </button>
                    ))}
                </motion.div>
            )}

            {/* Position table */}
            {isLoading && (
                <div className="flex flex-col gap-2">
                    {[...Array(4)].map((_, i) => (
                        <Skeleton key={i} className="h-14 rounded-lg" />
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
            {!isLoading && sortedTrades.length > 0 && (
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }}>
                    <Card padding="sm" className="relative hud-panel">
                        <HudCorners opacity={0.3} />
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                                        {["Ticker", "Entry × Qty × Wt", "Current", "P&L", "Stop", "Curr. Value", "Holding Period"].map((h) => (
                                            <th key={h} className="py-3 pr-8 first:pl-5 font-mono text-[10px] text-secondary uppercase tracking-[0.15em] font-medium text-left whitespace-nowrap">
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
                </motion.div>
            )}
        </div>
    )
}
