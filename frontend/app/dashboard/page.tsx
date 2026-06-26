"use client"

import { useTrades } from "@/libraries/hooks/useTrades"
import { usePortfolioStats } from "@/libraries/hooks/usePortfolio"
import { useSignals } from "@/libraries/hooks/useSignals"
import PageHeader from "@/components/layout/PageHeader"
import Card from "@/components/ui/Card"
import Stat from "@/components/ui/Stat"
import Badge from "@/components/ui/Badge"
import Skeleton from "@/components/ui/Skeleton"

function formatCurrency(value: number | null) {
    if (value === null) return "—"
    return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(value)
}

export default function DashboardPage() {
    const { data: trades, isLoading: tradesLoading } = useTrades("open")
    const { data: stats, isLoading: statsLoading } = usePortfolioStats()
    const { data: signals, isLoading: signalsLoading } = useSignals()

    const todaySignals =
        signals?.filter((s) => {
            const today = new Date().toISOString().slice(0, 10)
            return s.observed_at.slice(0, 10) === today
        }) ?? []

    return (
        <div className="flex flex-col gap-8">
            <PageHeader title="Dashboard" subtitle="Morning snapshot" />

            {/* Stats row */}
            <div className="grid grid-cols-4 gap-4">
                {statsLoading ? (
                    [...Array(4)].map((_, i) => <Skeleton key={i} className="h-20" />)
                ) : (
                    <>
                        <Card>
                            <Stat label="Total Trades" value={stats?.total_trades ?? "—"} mono={false} />
                        </Card>
                        <Card>
                            <Stat label="Open Positions" value={stats?.open_trades ?? "—"} mono={false} />
                        </Card>
                        <Card>
                            <Stat label="Closed Trades" value={stats?.closed_trades ?? "—"} mono={false} />
                        </Card>
                        <Card>
                            <Stat label="Total P&L" value={formatCurrency(stats?.total_pnl ?? null)} delta={stats?.win_rate ?? undefined} deltaLabel="win rate" />
                        </Card>
                    </>
                )}
            </div>

            <div className="grid grid-cols-2 gap-6">
                {/* Open positions strip */}
                <div className="flex flex-col gap-3">
                    <h2 className="text-xs uppercase tracking-widest text-secondary font-medium">Open Positions</h2>
                    {tradesLoading && [...Array(3)].map((_, i) => <Skeleton key={i} className="h-16" />)}
                    {!tradesLoading && (!trades || trades.length === 0) && (
                        <Card>
                            <p className="text-sm text-secondary">No open positions</p>
                        </Card>
                    )}
                    {trades?.map((trade) => (
                        <Card key={trade.id} className="flex items-center justify-between">
                            <div className="flex flex-col gap-0.5">
                                <p className="text-sm font-semibold text-primary">{trade.security.ticker}</p>
                                <p className="text-xs text-secondary">{trade.security.display_name}</p>
                            </div>
                            <div className="flex flex-col items-end gap-0.5">
                                <p className="text-xs text-secondary font-mono">Entry {trade.fill_price ? `₹${trade.fill_price.toFixed(2)}` : "—"}</p>
                                <p className="text-xs text-secondary font-mono">Timeout {trade.timeout_date}</p>
                            </div>
                        </Card>
                    ))}
                </div>

                {/* Today's signals */}
                <div className="flex flex-col gap-3">
                    <h2 className="text-xs uppercase tracking-widest text-secondary font-medium">Today&apos;s Signals</h2>
                    {signalsLoading && [...Array(3)].map((_, i) => <Skeleton key={i} className="h-16" />)}
                    {!signalsLoading && todaySignals.length === 0 && (
                        <Card>
                            <p className="text-sm text-secondary">No signals today</p>
                        </Card>
                    )}
                    {todaySignals.map((signal) => (
                        <Card key={signal.id} className="flex items-center justify-between">
                            <div className="flex flex-col gap-0.5">
                                <p className="text-sm font-semibold text-primary">{signal.security.ticker}</p>
                                <p className="text-xs text-secondary">{signal.security.display_name}</p>
                            </div>
                            <Badge label={signal.signal_status} variant={signal.signal_status === "entered" ? "green" : "muted"} />
                        </Card>
                    ))}
                </div>
            </div>

            {/* Portfolio summary */}
            {!statsLoading && stats && (
                <div className="flex flex-col gap-3">
                    <h2 className="text-xs uppercase tracking-widest text-secondary font-medium">Performance Summary</h2>
                    <div className="grid grid-cols-4 gap-4">
                        <Card>
                            <Stat label="Win Rate" value={stats.win_rate !== null ? `${stats.win_rate}%` : "—"} />
                        </Card>
                        <Card>
                            <Stat label="Avg Hold" value={stats.avg_holding_days !== null ? `${stats.avg_holding_days}d` : "—"} />
                        </Card>
                        <Card>
                            <Stat label="Avg Win" value={stats.avg_win_pct !== null ? `${stats.avg_win_pct.toFixed(2)}%` : "—"} />
                        </Card>
                        <Card>
                            <Stat label="Avg Loss" value={stats.avg_loss_pct !== null ? `${stats.avg_loss_pct.toFixed(2)}%` : "—"} />
                        </Card>
                    </div>
                </div>
            )}
        </div>
    )
}
