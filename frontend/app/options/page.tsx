"use client"

import { useOptionsPositions } from "@/libraries/hooks/useOptionsPositions"
import { useLivePnL } from "@/libraries/hooks/useLivePnL"
import Skeleton from "@/components/ui/Skeleton"
import Card from "@/components/ui/Card"
import HudCorners from "@/components/ui/HudCorners"
import KpiTile from "@/components/ui/KpiTile"
import { motion } from "framer-motion"
import { Radio, Layers, Wallet, Coins, Target, TrendingUp, TrendingDown } from "lucide-react"
import { OptionsPosition, OptionsLeg, OptionsLegRole } from "@/libraries/types/options"
import { formatINR, pctColor } from "@/libraries/utils/format"

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

const ACTIVE_STATUSES = ["pending", "open", "closing"]
const HISTORY_STATUSES = ["closed", "failed", "skipped"]

const STATUS_STYLE: Record<string, { bg: string; text: string; label: string }> = {
    pending: { bg: "rgba(251,191,36,0.1)", text: "text-amber-400", label: "Pending" },
    open: { bg: "rgba(74,222,128,0.1)", text: "text-green-400", label: "Open" },
    closing: { bg: "rgba(96,165,250,0.1)", text: "text-blue-400", label: "Closing" },
    closed: { bg: "rgba(255,255,255,0.05)", text: "text-secondary", label: "Closed" },
    failed: { bg: "rgba(248,113,113,0.1)", text: "text-red-400", label: "Failed" },
    skipped: { bg: "rgba(255,255,255,0.04)", text: "text-muted", label: "Skipped" }
}

const ROLE_LABEL: Record<OptionsLegRole, string> = {
    short_call: "Short Call",
    short_put: "Short Put",
    long_call: "Long Call",
    long_put: "Long Put"
}

function isShortRole(role: OptionsLegRole) {
    return role === "short_call" || role === "short_put"
}

function daysBetween(a: string, b: string) {
    return Math.floor((new Date(b).getTime() - new Date(a).getTime()) / 86400000)
}

function today() {
    return new Date().toISOString().slice(0, 10)
}

function legPnl(leg: OptionsLeg, livePrice: number | null | undefined): number | null {
    if (leg.status !== "open" || leg.entry_fill_price === null || !leg.entry_fill_quantity) return null
    const current = livePrice ?? leg.entry_fill_price
    return isShortRole(leg.role) ? (leg.entry_fill_price - current) * leg.entry_fill_quantity : (current - leg.entry_fill_price) * leg.entry_fill_quantity
}

function positionUnrealizedPnl(position: OptionsPosition, liveQuotes: Record<string, { last_price: number | null }>): number | null {
    const openLegs = position.legs.filter((l) => l.status === "open")
    if (openLegs.length === 0) return null
    let total = 0
    for (const leg of openLegs) {
        const pnl = legPnl(leg, liveQuotes[leg.ticker]?.last_price)
        if (pnl === null) return null
        total += pnl
    }
    return total
}

function StatusBadge({ status }: { status: string }) {
    const s = STATUS_STYLE[status] ?? STATUS_STYLE.pending
    return (
        <span className={`inline-flex items-center px-2.5 py-1 rounded-full text-[10px] font-mono font-semibold uppercase tracking-wider ${s.text}`} style={{ background: s.bg }}>
            {s.label}
        </span>
    )
}

function StrikeRail({ position }: { position: OptionsPosition }) {
    const rungs = [
        { label: "Long Put", value: position.put_long_strike },
        { label: "Short Put", value: position.put_short_strike },
        { label: "Spot @ Signal", value: position.spot_at_signal, accent: true },
        { label: "Short Call", value: position.call_short_strike },
        { label: "Long Call", value: position.call_long_strike }
    ]
    return (
        <div className="grid grid-cols-5 gap-1.5">
            {rungs.map((r) => (
                <div key={r.label} className="flex flex-col items-center gap-1 rounded-lg py-2.5 px-1" style={{ background: r.accent ? "rgba(var(--color-accent-rgb,255,255,255),0.06)" : "rgba(255,255,255,0.03)", border: r.accent ? "1px solid rgba(255,255,255,0.12)" : "1px solid transparent" }}>
                    <span className="text-[9px] font-mono uppercase tracking-wider text-muted text-center">{r.label}</span>
                    <span className={`text-sm font-mono font-bold ${r.accent ? "text-accent" : "text-primary"}`}>{r.value !== null ? r.value.toFixed(0) : "—"}</span>
                </div>
            ))}
        </div>
    )
}

