"use client"

import { useState } from "react"
import { useSignals } from "@/libraries/hooks/useSignals"
import { useCountUp } from "@/libraries/hooks/useCountUp"
import Skeleton from "@/components/ui/Skeleton"
import HudCorners from "@/components/ui/HudCorners"
import KpiTile from "@/components/ui/KpiTile"
import { motion } from "framer-motion"
import { Zap, CheckCircle, XCircle, TrendingUp, TrendingDown, X } from "lucide-react"
import { Signal } from "@/libraries/types/signal"
import { useRouter } from "next/navigation"
import { pctColor } from "@/libraries/utils/format"

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

const FILTERS = [
    { label: "All", value: undefined },
    { label: "Entered", value: "entered" },
    { label: "Missed", value: "missed" }
]

function PerfValue({ value }: { value: number | null }) {
    if (value === null) return <span className="font-mono text-muted">—</span>
    const up = value >= 0
    const Icon = up ? TrendingUp : TrendingDown
    return (
        <span className={`flex items-center gap-1 font-mono font-semibold whitespace-nowrap ${pctColor(value)}`}>
            <Icon size={11} strokeWidth={2.5} />
            {value > 0 ? "+" : ""}
            {value.toFixed(2)}%
        </span>
    )
}

const COL_HEADERS = ["Ticker", "Strategy", "Sector / Industry", "Signal ₹", "Fill ₹", "Since Signal", "Trade P&L", "Date", "Status"]

