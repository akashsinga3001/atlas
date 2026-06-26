"use client"

import { useState } from "react"
import { useSignals } from "@/libraries/hooks/useSignals"
import PageHeader from "@/components/layout/PageHeader"
import Card from "@/components/ui/Card"
import Badge from "@/components/ui/Badge"
import Skeleton from "@/components/ui/Skeleton"
import EmptyState from "@/components/ui/EmptyState"
import { Zap } from "lucide-react"

const STATUS_OPTIONS = [
    { label: "All", value: undefined },
    { label: "Entered", value: "entered" },
    { label: "Missed", value: "missed" }
]

export default function SignalsPage() {
    const [status, setStatus] = useState<string | undefined>(undefined)
    const { data: signals, isLoading, isError } = useSignals({ status })

    return (
        <div>
            <PageHeader title="Signals" subtitle="All strategy signals" />

            {/* Filters */}
            <div className="flex gap-2 mb-6">
                {STATUS_OPTIONS.map((opt) => (
                    <button key={opt.label} onClick={() => setStatus(opt.value)} className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${status === opt.value ? "bg-accent/10 text-accent border-accent/30" : "bg-surface border-border text-secondary hover:text-primary"}`}>
                        {opt.label}
                    </button>
                ))}
            </div>

            <Card>
                {isLoading && (
                    <div className="flex flex-col gap-3 p-2">
                        {[...Array(8)].map((_, i) => (
                            <Skeleton key={i} className="h-12 w-full" />
                        ))}
                    </div>
                )}
                {isError && <EmptyState icon={Zap} title="Failed to load signals" description="Check that the backend is running" />}
                {!isLoading && !isError && signals?.length === 0 && <EmptyState icon={Zap} title="No signals found" description="Signals will appear once the strategy runs" />}
                {!isLoading && !isError && signals && signals.length > 0 && (
                    <table className="w-full text-sm">
                        <thead>
                            <tr className="border-b border-border text-left">
                                {["Date", "Ticker", "Sector", "Status", "Entry Price"].map((h) => (
                                    <th key={h} className="pb-3 pr-6 text-xs text-secondary uppercase tracking-wider font-medium">
                                        {h}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {signals.map((signal) => (
                                <tr key={signal.id} className="border-b border-border last:border-0 hover:bg-surface2 transition-colors">
                                    <td className="py-3 pr-6 text-secondary font-mono">{signal.observed_at.slice(0, 10)}</td>
                                    <td className="py-3 pr-6 font-medium text-primary">{signal.security.ticker}</td>
                                    <td className="py-3 pr-6 text-secondary text-xs">{signal.security.sector ?? "—"}</td>
                                    <td className="py-3 pr-6">
                                        <Badge label={signal.signal_status} variant={signal.signal_status === "entered" ? "green" : "muted"} />
                                    </td>
                                    <td className="py-3 pr-6 font-mono text-secondary">{signal.trade_fill_price ? `₹${signal.trade_fill_price.toFixed(2)}` : "—"}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}
            </Card>
        </div>
    )
}