function LegRow({ leg, livePrice }: { leg: OptionsLeg; livePrice: number | null | undefined }) {
    const pnl = legPnl(leg, livePrice)
    const short = isShortRole(leg.role)
    return (
        <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
            <td className="py-2.5 pr-4">
                <span className={`text-xs font-semibold ${short ? "text-red-400" : "text-green-400"}`}>{ROLE_LABEL[leg.role]}</span>
            </td>
            <td className="py-2.5 pr-4 font-mono text-xs text-secondary whitespace-nowrap">{leg.ticker}</td>
            <td className="py-2.5 pr-4 font-mono text-xs text-primary whitespace-nowrap">{leg.entry_fill_price !== null ? `₹${leg.entry_fill_price.toFixed(2)}` : "—"}</td>
            <td className="py-2.5 pr-4 font-mono text-xs whitespace-nowrap">
                {livePrice ? (
                    <span className="inline-flex items-center gap-1 text-primary font-semibold">
                        <Radio size={8} className="text-green-400 live-pulse" />₹{livePrice.toFixed(2)}
                    </span>
                ) : (
                    <span className="text-muted">—</span>
                )}
            </td>
            <td className={`py-2.5 pr-4 font-mono text-xs font-semibold whitespace-nowrap ${pctColor(pnl)}`}>{pnl !== null ? formatINR(pnl, true) : "—"}</td>
            <td className="py-2.5">
                <StatusBadge status={leg.status} />
            </td>
        </tr>
    )
}

