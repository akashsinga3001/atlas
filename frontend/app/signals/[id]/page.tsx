"use client"

import { use } from "react"
import { useQuery } from "@tanstack/react-query"
import { getSignalPerformance, SignalForwardDataPoint } from "@/libraries/api/signals"
import Skeleton from "@/components/ui/Skeleton"
import Badge from "@/components/ui/Badge"
import Card from "@/components/ui/Card"
import { motion } from "framer-motion"
import { ArrowLeft, TrendingUp, TrendingDown, Minus, AlertTriangle, CheckCircle } from "lucide-react"
import Link from "next/link"
import { AreaChart, Area, Line, ComposedChart, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, ReferenceDot } from "recharts"
import { formatINR, pctColor } from "@/libraries/utils/format"

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

function fmtPct(v: number | null | undefined): string {
    if (v == null) return "—"
    return `${v > 0 ? "+" : ""}${v.toFixed(2)}%`
}

function PerfValue({ value }: { value: number | null | undefined }) {
    if (value == null) return <span className="font-mono text-muted">—</span>
    const up = value >= 0
    const Icon = up ? TrendingUp : TrendingDown
    return (
        <span className={`flex items-center gap-1 font-mono font-bold ${pctColor(value)}`}>
            <Icon size={13} strokeWidth={2.5} />
            {fmtPct(value)}
        </span>
    )
}

const ChartTooltip = ({ active, payload, label }: { active?: boolean; payload?: { name: string; value: number; color: string }[]; label?: string }) => {
    if (!active || !payload?.length) return null
    return (
        <div className="rounded-[var(--radius-card)] px-3 py-2.5 text-xs flex flex-col gap-1.5" style={{ background: "var(--color-tooltip)", border: "1px solid var(--color-border)", boxShadow: "var(--shadow-large)" }}>
            <div className="font-mono text-secondary mb-0.5">{label}</div>
            {payload.map((p) => (
                <div key={p.name} className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ background: p.color }} />
                    <span className="text-secondary capitalize">{p.name === "close" ? "Close" : "Stop"}</span>
                    <span className="font-mono font-semibold text-primary ml-auto pl-4">{formatINR(p.value)}</span>
                </div>
            ))}
        </div>
    )
}

function ForwardChart({ data, simulated, fillPrice }: { data: SignalForwardDataPoint[]; simulated: boolean; fillPrice: number | null }) {
    const exitIdx = data.findIndex((d) => d.exit_triggered)
    const exitPoint = exitIdx >= 0 ? data[exitIdx] : null

    return (
        <Card padding="md" className="flex flex-col gap-4">
            <div className="flex items-center justify-between">
                <div className="flex flex-col gap-0.5">
                    <span className="text-xs font-medium text-secondary">Forward Price</span>
                    {simulated && (
                        <span className="text-[10px] text-warning/80 flex items-center gap-1">
                            <AlertTriangle size={9} strokeWidth={2} />
                            Simulated ATR stop — no trade was entered
                        </span>
                    )}
                </div>
                <div className="flex items-center gap-3 text-[10px] text-secondary">
                    <span className="flex items-center gap-1.5">
                        <span className="w-3 h-0.5 rounded-full bg-primary inline-block" />
                        Close
                    </span>
                    <span className="flex items-center gap-1.5">
                        <span className="w-3 h-0.5 rounded-full bg-danger inline-block" />
                        Stop level
                    </span>
                    {fillPrice && (
                        <span className="flex items-center gap-1.5">
                            <span className="w-3 h-0.5 rounded-full bg-success/50 inline-block border-dashed" />
                            Entry
                        </span>
                    )}
                </div>
            </div>
            <div style={{ height: 300 }}>
                <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                        <defs>
                            <linearGradient id="closeGrad" x1="0" y1="0" x2="0" y2="1">
                                <stop offset="0%" stopColor="var(--color-primary)" stopOpacity={0.15} />
                                <stop offset="100%" stopColor="var(--color-primary)" stopOpacity={0} />
                            </linearGradient>
                        </defs>
                        <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--color-secondary)" }} tickLine={false} axisLine={false} tickFormatter={(v) => v?.slice(5)} interval="preserveStartEnd" />
                        <YAxis tick={{ fontSize: 10, fill: "var(--color-secondary)" }} tickLine={false} axisLine={false} tickFormatter={(v) => `₹${v.toFixed(0)}`} width={64} domain={["auto", "auto"]} />
                        <Tooltip content={<ChartTooltip />} />
                        {fillPrice && <ReferenceLine y={fillPrice} stroke="var(--color-success)" strokeOpacity={0.6} strokeDasharray="6 3" />}
                        <Area type="monotone" dataKey="close" stroke="var(--color-primary)" strokeWidth={2} fill="url(#closeGrad)" dot={false} connectNulls />
                        <Line type="monotone" dataKey="stop_price" stroke="var(--color-danger)" strokeWidth={1.5} strokeDasharray="4 3" dot={false} connectNulls />
                        {exitPoint && <ReferenceDot x={exitPoint.date} y={exitPoint.close} r={5} fill="var(--color-danger)" stroke="var(--color-danger)" strokeWidth={2} />}
                    </ComposedChart>
                </ResponsiveContainer>
            </div>
        </Card>
    )
}

