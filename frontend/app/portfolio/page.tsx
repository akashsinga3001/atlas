"use client"

import { usePortfolioStats, useEquityCurve, useNavCurve, useCreateCashFlow } from "@/libraries/hooks/usePortfolio"
import { useTrades } from "@/libraries/hooks/useTrades"
import { useLivePnL } from "@/libraries/hooks/useLivePnL"
import { useCountUp } from "@/libraries/hooks/useCountUp"
import Card from "@/components/ui/Card"
import Badge from "@/components/ui/Badge"
import Skeleton from "@/components/ui/Skeleton"
import HudCorners from "@/components/ui/HudCorners"
import KpiTile from "@/components/ui/KpiTile"
import { motion, AnimatePresence } from "framer-motion"
import { TrendingUp, TrendingDown, Minus, Plus, ArrowDownToLine, ArrowUpFromLine, X, History, Target, Gauge, Clock, Wallet } from "lucide-react"
import { AreaChart, Area, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine } from "recharts"
import { Trade } from "@/libraries/types/trade"
import { FlowType } from "@/libraries/types/portfolio"
import { useMemo, useState } from "react"

import { formatINR, pctColor } from "@/libraries/utils/format"
import { PortfolioStats } from "@/libraries/types/portfolio"

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

function buildMonthlyPnl(trades: Trade[]): { year: number; month: number; pnl: number }[] {
    const map: Record<string, number> = {}
    for (const t of trades) {
        if (!t.exit_date || t.pnl === null) continue
        const d = new Date(t.exit_date)
        const key = `${d.getFullYear()}-${d.getMonth()}`
        map[key] = (map[key] ?? 0) + (t.pnl ?? 0)
    }
    return Object.entries(map).map(([key, pnl]) => {
        const [y, m] = key.split("-").map(Number)
        return { year: y, month: m, pnl }
    })
}

const CustomTooltip = ({ active, payload, label }: { active?: boolean; payload?: { value: number; payload: { pnl: number } }[]; label?: string }) => {
    if (!active || !payload?.length) return null
    const pnl = payload[0]?.value
    const tradePnl = payload[0]?.payload?.pnl
    return (
        <div className="rounded-xl px-3 py-2.5 text-xs" style={{ background: "var(--color-tooltip)", border: "1px solid rgba(255,255,255,0.08)" }}>
            <div className="text-secondary font-mono mb-2">{label}</div>
            <div className={`font-bold font-mono text-sm ${pnl >= 0 ? "text-green-400" : "text-red-400"}`}>{formatINR(pnl, true)}</div>
            {tradePnl !== undefined && <div className={`text-[10px] font-mono mt-0.5 ${tradePnl >= 0 ? "text-green-400/70" : "text-red-400/70"}`}>Trade: {formatINR(tradePnl, true)}</div>}
        </div>
    )
}