function ActivePositionCard({ position, index, liveQuotes }: { position: OptionsPosition; index: number; liveQuotes: Record<string, { last_price: number | null }> }) {
    const unrealized = positionUnrealizedPnl(position, liveQuotes)
    const daysToExpiry = position.expiry_date ? daysBetween(today(), position.expiry_date) : null
    const daysToPlannedExit = position.planned_exit_date ? daysBetween(today(), position.planned_exit_date) : null

    return (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.06, duration: 0.35, ease }}>
            <Card padding="md" className="relative hud-panel">
                <HudCorners opacity={0.3} />
                <div className="flex items-start justify-between mb-4 flex-wrap gap-2">
                    <div className="flex items-center gap-3">
                        <StatusBadge status={position.status} />
                        <span className="text-sm font-bold text-primary">Expiry {position.expiry_date ?? "—"}</span>
                        {daysToExpiry !== null && <span className="text-[11px] font-mono text-muted">{daysToExpiry}d to expiry</span>}
                    </div>
                    <div className="flex items-center gap-4">
                        <span className="text-[11px] font-mono text-secondary">
                            {position.lots ?? "—"} lot{position.lots === 1 ? "" : "s"} × {position.lot_size ?? "—"}
                        </span>
                        {unrealized !== null && (
                            <span className={`text-base font-bold font-mono ${pctColor(unrealized)}`}>{formatINR(unrealized, true)}</span>
                        )}
                    </div>
                </div>

                <StrikeRail position={position} />

                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4">
                    {[
                        { label: "Net Credit / Lot", value: position.net_credit_per_lot !== null ? formatINR(position.net_credit_per_lot) : "—" },
                        { label: "Margin / Lot", value: position.margin_per_lot !== null ? formatINR(position.margin_per_lot) : "—" },
                        { label: "Planned Exit", value: position.planned_exit_date ?? "—", sub: daysToPlannedExit !== null ? `${daysToPlannedExit}d left` : undefined },
                        { label: "Net Credit Total", value: position.net_credit_total !== null ? formatINR(position.net_credit_total, true) : "—" }
                    ].map((m) => (
                        <div key={m.label} className="flex flex-col gap-0.5">
                            <span className="text-[9px] font-mono uppercase tracking-wider text-muted">{m.label}</span>
                            <span className="text-xs font-mono font-semibold text-primary">{m.value}</span>
                            {m.sub && <span className="text-[10px] font-mono text-muted">{m.sub}</span>}
                        </div>
                    ))}
                </div>

                <div className="overflow-x-auto mt-5">
                    <table className="w-full">
                        <thead>
                            <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                                {["Leg", "Ticker", "Entry", "Live", "Leg P&L", "Status"].map((h) => (
                                    <th key={h} className="pb-2 pr-4 font-mono text-[9px] text-secondary uppercase tracking-wider font-medium text-left whitespace-nowrap">
                                        {h}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {position.legs.map((leg) => (
                                <LegRow key={leg.id} leg={leg} livePrice={liveQuotes[leg.ticker]?.last_price} />
                            ))}
                        </tbody>
                    </table>
                </div>
            </Card>
        </motion.div>
    )
}

function HistoryRow({ position, index }: { position: OptionsPosition; index: number }) {
    return (
        <motion.tr initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: index * 0.03, duration: 0.3 }} style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
            <td className="py-3.5 pr-6 pl-5">
                <StatusBadge status={position.status} />
            </td>
            <td className="py-3.5 pr-6 font-mono text-xs text-secondary whitespace-nowrap">{position.entry_date}</td>
            <td className="py-3.5 pr-6 font-mono text-xs text-secondary whitespace-nowrap">{position.exit_date ?? "—"}</td>
            <td className="py-3.5 pr-6 font-mono text-xs text-secondary whitespace-nowrap">{position.expiry_date ?? "—"}</td>
            <td className="py-3.5 pr-6 font-mono text-xs text-secondary whitespace-nowrap">{position.lots ?? "—"}</td>
            <td className="py-3.5 pr-6 text-xs text-secondary max-w-[220px] truncate">{position.exit_reason ?? position.skip_reason ?? "—"}</td>
            <td className={`py-3.5 pr-5 font-mono text-xs font-semibold whitespace-nowrap ${pctColor(position.realized_pnl)}`}>{position.realized_pnl !== null ? formatINR(position.realized_pnl, true) : "—"}</td>
        </motion.tr>
    )
}