export default function SignalPerformancePage({ params }: { params: Promise<{ id: string }> }) {
    const { id } = use(params)
    const signalId = Number(id)

    const { data, isLoading, isError } = useQuery({
        queryKey: ["signal-performance", signalId],
        queryFn: () => getSignalPerformance(signalId),
        enabled: !isNaN(signalId)
    })

    const signal = data?.signal
    const summary = data?.summary
    const forwardData = data?.forward_data ?? []
    const entered = signal?.signal_status === "entered"

    if (isLoading) {
        return (
            <div className="flex flex-col gap-5">
                <Skeleton className="h-12 w-64" />
                <Skeleton className="h-8 w-full" />
                <Skeleton className="h-80 w-full rounded-2xl" />
            </div>
        )
    }

    if (isError || !data) {
        return (
            <div className="py-24 text-center">
                <p className="text-sm font-medium text-primary mb-1">Signal not found</p>
                <Link href="/signals" className="text-xs text-secondary hover:text-primary transition-colors">
                    ← Back to signals
                </Link>
            </div>
        )
    }

    const pnlUp = summary?.perf_since_signal != null ? summary.perf_since_signal >= 0 : null
    const tradePnlUp = summary?.trade_pnl_pct != null ? summary.trade_pnl_pct >= 0 : null

    const statItems = [
        { label: "Signal Close", value: formatINR(summary?.signal_close) },
        { label: "Latest Close", value: formatINR(summary?.latest_close) },
        { label: "Since Signal", value: fmtPct(summary?.perf_since_signal), color: pnlUp === null ? undefined : pctColor(summary?.perf_since_signal) },
        { label: "Max Move", value: fmtPct(summary?.max_perf), color: summary?.max_perf != null ? pctColor(summary.max_perf) : undefined },
        ...(entered
            ? [
                  { label: "Entry Price", value: formatINR(signal?.fill_price) },
                  { label: "Trade P&L", value: fmtPct(summary?.trade_pnl_pct), color: tradePnlUp === null ? undefined : pctColor(summary?.trade_pnl_pct) }
              ]
            : []),
        { label: "Days Tracked", value: String(summary?.days_since_signal ?? "—") },
        ...(summary?.exit_triggered_on ? [{ label: "Stop Hit", value: summary.exit_triggered_on }] : [])
    ]

    return (
        <div className="flex flex-col gap-5">
            {/* Back + Hero */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex flex-col gap-3">
                <Link href="/signals" className="flex items-center gap-1.5 text-xs text-secondary hover:text-primary transition-colors w-fit">
                    <ArrowLeft size={13} strokeWidth={2} />
                    All signals
                </Link>
                <div className="flex items-end justify-between">
                    <div className="flex flex-col gap-2">
                        <div className="flex items-center gap-3">
                            <h1 className="text-xl font-semibold tracking-tight text-primary leading-none">{signal?.security?.ticker}</h1>
                            <Badge label={entered ? "ENTERED" : "MISSED"} variant={entered ? "green" : "muted"} />
                            {summary?.simulated && !entered && <Badge label="SIMULATED" variant="amber" />}
                        </div>
                        <div className="flex items-center gap-3 text-xs text-secondary">
                            <span>{signal?.security?.sector}</span>
                            {signal?.security?.industry && (
                                <>
                                    <span className="text-muted">·</span>
                                    <span>{signal?.security?.industry}</span>
                                </>
                            )}
                            <span className="text-muted">·</span>
                            <span className="font-mono">{signal?.observed_at?.slice(0, 10)}</span>
                            {signal?.strategy_name && (
                                <>
                                    <span className="text-muted">·</span>
                                    <span>{signal?.strategy_name}</span>
                                </>
                            )}
                        </div>
                    </div>
                    <div className="flex flex-col items-end gap-0.5 px-4 py-2.5 bg-surface border border-border rounded-[var(--radius-card)]">
                        <span className="text-[11px] text-secondary">Since Signal</span>
                        <div className={`text-2xl font-semibold leading-none ${pnlUp === null ? "text-secondary" : pctColor(summary?.perf_since_signal)}`}>{fmtPct(summary?.perf_since_signal)}</div>
                    </div>
                </div>
            </motion.div>

            {/* Stat strip */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.4, ease }}>
                <div className="flex items-center rounded-[var(--radius-card)] overflow-hidden bg-surface border border-border">
                    {statItems.map(({ label, value, color }, i) => (
                        <div key={label} className="flex-1 flex flex-col gap-1 px-5 py-4" style={{ borderRight: i < statItems.length - 1 ? "1px solid var(--color-border)" : "none" }}>
                            <span className="text-[10px] uppercase tracking-wide font-medium text-secondary whitespace-nowrap">{label}</span>
                            <span className={`text-xl font-bold leading-none ${color ?? "text-primary"}`}>{value}</span>
                        </div>
                    ))}
                </div>
            </motion.div>

            {/* Trade detail (entered only) */}
            {entered && signal && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15, duration: 0.4 }}>
                    <div className="grid grid-cols-4 gap-3">
                        {[
                            { label: "Fill Price", value: formatINR(signal.fill_price) },
                            { label: "Quantity", value: signal.fill_quantity ? String(signal.fill_quantity) : "—" },
                            { label: "Entry Date", value: signal.entry_date ?? "—" },
                            {
                                label: signal.exit_date ? "Exit Date" : "Timeout Date",
                                value: signal.exit_date ?? signal.timeout_date ?? "—",
                                highlight: signal.exit_date != null
                            }
                        ].map(({ label, value, highlight }) => (
                            <div key={label} className="flex flex-col gap-1.5 px-4 py-3 rounded-[var(--radius-card)] bg-surface2 border border-border">
                                <span className="text-[10px] uppercase tracking-wide text-secondary font-medium">{label}</span>
                                <span className={`text-lg font-bold leading-none ${highlight ? "text-danger" : "text-primary"}`}>{value}</span>
                            </div>
                        ))}
                    </div>
                </motion.div>
            )}

            {/* Signal conditions from payload */}
            {(() => {
                const features = signal?.payload?.features as Record<string, number> | undefined
                if (!features || Object.keys(features).length === 0) return null
                return (
                    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.18, duration: 0.4 }}>
                        <Card padding="md" className="flex flex-col gap-3">
                            <span className="text-xs font-medium text-secondary">Signal Conditions</span>
                            <div className="flex flex-wrap gap-3">
                                {Object.entries(features).map(([key, value]) => {
                                    const label = key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())
                                    const pct = (value * 100).toFixed(1)
                                    return (
                                        <div key={key} className="flex flex-col gap-1.5 px-4 py-3 rounded-[var(--radius-card)] bg-surface2 border border-border min-w-36">
                                            <span className="text-[10px] uppercase tracking-wide text-secondary font-medium">{label}</span>
                                            <div className="flex items-end gap-2">
                                                <span className="text-lg font-bold text-primary leading-none">{pct}%</span>
                                                <span className="text-[10px] text-muted pb-0.5">percentile</span>
                                            </div>
                                            <div className="h-0.5 rounded-full bg-border">
                                                <div className="h-0.5 rounded-full" style={{ width: `${Math.min(value * 100, 100)}%`, background: "var(--color-primary)", opacity: 0.5 }} />
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>
                        </Card>
                    </motion.div>
                )
            })()}

            {/* Forward price chart */}
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2, duration: 0.5 }}>
                {forwardData.length > 0 ? (
                    <ForwardChart data={forwardData} simulated={summary?.simulated ?? true} fillPrice={signal?.fill_price ?? null} />
                ) : (
                    <Card padding="md">
                        <div className="flex items-center justify-center py-16 text-sm text-secondary">No forward price data available</div>
                    </Card>
                )}
            </motion.div>

            {/* MTM progression table (last 10 rows) */}
            {forwardData.length > 0 && (
                <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.25, duration: 0.4 }}>
                    <Card padding="md" className="flex flex-col gap-3">
                        <span className="text-xs font-medium text-secondary">Daily Progression (last 10)</span>
                        <div className="rounded-[var(--radius-card)] overflow-hidden border border-border">
                            <table className="w-full text-xs border-collapse">
                                <thead>
                                    <tr className="border-b border-border">
                                        {["Date", "Close", "Stop Level", "MTM %", "ATR 14"].map((h) => (
                                            <th key={h} className="py-2.5 px-4 text-left text-[10px] font-medium uppercase tracking-wide text-secondary first:pl-5 last:pr-5">
                                                {h}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {[...forwardData].slice(-10).map((row, i) => {
                                        const up = row.mtm_pct != null ? row.mtm_pct >= 0 : null
                                        return (
                                            <tr key={row.date} className={`border-b border-border ${row.exit_triggered ? "bg-danger/5" : ""}`}>
                                                <td className="py-2.5 px-4 pl-5 text-secondary">
                                                    <div className="flex items-center gap-2">
                                                        {row.exit_triggered && <AlertTriangle size={10} className="text-danger" strokeWidth={2} />}
                                                        {row.date}
                                                    </div>
                                                </td>
                                                <td className="py-2.5 px-4 text-primary">{formatINR(row.close)}</td>
                                                <td className="py-2.5 px-4 text-danger/70">{formatINR(row.stop_price)}</td>
                                                <td className={`py-2.5 px-4 font-semibold ${up === null ? "text-secondary" : up ? "text-success" : "text-danger"}`}>{fmtPct(row.mtm_pct)}</td>
                                                <td className="py-2.5 px-4 pr-5 text-muted">{row.atr_14 != null ? row.atr_14.toFixed(2) : "—"}</td>
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </Card>
                </motion.div>
            )}
        </div>
    )
}