function MonthlyHeatmap({ trades }: { trades: Trade[] }) {
    const cells = useMemo(() => buildMonthlyPnl(trades), [trades])
    const years = useMemo(() => [...new Set(cells.map((c) => c.year))].sort(), [cells])
    const maxAbs = useMemo(() => Math.max(...cells.map((c) => Math.abs(c.pnl)), 1), [cells])

    if (years.length === 0)
        return (
            <div className="py-10 text-center">
                <p className="text-sm text-secondary">No closed trades yet</p>
            </div>
        )

    const pnlFor = (year: number, month: number) => cells.find((c) => c.year === year && c.month === month)?.pnl ?? null
    const todayYear = new Date().getFullYear()
    const todayMonth = new Date().getMonth()

    return (
        <div className="flex flex-col gap-2">
            {/* Month labels */}
            <div className="grid gap-1.5" style={{ gridTemplateColumns: "48px repeat(12, 1fr)" }}>
                <div />
                {MONTHS.map((m) => (
                    <div key={m} className="text-center font-mono text-[10px] uppercase tracking-widest text-secondary font-medium">
                        {m}
                    </div>
                ))}
            </div>

            {/* Rows per year */}
            {years.map((year) => (
                <div key={year} className="grid gap-1.5 items-center" style={{ gridTemplateColumns: "48px repeat(12, 1fr)" }}>
                    <div className="text-[11px] font-mono font-semibold text-secondary text-right pr-2">{year}</div>
                    {MONTHS.map((_, monthIdx) => {
                        const pnl = pnlFor(year, monthIdx)
                        const intensity = pnl !== null ? Math.min(Math.abs(pnl) / maxAbs, 1) : 0
                        const isWin = pnl !== null && pnl >= 0
                        const isFuture = year > todayYear || (year === todayYear && monthIdx > todayMonth)
                        const bg = pnl === null ? "rgba(255,255,255,0.03)" : isWin ? `rgba(74, 222, 128, ${0.08 + intensity * 0.35})` : `rgba(248, 113, 113, ${0.08 + intensity * 0.35})`
                        const textColor = pnl === null ? "rgba(255,255,255,0.15)" : isWin ? "#4ade80" : "#f87171"

                        return (
                            <div key={monthIdx} title={pnl !== null ? formatINR(pnl) : undefined} className="rounded-lg flex flex-col items-center justify-center transition-all" style={{ background: isFuture ? "rgba(255,255,255,0.015)" : bg, aspectRatio: "1.6 / 1", opacity: isFuture ? 0.3 : 1 }}>
                                {pnl !== null && (
                                    <span className="text-[9px] font-mono font-bold leading-none" style={{ color: textColor }}>
                                        {formatINR(pnl, true)}
                                    </span>
                                )}
                            </div>
                        )
                    })}
                </div>
            ))}

            {/* Column totals */}
            <div className="grid gap-1.5 pt-1" style={{ gridTemplateColumns: "48px repeat(12, 1fr)", borderTop: "1px solid rgba(255,255,255,0.05)" }}>
                <div className="font-mono text-[9px] text-secondary font-medium text-right pr-2 self-center uppercase tracking-[0.08em]">Total</div>
                {MONTHS.map((_, monthIdx) => {
                    const total = years.reduce((s, y) => s + (pnlFor(y, monthIdx) ?? 0), 0)
                    const hasTrades = cells.some((c) => c.month === monthIdx)
                    return (
                        <div key={monthIdx} className="text-center self-center">
                            {hasTrades && total !== 0 && <span className={`text-[9px] font-mono font-semibold ${total >= 0 ? "text-green-400/60" : "text-red-400/60"}`}>{formatINR(total, true)}</span>}
                        </div>
                    )
                })}
            </div>
        </div>
    )
}