export default function OptionsPage() {
    const { data: positions, isLoading } = useOptionsPositions()

    const activePositions = (positions ?? []).filter((p) => ACTIVE_STATUSES.includes(p.status))
    const historyPositions = (positions ?? []).filter((p) => HISTORY_STATUSES.includes(p.status))

    const legTickers = activePositions.flatMap((p) => p.legs.filter((l) => l.status === "open").map((l) => l.ticker))
    const liveQuotes = useLivePnL(legTickers)

    const totalLots = activePositions.reduce((s, p) => s + (p.lots ?? 0), 0)
    const totalMargin = activePositions.reduce((s, p) => s + (p.margin_total ?? 0), 0)
    const totalNetCredit = activePositions.reduce((s, p) => s + (p.net_credit_total ?? 0), 0)
    const liveUnrealized = activePositions.reduce((s, p) => {
        const pnl = positionUnrealizedPnl(p, liveQuotes)
        return s + (pnl ?? 0)
    }, 0)

    const closedPositions = historyPositions.filter((p) => p.status === "closed" && p.realized_pnl !== null)
    const totalRealized = closedPositions.reduce((s, p) => s + (p.realized_pnl ?? 0), 0)
    const wins = closedPositions.filter((p) => (p.realized_pnl ?? 0) > 0).length
    const winRate = closedPositions.length > 0 ? (wins / closedPositions.length) * 100 : null

    return (
        <div className="flex flex-col gap-6">
            {/* Hero */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between flex-wrap gap-4">
                <div>
                    <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-secondary mb-1">Positions</p>
                    <h1 className="text-4xl font-bold tracking-tight text-primary leading-none">Options</h1>
                    <p className="text-xs text-secondary mt-2">NIFTY Iron Condor</p>
                </div>
                <div className="relative flex flex-col items-end gap-1 px-5 py-4 hud-panel">
                    <HudCorners opacity={0.35} />
                    <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-secondary">Live Unrealised P&amp;L</span>
                    {isLoading ? <Skeleton className="h-12 w-36" /> : <span className={`text-5xl font-bold font-mono leading-none ${liveUnrealized >= 0 ? "text-green-400" : "text-red-400"}`}>{formatINR(liveUnrealized, true)}</span>}
                </div>
            </motion.div>

            {/* Stat strip */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.4, ease }} className="grid grid-cols-3 md:grid-cols-6 gap-2">
                {[
                    { icon: Layers, iconColor: "var(--color-accent)", label: "Active", value: isLoading ? "—" : String(activePositions.length) },
                    { icon: Coins, iconColor: "var(--color-accent)", label: "Total Lots", value: isLoading ? "—" : String(totalLots) },
                    { icon: Wallet, iconColor: "var(--color-accent)", label: "Margin Deployed", value: isLoading ? "—" : formatINR(totalMargin, true) },
                    { icon: Wallet, iconColor: "#4ade80", label: "Net Credit Open", value: isLoading ? "—" : formatINR(totalNetCredit, true) },
                    { icon: Target, iconColor: winRate !== null && winRate < 50 ? "#f87171" : "#4ade80", label: "Win Rate (Closed)", value: isLoading ? "—" : winRate !== null ? `${winRate.toFixed(0)}%` : "—", sub: closedPositions.length > 0 ? `${wins}/${closedPositions.length}` : undefined },
                    { icon: totalRealized >= 0 ? TrendingUp : TrendingDown, iconColor: totalRealized >= 0 ? "#4ade80" : "#f87171", label: "Realized P&L", value: isLoading ? "—" : formatINR(totalRealized, true), valueColor: pctColor(totalRealized) }
                ].map((t) => (
                    <KpiTile key={t.label} {...t} />
                ))}
            </motion.div>

            {/* Active positions */}
            {isLoading && (
                <div className="flex flex-col gap-3">
                    {[...Array(2)].map((_, i) => (
                        <Skeleton key={i} className="h-64 rounded-2xl" />
                    ))}
                </div>
            )}

            {!isLoading && activePositions.length === 0 && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>
                    <div className="py-20 text-center rounded-2xl bg-surface2 border border-white/4">
                        <TrendingUp size={32} className="text-muted mx-auto mb-4" strokeWidth={1.5} />
                        <p className="text-sm font-medium text-primary mb-1">No active iron condor</p>
                        <p className="text-xs text-secondary">A position will appear here once the week's entry fills</p>
                    </div>
                </motion.div>
            )}

            {!isLoading && activePositions.length > 0 && (
                <div className="flex flex-col gap-4">
                    {activePositions.map((position, i) => (
                        <ActivePositionCard key={position.id} position={position} index={i} liveQuotes={liveQuotes} />
                    ))}
                </div>
            )}

            {/* History */}
            {!isLoading && historyPositions.length > 0 && (
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex flex-col gap-3">
                    <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-secondary">History</span>
                    <Card padding="sm" className="relative hud-panel">
                        <HudCorners opacity={0.3} />
                        <div className="overflow-x-auto">
                            <table className="w-full text-sm">
                                <thead>
                                    <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                                        {["Status", "Entry", "Exit", "Expiry", "Lots", "Reason", "Realized P&L"].map((h) => (
                                            <th key={h} className="py-3 pr-6 first:pl-5 font-mono text-[10px] text-secondary uppercase tracking-[0.15em] font-medium text-left whitespace-nowrap">
                                                {h}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {historyPositions.map((position, i) => (
                                        <HistoryRow key={position.id} position={position} index={i} />
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
