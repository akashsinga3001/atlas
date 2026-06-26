"use client"

import { useState } from "react"
import { useSignals } from "@/libraries/hooks/useSignals"
import Skeleton from "@/components/ui/Skeleton"
import { motion } from "framer-motion"
import { Zap, CheckCircle, XCircle } from "lucide-react"
import { Signal } from "@/libraries/types/signal"

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

const FILTERS = [
    { label: "All", value: undefined },
    { label: "Entered", value: "entered" },
    { label: "Missed", value: "missed" }
]

function SignalCard({ signal, index }: { signal: Signal; index: number }) {
    const entered = signal.signal_status === "entered"

    return (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: index * 0.04, duration: 0.35, ease }}>
            <div className={`flex items-center justify-between gap-6 px-5 py-4 rounded-xl border transition-colors ${entered ? "bg-green-400/[0.03] border-green-400/10 hover:border-green-400/20" : "bg-surface2 border-white/4 hover:border-white/8"}`}>

                {/* Status icon */}
                <div className={`shrink-0 ${entered ? "text-green-400" : "text-muted"}`}>
                    {entered ? <CheckCircle size={16} strokeWidth={2} /> : <XCircle size={16} strokeWidth={1.5} />}
                </div>

                {/* Ticker + company */}
                <div className="flex flex-col gap-0.5 w-40 shrink-0">
                    <span className="text-base font-bold text-primary tracking-tight">{signal.security.ticker}</span>
                    <span className="text-[11px] text-muted truncate">{signal.security.display_name}</span>
                </div>

                {/* Sector */}
                <span className="text-xs text-secondary flex-1">{signal.security.sector ?? "—"}</span>

                {/* Entry price */}
                <div className="flex flex-col items-end gap-0.5 shrink-0">
                    <span className="text-[10px] uppercase tracking-[0.1em] text-secondary">Entry</span>
                    <span className="text-sm font-mono font-semibold text-primary">{signal.trade_fill_price ? `₹${signal.trade_fill_price.toFixed(2)}` : "—"}</span>
                </div>

                {/* Time */}
                <div className="flex flex-col items-end gap-0.5 shrink-0">
                    <span className="text-xs font-mono text-muted">{signal.observed_at.slice(0, 10)}</span>
                    <span className="text-[11px] font-mono text-muted">{signal.observed_at.slice(11, 16)}</span>
                </div>

                {/* Status label */}
                <div className={`shrink-0 text-[10px] font-bold uppercase tracking-[0.15em] w-16 text-right ${entered ? "text-green-400" : "text-muted"}`}>
                    {signal.signal_status}
                </div>
            </div>
        </motion.div>
    )
}

export default function SignalsPage() {
    const [status, setStatus] = useState<string | undefined>(undefined)
    const { data: signals, isLoading } = useSignals({ status })

    const all = signals ?? []
    const entered = all.filter(s => s.signal_status === "entered").length
    const missed = all.filter(s => s.signal_status === "missed").length
    const hitRate = all.length > 0 ? ((entered / all.length) * 100).toFixed(0) : null

    return (
        <div className="flex flex-col gap-6">

            {/* Hero */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between">
                <div>
                    <p className="text-[10px] uppercase tracking-[0.2em] text-secondary mb-1">Strategy</p>
                    <h1 className="text-4xl font-bold tracking-tight text-primary leading-none">Signals</h1>
                </div>
                <div className="flex flex-col items-end gap-1">
                    <span className="text-[10px] uppercase tracking-[0.15em] text-secondary">Hit Rate</span>
                    {isLoading
                        ? <Skeleton className="h-12 w-24" />
                        : <span className="text-5xl font-bold font-mono leading-none text-accent">{hitRate !== null ? `${hitRate}%` : "—"}</span>
                    }
                </div>
            </motion.div>

            {/* Stat strip */}
            <div className="grid grid-cols-3 gap-3">
                {[
                    { label: "Total Signals", value: isLoading ? "—" : String(all.length) },
                    { label: "Entered", value: isLoading ? "—" : String(entered), color: "text-green-400" },
                    { label: "Missed", value: isLoading ? "—" : String(missed) }
                ].map(({ label, value, color }, i) => (
                    <motion.div key={label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07, duration: 0.4, ease }}>
                        <div className="flex flex-col gap-1.5 px-5 py-4 rounded-xl bg-surface2 border border-white/4">
                            <span className="text-[10px] uppercase tracking-[0.15em] text-secondary font-medium">{label}</span>
                            <span className={`text-2xl font-bold font-mono leading-none ${color ?? "text-primary"}`}>{value}</span>
                        </div>
                    </motion.div>
                ))}
            </div>

            {/* Filters */}
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2, duration: 0.3 }} className="flex gap-2">
                {FILTERS.map(f => (
                    <button key={f.label} onClick={() => setStatus(f.value)} className={`px-4 py-1.5 rounded-full text-xs font-medium transition-all duration-150 border ${status === f.value ? "bg-accent/10 text-accent border-accent/30" : "bg-transparent text-secondary border-white/8 hover:text-primary hover:border-white/20"}`}>
                        {f.label}
                    </button>
                ))}
            </motion.div>

            {/* Signal list */}
            <div className="flex flex-col gap-2">
                {isLoading && [...Array(8)].map((_, i) => <Skeleton key={i} className="h-16 rounded-xl" />)}
                {!isLoading && all.length === 0 && (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                        <div className="py-20 text-center rounded-2xl bg-surface2 border border-white/4">
                            <Zap size={32} className="text-muted mx-auto mb-4" strokeWidth={1.5} />
                            <p className="text-sm font-medium text-primary mb-1">No signals found</p>
                            <p className="text-xs text-secondary">Signals will appear once the strategy runs</p>
                        </div>
                    </motion.div>
                )}
                {!isLoading && all.map((signal, i) => <SignalCard key={signal.id} signal={signal} index={i} />)}
            </div>
        </div>
    )
}