function CashFlowForm({ onClose }: { onClose: () => void }) {
    const [flowType, setFlowType] = useState<FlowType>("deposit")
    const [amount, setAmount] = useState("")
    const [flowDate, setFlowDate] = useState(new Date().toISOString().slice(0, 10))
    const [note, setNote] = useState("")
    const { mutate, isPending, error } = useCreateCashFlow()

    const handleSubmit = () => {
        const parsedAmount = parseFloat(amount)
        if (!parsedAmount || parsedAmount <= 0) return
        mutate({ flow_type: flowType, amount: parsedAmount, flow_date: flowDate, note: note || undefined }, { onSuccess: onClose })
    }

    return (
        <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.25, ease }} className="overflow-hidden">
            <Card padding="md" className="relative flex flex-col gap-4 hud-panel">
                <HudCorners opacity={0.3} />
                <div className="flex items-center justify-between">
                    <span className="hud-label">Record Cash Flow</span>
                    <button onClick={onClose} className="text-muted hover:text-primary transition-colors">
                        <X size={16} />
                    </button>
                </div>
                <div className="flex items-center gap-2">
                    {[
                        { type: "deposit" as FlowType, label: "Deposit", Icon: ArrowDownToLine },
                        { type: "withdrawal" as FlowType, label: "Withdrawal", Icon: ArrowUpFromLine }
                    ].map(({ type, label, Icon }) => (
                        <button key={type} onClick={() => setFlowType(type)} className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium transition-all duration-150 border ${flowType === type ? "bg-accent/10 text-accent border-accent/30" : "bg-transparent text-secondary border-white/8 hover:text-primary hover:border-white/20"}`}>
                            <Icon size={12} />
                            {label}
                        </button>
                    ))}
                </div>
                <div className="grid grid-cols-2 gap-3">
                    <div className="flex flex-col gap-1.5">
                        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-secondary font-medium">Amount (₹)</span>
                        <input type="number" value={amount} onChange={(e) => setAmount(e.target.value)} placeholder="0.00" className="px-3 py-2 rounded-lg bg-surface2 border border-white/8 text-sm font-mono text-primary focus:outline-none focus:border-accent/40" />
                    </div>
                    <div className="flex flex-col gap-1.5">
                        <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-secondary font-medium">Date</span>
                        <input type="date" value={flowDate} onChange={(e) => setFlowDate(e.target.value)} className="px-3 py-2 rounded-lg bg-surface2 border border-white/8 text-sm font-mono text-primary focus:outline-none focus:border-accent/40" />
                    </div>
                </div>
                <div className="flex flex-col gap-1.5">
                    <span className="font-mono text-[10px] uppercase tracking-[0.12em] text-secondary font-medium">Note (optional)</span>
                    <input type="text" value={note} onChange={(e) => setNote(e.target.value)} placeholder="e.g. Quarterly top-up" className="px-3 py-2 rounded-lg bg-surface2 border border-white/8 text-sm text-primary focus:outline-none focus:border-accent/40" />
                </div>
                {error && <p className="text-xs text-red-400">Failed to record cash flow. Try again.</p>}
                <button onClick={handleSubmit} disabled={isPending || !amount} className="self-end px-4 py-2 rounded-lg bg-accent/10 text-accent border border-accent/30 text-xs font-semibold hover:bg-accent/15 transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                    {isPending ? "Saving..." : "Save"}
                </button>
            </Card>
        </motion.div>
    )
}

function AccountValueChart() {
    const { data: navCurve, isLoading } = useNavCurve()
    const last = navCurve && navCurve.length > 0 ? navCurve[navCurve.length - 1] : null

    return (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05, duration: 0.5, ease }}>
            <Card padding="md" className="relative flex flex-col gap-4 hud-panel">
                <HudCorners />
                <div className="flex items-center justify-between">
                    <span className="hud-label">Account Value</span>
                    {!isLoading && last && (
                        <span className="text-[10px] text-muted font-mono">
                            {formatINR(last.total_value, true)} as of {last.date}
                        </span>
                    )}
                </div>
                {isLoading && <Skeleton className="rounded-lg" style={{ height: 220 }} />}
                {!isLoading && (!navCurve || navCurve.length === 0) && (
                    <div className="flex flex-col items-center justify-center gap-1.5" style={{ height: 220 }}>
                        <p className="text-sm font-medium text-secondary">No account value history yet</p>
                        <p className="text-xs text-muted">Builds up daily after the EOD snapshot job runs</p>
                    </div>
                )}
                {!isLoading && navCurve && navCurve.length > 0 && (
                    <div style={{ height: 220 }}>
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={navCurve} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                                <defs>
                                    <linearGradient id="navGrad" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#60a5fa" stopOpacity={0.25} />
                                        <stop offset="100%" stopColor="#60a5fa" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} tickFormatter={(v) => v?.slice(5)} />
                                <YAxis tick={{ fontSize: 10, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} tickFormatter={(v) => formatINR(v, true)} width={64} domain={["auto", "auto"]} />
                                <Tooltip
                                    content={({ active, payload, label }) => {
                                        if (!active || !payload?.length) return null
                                        const d = payload[0]?.payload
                                        return (
                                            <div className="rounded-xl px-3 py-2.5 text-xs" style={{ background: "var(--color-tooltip)", border: "1px solid rgba(255,255,255,0.08)" }}>
                                                <div className="text-secondary font-mono mb-1">{label}</div>
                                                <div className="font-bold font-mono text-sm text-primary">{formatINR(d.total_value, true)}</div>
                                                {d.cash_flow != null && (
                                                    <div className={`text-[10px] font-mono mt-1 ${d.cash_flow >= 0 ? "text-green-400/70" : "text-red-400/70"}`}>
                                                        {d.cash_flow >= 0 ? "+" : ""}
                                                        {formatINR(d.cash_flow, true)} {d.cash_flow >= 0 ? "deposit" : "withdrawal"}
                                                    </div>
                                                )}
                                            </div>
                                        )
                                    }}
                                />
                                <Area type="monotone" dataKey="total_value" stroke="#60a5fa" strokeWidth={2} fill="url(#navGrad)" dot={false} />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>
                )}
            </Card>
        </motion.div>
    )
}

export default function PortfolioPage() {
    const { data: stats, isLoading: statsLoading } = usePortfolioStats()
    const { data: curve, isLoading: curveLoading } = useEquityCurve()
    const { data: trades, isLoading: tradesLoading } = useTrades("closed")
    const { data: openTrades } = useTrades("open")
    const liveQuotes = useLivePnL(openTrades?.map((t) => t.security.ticker) ?? [])
    const [showCashFlowForm, setShowCashFlowForm] = useState(false)

    const openUnrealised =
        openTrades?.reduce((s, t) => {
            const lp = liveQuotes[t.security.ticker]?.last_price
            if (lp && t.fill_price && t.fill_quantity) return s + (lp - t.fill_price) * t.fill_quantity
            return s + (t.pnl ?? 0)
        }, 0) ?? 0
    const totalPnl = (stats?.total_pnl ?? 0) + openUnrealised

    const pnlPositive = totalPnl >= 0
    const chartColor = pnlPositive ? "#4ade80" : "#f87171"
    const pnlColor = totalPnl >= 0 ? "text-green-400" : "text-red-400"
    const totalPnlAnimated = useCountUp(totalPnl)

    const maxDrawdown = stats?.max_drawdown_pct ?? null
    const profitFactor = stats?.profit_factor ?? null
    const bestTrade = trades?.reduce((b, t) => ((t.pnl_pct ?? -Infinity) > (b?.pnl_pct ?? -Infinity) ? t : b), null as Trade | null) ?? null
    const worstTrade = trades?.reduce((w, t) => ((t.pnl_pct ?? Infinity) < (w?.pnl_pct ?? Infinity) ? t : w), null as Trade | null) ?? null

    return (
        <div className="flex flex-col gap-6">
            {/* Hero */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between">
                <div className="flex flex-col gap-2">
                    <div>
                        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-secondary mb-1">Performance</p>
                        <h1 className="text-4xl font-bold tracking-tight text-primary leading-none">Portfolio</h1>
                    </div>
                    <button onClick={() => setShowCashFlowForm((v) => !v)} className="self-start flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium border border-white/8 text-secondary hover:text-primary hover:border-white/20 transition-colors">
                        <Plus size={12} />
                        Record Deposit / Withdrawal
                    </button>
                </div>
                <div className="relative flex flex-col items-end gap-1 px-5 py-4 hud-panel">
                    <HudCorners opacity={0.35} />
                    <span className="font-mono text-[10px] uppercase tracking-[0.15em] text-secondary">
                        Total P&amp;L <span className="normal-case tracking-normal opacity-50">(closed + open)</span>
                    </span>
                    {statsLoading ? <Skeleton className="h-12 w-36" /> : <span className={`text-5xl font-bold font-mono leading-none ${pnlColor}`}>{formatINR(totalPnlAnimated, true)}</span>}
                    {openUnrealised !== 0 && !statsLoading && (
                        <span className="text-[10px] font-mono text-secondary">
                            {formatINR(stats?.total_pnl, true)} closed ·{" "}
                            <span className={openUnrealised >= 0 ? "text-green-400/70" : "text-red-400/70"}>
                                {openUnrealised >= 0 ? "+" : ""}
                                {formatINR(openUnrealised, true)} open
                            </span>
                        </span>
                    )}
                    {!statsLoading && stats?.true_return_pct != null && (
                        <span className="text-[10px] font-mono text-secondary">
                            True return (Modified Dietz):{" "}
                            <span className={stats.true_return_pct >= 0 ? "text-green-400/70" : "text-red-400/70"}>
                                {stats.true_return_pct >= 0 ? "+" : ""}
                                {stats.true_return_pct.toFixed(2)}%
                            </span>
                        </span>
                    )}
                </div>
            </motion.div>

            <AnimatePresence>{showCashFlowForm && <CashFlowForm onClose={() => setShowCashFlowForm(false)} />}</AnimatePresence>

            {/* Account Value (NAV curve) */}
            <AccountValueChart />

            {/* Equity curve */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.5, ease }}>
                <Card padding="md" className="relative flex flex-col gap-4 hud-panel">
                    <HudCorners />
                    <div className="flex items-center justify-between">
                        <span className="hud-label">Equity Curve</span>
                        {!curveLoading && curve && <span className="text-[10px] text-muted font-mono">{curve.length} closed trades</span>}
                    </div>
                    {curveLoading && <Skeleton className="rounded-lg" style={{ height: 280 }} />}
                    {!curveLoading && (!curve || curve.length === 0) && (
                        <div className="flex items-center justify-center" style={{ height: 280 }}>
                            <p className="text-sm text-secondary">No closed trades yet</p>
                        </div>
                    )}
                    {!curveLoading && curve && curve.length > 0 && (
                        <div style={{ height: 280 }}>
                            <ResponsiveContainer width="100%" height="100%">
                                <AreaChart data={curve} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
                                    <defs>
                                        <linearGradient id="curveGrad" x1="0" y1="0" x2="0" y2="1">
                                            <stop offset="0%" stopColor={chartColor} stopOpacity={0.25} />
                                            <stop offset="100%" stopColor={chartColor} stopOpacity={0} />
                                        </linearGradient>
                                    </defs>
                                    <XAxis dataKey="date" tick={{ fontSize: 10, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} tickFormatter={(v) => v?.slice(5)} />
                                    <YAxis tick={{ fontSize: 10, fill: "var(--color-muted)" }} tickLine={false} axisLine={false} tickFormatter={(v) => formatINR(v, true)} width={64} />
                                    <ReferenceLine y={0} stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
                                    <Tooltip content={<CustomTooltip />} />
                                    <Area type="monotone" dataKey="cumulative_pnl" stroke={chartColor} strokeWidth={2} fill="url(#curveGrad)" dot={false} />
                                </AreaChart>
                            </ResponsiveContainer>
                        </div>
                    )}
                </Card>
            </motion.div>

            {/* Stats strip — 8 cols */}
            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2, duration: 0.4, ease }} className="grid grid-cols-4 md:grid-cols-8 gap-2">
                {[
                    { icon: History, iconColor: "var(--color-secondary)", label: "Closed Trades", value: statsLoading ? "—" : String(stats?.closed_trades ?? 0) },
                    { icon: Target, iconColor: "#4ade80", label: "Win Rate", value: statsLoading ? "—" : stats?.win_rate != null ? `${stats.win_rate}%` : "—", valueColor: stats?.win_rate != null ? (stats.win_rate >= 50 ? "text-green-400" : "text-red-400") : undefined, ring: stats?.win_rate ?? 0, ringColor: "#4ade80" },
                    { icon: Gauge, iconColor: profitFactor != null && profitFactor >= 1 ? "#4ade80" : "#f87171", label: "Profit Factor", value: statsLoading ? "—" : profitFactor != null ? profitFactor.toFixed(2) : "—", valueColor: profitFactor != null ? (profitFactor >= 1 ? "text-green-400" : "text-red-400") : undefined },
                    { icon: TrendingDown, iconColor: "#f87171", label: "Max Drawdown", value: statsLoading ? "—" : maxDrawdown != null ? `${maxDrawdown.toFixed(1)}%` : "—", valueColor: "text-red-400" },
                    { icon: Clock, iconColor: "var(--color-secondary)", label: "Avg Hold", value: statsLoading ? "—" : stats?.avg_holding_days != null ? `${stats.avg_holding_days}d` : "—" },
                    { icon: TrendingUp, iconColor: "#4ade80", label: "Avg Win", value: statsLoading ? "—" : stats?.avg_win_pct != null ? `+${stats.avg_win_pct.toFixed(2)}%` : "—", valueColor: "text-green-400" },
                    { icon: TrendingDown, iconColor: "#f87171", label: "Avg Loss", value: statsLoading ? "—" : stats?.avg_loss_pct != null ? `${stats.avg_loss_pct.toFixed(2)}%` : "—", valueColor: "text-red-400" },
                    { icon: Wallet, iconColor: "var(--color-accent)", label: "Net Deposits", value: statsLoading ? "—" : formatINR(stats?.net_deposits ?? 0, true) }
                ].map((t) => (
                    <KpiTile key={t.label} {...t} />
                ))}
            </motion.div>

            {/* Monthly P&L heatmap */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.4, ease }}>
                <Card padding="md" className="relative flex flex-col gap-5 hud-panel">
                    <HudCorners opacity={0.3} />
                    <div className="flex items-center justify-between">
                        <span className="hud-label">Monthly P&amp;L</span>
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-1.5">
                                <div className="w-2.5 h-2.5 rounded-sm" style={{ background: "rgba(74,222,128,0.4)" }} />
                                <span className="text-[10px] text-muted">Profit</span>
                            </div>
                            <div className="flex items-center gap-1.5">
                                <div className="w-2.5 h-2.5 rounded-sm" style={{ background: "rgba(248,113,113,0.4)" }} />
                                <span className="text-[10px] text-muted">Loss</span>
                            </div>
                        </div>
                    </div>
                    {tradesLoading ? <Skeleton className="rounded-lg h-24" /> : <MonthlyHeatmap trades={trades ?? []} />}
                </Card>
            </motion.div>

            {/* Best / Worst */}
            {!tradesLoading && trades && trades.length > 0 && (
                <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35, duration: 0.35, ease }} className="grid grid-cols-2 gap-3">
                    {(
                        [
                            { label: "Best Trade", trade: bestTrade, positive: true },
                            { label: "Worst Trade", trade: worstTrade, positive: false }
                        ] as { label: string; trade: Trade | null; positive: boolean }[]
                    ).map(({ label, trade, positive }) => (
                        <div key={label} className="relative flex items-center justify-between px-5 py-4 hud-panel">
                            <HudCorners opacity={0.3} />
                            <div className="flex flex-col gap-0.5">
                                <span className="hud-label">{label}</span>
                                <span className="text-sm font-bold text-primary">{trade?.security.ticker ?? "—"}</span>
                                <span className="text-[10px] text-muted">{trade?.exit_date ?? ""}</span>
                            </div>
                            <div className="flex flex-col items-end gap-0.5">
                                <span className={`text-xl font-bold font-mono ${positive ? "text-green-400" : "text-red-400"}`}>{trade?.pnl_pct != null ? `${trade.pnl_pct > 0 ? "+" : ""}${trade.pnl_pct.toFixed(2)}%` : "—"}</span>
                                <span className={`text-sm font-mono font-semibold ${positive ? "text-green-400" : "text-red-400"}`}>{formatINR(trade?.pnl, true)}</span>
                            </div>
                        </div>
                    ))}
                </motion.div>
            )}

            {/* Trade history */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4, duration: 0.4, ease }}>
                <Card padding="sm" className="relative hud-panel">
                    <HudCorners opacity={0.3} />
                    <div className="px-4 pt-3 pb-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <span className="hud-label">Trade History</span>
                    </div>
                    {tradesLoading && (
                        <div className="flex flex-col gap-2 p-3">
                            {[...Array(5)].map((_, i) => (
                                <Skeleton key={i} className="h-14 rounded-lg" />
                            ))}
                        </div>
                    )}
                    {!tradesLoading && (!trades || trades.length === 0) && (
                        <div className="py-16 text-center">
                            <p className="text-sm font-medium text-primary mb-1">No closed trades</p>
                            <p className="text-xs text-secondary">Closed trades will appear here</p>
                        </div>
                    )}
                    {!tradesLoading && trades && trades.length > 0 && (
                        <table className="w-full text-sm">
                            <thead>
                                <tr style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                                    {["Ticker", "Entry", "Exit", "Entry ₹", "Exit ₹", "P&L", "P&L %", "Days", "Reason"].map((h) => (
                                        <th key={h} className="py-3 pr-6 first:pl-4 font-mono text-[10px] text-secondary uppercase tracking-[0.15em] font-medium text-left whitespace-nowrap">
                                            {h}
                                        </th>
                                    ))}
                                </tr>
                            </thead>
                            <tbody>
                                {trades.map((trade, i) => {
                                    const pnlUp = trade.pnl !== null ? trade.pnl >= 0 : null
                                    const PnlIcon = pnlUp === null ? Minus : pnlUp ? TrendingUp : TrendingDown
                                    const days = trade.exit_date && trade.entry_date ? Math.round((new Date(trade.exit_date).getTime() - new Date(trade.entry_date).getTime()) / 86400000) : null
                                    return (
                                        <motion.tr key={trade.id} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.45 + i * 0.03, duration: 0.3 }} className={`transition-colors ${pnlUp ? "hover:bg-green-400/2" : "hover:bg-red-400/2"}`} style={{ borderBottom: "1px solid rgba(255,255,255,0.03)" }}>
                                            <td className="py-3.5 pr-6 pl-4">
                                                <div className="flex flex-col gap-0.5">
                                                    <span className="font-bold text-primary tracking-tight whitespace-nowrap">{trade.security.ticker}</span>
                                                    <span className="text-[10px] text-muted whitespace-nowrap">{trade.security.sector ?? ""}</span>
                                                </div>
                                            </td>
                                            <td className="py-3.5 pr-6 text-secondary font-mono text-xs whitespace-nowrap">{trade.entry_date}</td>
                                            <td className="py-3.5 pr-6 text-secondary font-mono text-xs whitespace-nowrap">{trade.exit_date ?? "—"}</td>
                                            <td className="py-3.5 pr-6 font-mono text-primary whitespace-nowrap">₹{trade.fill_price?.toFixed(2) ?? "—"}</td>
                                            <td className="py-3.5 pr-6 font-mono text-primary whitespace-nowrap">{trade.exit_price ? `₹${trade.exit_price.toFixed(2)}` : "—"}</td>
                                            <td className={`py-3.5 pr-6 font-mono font-semibold whitespace-nowrap ${pctColor(trade.pnl)}`}>{formatINR(trade.pnl)}</td>
                                            <td className={`py-3.5 pr-6 font-mono font-semibold whitespace-nowrap ${pctColor(trade.pnl_pct)}`}>
                                                <div className="flex items-center gap-1">
                                                    <PnlIcon size={11} strokeWidth={2.5} />
                                                    {trade.pnl_pct !== null ? `${trade.pnl_pct > 0 ? "+" : ""}${trade.pnl_pct.toFixed(2)}%` : "—"}
                                                </div>
                                            </td>
                                            <td className="py-3.5 pr-6 text-secondary font-mono text-xs whitespace-nowrap">{days !== null ? `${days}d` : "—"}</td>
                                            <td className="py-3.5 pr-4 whitespace-nowrap">
                                                <Badge label={trade.exit_reason?.toUpperCase() ?? "—"} variant="muted" />
                                            </td>
                                        </motion.tr>
                                    )
                                })}
                            </tbody>
                        </table>
                    )}
                </Card>
            </motion.div>
        </div>
    )
}
