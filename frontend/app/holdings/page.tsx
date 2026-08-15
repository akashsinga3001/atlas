"use client"

import { useState } from "react"
import { useTrades } from "@/libraries/hooks/useTrades"
import { useLivePnL } from "@/libraries/hooks/useLivePnL"
import Skeleton from "@/components/ui/Skeleton"
import Card from "@/components/ui/Card"
import KpiTile from "@/components/ui/KpiTile"
import { motion } from "framer-motion"
import { TrendingUp, TrendingDown, Minus, Radio, Layers, Wallet, Target } from "lucide-react"
import { Trade } from "@/libraries/types/trade"
import { formatINR, pctColor } from "@/libraries/utils/format"
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
    const pnlColor = pnlUp === null ? "text-secondary" : pctColor(livePnl)
    const PnlIcon = pnlUp === null ? Minus : pnlUp ? TrendingUp : TrendingDown
    const flashClass = usePriceFlash(currentPrice)

    const daysHeld = trade.entry_date ? daysBetween(trade.entry_date, today()) : null
    const totalDays = trade.entry_date && trade.timeout_date ? daysBetween(trade.entry_date, trade.timeout_date) : null
    const daysLeft = trade.timeout_date ? daysBetween(today(), trade.timeout_date) : null
    const progress = daysHeld !== null && totalDays !== null && totalDays > 0 ? Math.min((daysHeld / totalDays) * 100, 100) : null

    const progressColor = progress === null ? "var(--color-muted)" : progress >= 85 ? "var(--color-danger)" : progress >= 60 ? "var(--color-warning)" : "var(--color-success)"
    const daysLeftUrgent = daysLeft !== null && daysLeft <= 5

    const weight = totalInvested > 0 && trade.invested_value ? (trade.invested_value / totalInvested) * 100 : null

    const stopPrice = trade.state?.["current_stop"] as number | undefined
    const distPct = stopPrice && currentPrice ? ((currentPrice - stopPrice) / currentPrice) * 100 : stopPrice && trade.fill_price ? ((trade.fill_price - stopPrice) / trade.fill_price) * 100 : null
    const distColor = distPct !== null ? (distPct < 3 ? "text-danger" : distPct < 6 ? "text-warning" : "text-secondary") : "text-secondary"

    const pnlBadgeBg = pnlUp === null ? "var(--color-surface2)" : pnlUp ? "rgba(74,222,128,0.1)" : "rgba(248,113,113,0.1)"
    const accentColor = pnlUp === null ? "transparent" : pnlUp ? "var(--color-success)" : "var(--color-danger)"

    return (
        <motion.tr initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: index * 0.05, duration: 0.3 }} className={`group transition-colors border-b border-border ${pnlUp ? "hover:bg-success/3" : "hover:bg-danger/3"}`}>
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
                        <Radio size={9} className="text-success" />₹{currentPrice.toFixed(2)}
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
                    <span className="text-sm font-mono font-semibold text-danger">{stopPrice ? `₹${stopPrice.toFixed(2)}` : "—"}</span>
                    {distPct !== null && <span className={`text-[11px] font-mono ${distColor}`}>{distPct.toFixed(1)}% away</span>}
                </div>
            </td>
            <td className="py-5 pr-8 font-mono text-sm font-semibold text-primary whitespace-nowrap">{formatINR(liveValue, true)}</td>
            <td className="py-5 pr-5">
                <div className="flex flex-col gap-1.5 min-w-[150px]">
                    <div className="flex items-center justify-between gap-2">
                        <span className="text-[11px] font-mono text-muted whitespace-nowrap">{daysHeld !== null ? `${daysHeld}d held` : "—"}</span>
                        <span className={`text-[11px] font-mono font-semibold whitespace-nowrap ${daysLeftUrgent ? "text-danger" : "text-muted"}`}>{daysLeft !== null ? `${daysLeft}d left` : "—"}</span>
                    </div>
                    <div className="h-1.5 rounded-full overflow-hidden bg-border">
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
                if (!stop || !price) return Infinity
                return ((price - stop) / price) * 100
            }
            const da = stopDist(a), db = stopDist(b)
            if (!isFinite(da) && !isFinite(db)) return 0
            return da - db
        }
        const iv = (t: Trade) => t.invested_value ?? (t.fill_price ?? 0) * (t.fill_quantity ?? 0)
        if (sortKey === "invested") return iv(b) - iv(a)
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
                <div className="flex flex-col gap-1.5">
                    <p className="text-xs text-secondary">Positions</p>
                    <h1 className="text-xl font-semibold tracking-tight text-primary leading-none">Holdings</h1>
                </div>
                <div className="flex flex-col items-end gap-0.5 px-4 py-2.5 bg-surface border border-border rounded-[var(--radius-card)]">
                    <span className="text-[11px] text-secondary">Unrealised P&amp;L</span>
                    {isLoading ? <Skeleton className="h-7 w-28" /> : <span className={`text-2xl font-semibold leading-none ${totalPnl >= 0 ? "text-success" : "text-danger"}`}>{formatINR(totalPnl, true)}</span>}
                </div>
            </motion.div>

            {/* Stat strip */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.4, ease }} className="grid grid-cols-3 md:grid-cols-6 gap-2">
                {[
                    { icon: Layers, iconColor: "var(--color-secondary)", label: "Positions", value: isLoading ? "—" : String(count) },
                    { icon: Wallet, iconColor: "var(--color-secondary)", label: "Total Invested", value: isLoading ? "—" : formatINR(totalInvested, true) },
                    { icon: Target, iconColor: "var(--color-success)", label: "In Profit", value: isLoading ? "—" : String(winners), sub: count > 0 ? `${count - winners} at loss` : undefined },
                    { icon: TrendingUp, iconColor: avgReturn !== null && avgReturn < 0 ? "var(--color-danger)" : "var(--color-success)", label: "Avg Return", value: isLoading ? "—" : avgReturn !== null ? `${avgReturn > 0 ? "+" : ""}${avgReturn.toFixed(2)}%` : "—", valueColor: avgReturn !== null ? (avgReturn >= 0 ? "text-success" : "text-danger") : undefined },
                    { icon: TrendingUp, iconColor: "var(--color-success)", label: "Best", value: isLoading ? "—" : bestPnlPct != null ? `${bestPnlPct > 0 ? "+" : ""}${bestPnlPct.toFixed(1)}%` : "—", sub: bestTrade?.security.ticker, valueColor: "text-success" },
                    { icon: TrendingDown, iconColor: "var(--color-danger)", label: "Worst", value: isLoading ? "—" : worstPnlPct != null ? `${worstPnlPct.toFixed(1)}%` : "—", sub: worstTrade?.security.ticker, valueColor: worstPnlPct !== null && worstPnlPct < 0 ? "text-danger" : "text-success" }
                ].map((t) => (
                    <KpiTile key={t.label} {...t} />
                ))}
            </motion.div>

            {/* Sort controls */}
            {!isLoading && trades && trades.length > 1 && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="flex items-center gap-2">
                    <span className="text-[11px] text-muted">Sort by</span>
                    {SORT_OPTIONS.map((opt) => (
                        <button key={opt.key} onClick={() => setSortKey(opt.key)} className={`px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-150 border ${sortKey === opt.key ? "bg-primary text-bg border-primary" : "bg-transparent text-secondary border-border hover:text-primary hover:border-muted"}`}>
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
                    <div className="py-20 text-center rounded-[var(--radius-card)] bg-surface2 border border-border">
                        <TrendingUp size={32} className="text-muted mx-auto mb-4" strokeWidth={1.5} />
                        <p className="text-sm font-medium text-primary mb-1">No open positions</p>
                        <p className="text-xs text-secondary">Trades will appear here once entered</p>
                    </div>
                </motion.div>
            )}
            {!isLoading && sortedTrades.length > 0 && (
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }}>
                    <Card padding="sm">
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr className="border-b border-border">
                                        {["Ticker", "Entry × Qty × Wt", "Current", "P&L", "Stop", "Curr. Value", "Holding Period"].map((h) => (
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
                </motion.div>
            )}
        </div>
    )
}