function SignalTable({ signals }: { signals: Signal[] }) {
    const router = useRouter()
    return (
        <div className="relative hud-panel">
            <HudCorners opacity={0.3} />
            <div className="overflow-hidden rounded-xl">
                <table className="w-full text-sm border-collapse">
                    <thead>
                        <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
                            {COL_HEADERS.map((h) => (
                                <th key={h} className="py-3 px-4 text-left font-mono text-[10px] font-medium uppercase tracking-[0.15em] text-secondary whitespace-nowrap first:pl-5 last:pr-5 last:text-right">
                                    {h}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody>
                        {signals.map((signal, i) => {
                            const entered = signal.signal_status === "entered"
                            const secLine = [signal.security.sector, signal.security.industry].filter(Boolean).join(" · ")
                            return (
                                <motion.tr key={signal.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03, duration: 0.3 }} className={`group cursor-pointer ${entered ? "hover:bg-green-400/3" : "hover:bg-white/2"}`} style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }} onClick={() => router.push(`/signals/${signal.id}`)}>
                                    {/* Ticker — accent bar lives here as absolute span so it never affects table layout */}
                                    <td className="relative py-3.5 px-4 pl-5 whitespace-nowrap">
                                        <span className="absolute left-0 inset-y-0 w-0.5 rounded-r-sm opacity-0 group-hover:opacity-100 transition-opacity duration-150" style={{ background: "var(--color-accent)" }} />
                                        <div className="flex items-center gap-2">
                                            <span className={entered ? "text-green-400" : "text-muted"}>{entered ? <CheckCircle size={13} strokeWidth={2} /> : <XCircle size={13} strokeWidth={1.5} />}</span>
                                            <span className="font-bold text-primary tracking-tight">{signal.security.ticker}</span>
                                        </div>
                                    </td>

                                    {/* Strategy */}
                                    <td className="py-3.5 px-4 whitespace-nowrap">
                                        <span className="text-xs text-secondary">{signal.strategy_name ?? `Run #${signal.strategy_run_id}`}</span>
                                    </td>

                                    {/* Sector / Industry */}
                                    <td className="py-3.5 px-4">
                                        <span className="text-xs text-secondary whitespace-nowrap">{secLine || "—"}</span>
                                    </td>

                                    {/* Signal ₹ */}
                                    <td className="py-3.5 px-4 whitespace-nowrap">
                                        <span className="font-mono text-primary">{signal.signal_close ? `₹${signal.signal_close.toFixed(2)}` : "—"}</span>
                                    </td>

                                    {/* Fill ₹ */}
                                    <td className="py-3.5 px-4 whitespace-nowrap">
                                        <span className="font-mono text-primary">{signal.trade_fill_price ? `₹${signal.trade_fill_price.toFixed(2)}` : "—"}</span>
                                    </td>

                                    {/* Since Signal */}
                                    <td className="py-3.5 px-4 whitespace-nowrap">
                                        <PerfValue value={signal.perf_since_signal} />
                                    </td>

                                    {/* Trade P&L */}
                                    <td className="py-3.5 px-4 whitespace-nowrap">
                                        <PerfValue value={entered ? signal.trade_pnl_pct : null} />
                                    </td>

                                    {/* Date */}
                                    <td className="py-3.5 px-4 whitespace-nowrap">
                                        <div className="flex flex-col gap-0">
                                            <span className="text-xs font-mono text-secondary">{signal.observed_at.slice(0, 10)}</span>
                                            <span className="text-[11px] font-mono text-muted">{signal.observed_at.slice(11, 16)}</span>
                                        </div>
                                    </td>

                                    {/* Status */}
                                    <td className="py-3.5 px-4 pr-5 text-right whitespace-nowrap">
                                        <span className={`font-mono text-[10px] font-bold uppercase tracking-[0.15em] ${entered ? "text-green-400" : "text-muted"}`}>{signal.signal_status}</span>
                                    </td>
                                </motion.tr>
                            )
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    )
}

export default function SignalsPage() {
    const [status, setStatus] = useState<string | undefined>(undefined)
    const [strategy, setStrategy] = useState<string | undefined>(undefined)

    // Separate display state from applied (query) state to avoid flicker while typing dates
    const [inputFrom, setInputFrom] = useState("")
    const [inputTo, setInputTo] = useState("")
    const [appliedFrom, setAppliedFrom] = useState("")
    const [appliedTo, setAppliedTo] = useState("")

    const { data: signals, isLoading } = useSignals({ status, date_from: appliedFrom || undefined, date_to: appliedTo || undefined, strategy })

    const all = signals ?? []

    // Strategy options derived from all loaded signals (unfiltered by strategy so pills don't disappear)
    const { data: allSignalsForStrategies } = useSignals({ date_from: appliedFrom || undefined, date_to: appliedTo || undefined })
    const strategyOptions = Array.from(new Set((allSignalsForStrategies ?? []).map((s) => s.strategy_name).filter(Boolean))) as string[]

    const entered = all.filter((s) => s.signal_status === "entered").length
    const missed = all.filter((s) => s.signal_status === "missed").length
    const hitRateRaw = all.length > 0 ? Math.round((entered / all.length) * 100) : 0
    const hitRate = all.length > 0 ? String(hitRateRaw) : null
    const hitRateAnimated = useCountUp(hitRateRaw)

    const missedWithPerf = all.filter((s) => s.signal_status === "missed" && s.perf_since_signal !== null)
    const avgMissedPerf = missedWithPerf.length > 0 ? missedWithPerf.reduce((s, x) => s + (x.perf_since_signal ?? 0), 0) / missedWithPerf.length : null

    const clearDates = () => {
        setInputFrom("")
        setInputTo("")
        setAppliedFrom("")
        setAppliedTo("")
    }

    return (
        <div className="flex flex-col gap-6">
            {/* Hero */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between">
                <div>
                    <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-secondary mb-1">Strategy</p>
                    <h1 className="text-4xl font-bold tracking-tight text-primary leading-none">Signals</h1>
                </div>
                <div className="relative flex flex-col items-end gap-1 px-5 py-4 hud-panel">
                    <HudCorners opacity={0.35} />
                    <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-secondary">Hit Rate</span>
                    {isLoading ? <Skeleton className="h-12 w-24" /> : <span className="text-5xl font-bold font-mono leading-none text-accent accent-glow">{hitRate !== null ? `${Math.round(hitRateAnimated)}%` : "—"}</span>}
                </div>
            </motion.div>

            {/* Stat strip */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.4, ease }} className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {[
                    { icon: Zap, iconColor: "var(--color-accent)", label: "Total Signals", value: isLoading ? "—" : String(all.length) },
                    { icon: CheckCircle, iconColor: "#4ade80", label: "Entered", value: isLoading ? "—" : String(entered), valueColor: "text-green-400" },
                    { icon: XCircle, iconColor: "var(--color-secondary)", label: "Missed", value: isLoading ? "—" : String(missed) },
                    {
                        icon: avgMissedPerf !== null && avgMissedPerf < 0 ? TrendingDown : TrendingUp,
                        iconColor: avgMissedPerf !== null && avgMissedPerf < 0 ? "#f87171" : "#4ade80",
                        label: "Avg Missed Perf",
                        value: isLoading ? "—" : avgMissedPerf !== null ? `${avgMissedPerf > 0 ? "+" : ""}${avgMissedPerf.toFixed(1)}%` : "—",
                        valueColor: avgMissedPerf !== null ? pctColor(avgMissedPerf) : undefined
                    }
                ].map((t) => (
                    <KpiTile key={t.label} {...t} />
                ))}
            </motion.div>

            {/* Filters */}
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2, duration: 0.3 }} className="flex flex-col gap-2">
                {/* Row 1: Status + Strategy + Date range */}
                <div className="flex items-center justify-between gap-4">
                    <div className="flex items-center gap-3">
                        {/* Status pills */}
                        <div className="flex gap-1.5">
                            {FILTERS.map((f) => (
                                <button key={f.label} onClick={() => setStatus(f.value)} className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-150 border ${status === f.value ? "bg-accent/10 text-accent border-accent/30" : "bg-transparent text-secondary border-white/8 hover:text-primary hover:border-white/20"}`}>
                                    {f.label}
                                </button>
                            ))}
                        </div>

                        {/* Strategy pills — only shown when multiple strategies exist */}
                        {strategyOptions.length > 1 && (
                            <>
                                <div className="w-px h-4" style={{ background: "rgba(255,255,255,0.08)" }} />
                                <div className="flex gap-1.5">
                                    <button onClick={() => setStrategy(undefined)} className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-150 border ${strategy === undefined ? "bg-accent/10 text-accent border-accent/30" : "bg-transparent text-secondary border-white/8 hover:text-primary hover:border-white/20"}`}>
                                        All strategies
                                    </button>
                                    {strategyOptions.map((s) => (
                                        <button key={s} onClick={() => setStrategy(s)} className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-150 border ${strategy === s ? "bg-accent/10 text-accent border-accent/30" : "bg-transparent text-secondary border-white/8 hover:text-primary hover:border-white/20"}`}>
                                            {s}
                                        </button>
                                    ))}
                                </div>
                            </>
                        )}
                    </div>

                    {/* Date range — applies on blur to avoid flicker */}
                    <div className="flex items-center gap-2">
                        <input type="date" value={inputFrom} onChange={(e) => setInputFrom(e.target.value)} onBlur={(e) => setAppliedFrom(e.target.value)} className="px-3 py-1.5 rounded-lg text-xs font-mono text-secondary border border-white/8 bg-transparent hover:border-white/20 focus:border-accent/40 focus:outline-none transition-colors" style={{ colorScheme: "dark" }} />
                        <span className="text-[10px] text-muted">to</span>
                        <input type="date" value={inputTo} onChange={(e) => setInputTo(e.target.value)} onBlur={(e) => setAppliedTo(e.target.value)} className="px-3 py-1.5 rounded-lg text-xs font-mono text-secondary border border-white/8 bg-transparent hover:border-white/20 focus:border-accent/40 focus:outline-none transition-colors" style={{ colorScheme: "dark" }} />
                        {(appliedFrom || appliedTo) && (
                            <button onClick={clearDates} className="flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] text-muted border border-white/8 hover:text-primary hover:border-white/20 transition-all">
                                <X size={10} />
                                Clear
                            </button>
                        )}
                    </div>
                </div>
            </motion.div>

            {/* Signal table */}
            {isLoading && (
                <div className="flex flex-col gap-2">
                    {[...Array(8)].map((_, i) => (
                        <Skeleton key={i} className="h-12 rounded-xl" />
                    ))}
                </div>
            )}
            {!isLoading && all.length === 0 && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <div className="py-20 text-center rounded-2xl bg-surface2 border border-white/4">
                        <Zap size={32} className="text-muted mx-auto mb-4" strokeWidth={1.5} />
                        <p className="text-sm font-medium text-primary mb-1">No signals found</p>
                        <p className="text-xs text-secondary">Signals will appear once the strategy runs</p>
                    </div>
                </motion.div>
            )}
            {!isLoading && all.length > 0 && <SignalTable signals={all} />}
        </div>
    )
}
