"use client"

import { useState } from "react"
import { motion } from "framer-motion"
import { Layers, ListTree, Settings2, SlidersHorizontal } from "lucide-react"
import { useStrategies } from "@/libraries/hooks/useStrategies"
import Skeleton from "@/components/ui/Skeleton"
import Card from "@/components/ui/Card"
import KpiTile from "@/components/ui/KpiTile"
import Badge from "@/components/ui/Badge"
import EmptyState from "@/components/ui/EmptyState"
import { Strategy } from "@/libraries/types/strategy"
import StrategyConfigModal from "./StrategyConfigModal"
import StrategyVersionHistory from "./StrategyVersionHistory"

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

function StrategyRow({ strategy, index, onEdit, onHistory }: { strategy: Strategy; index: number; onEdit: () => void; onHistory: () => void }) {
    const hasVersions = strategy.active_version !== null || strategy.version_count > 0

    return (
        <motion.div initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.04, duration: 0.3, ease }}>
            <div className="flex items-center gap-5 px-5 py-4 hover:bg-surface2/60 transition-colors border-b border-border">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-0.5">
                        <p className="text-sm font-semibold text-primary leading-none">{strategy.name}</p>
                        <Badge label={strategy.is_active ? "Active" : "Inactive"} variant={strategy.is_active ? "green" : "muted"} />
                    </div>
                    <p className="text-xs text-secondary font-mono truncate">{strategy.code}</p>
                </div>

                <div className="w-32 flex flex-col items-end gap-0.5 shrink-0">
                    <span className="text-[11px] font-mono font-semibold text-primary">{strategy.active_version ? `v${strategy.active_version.version}` : "—"}</span>
                    <span className="text-[10px] text-muted">
                        {strategy.version_count} version{strategy.version_count === 1 ? "" : "s"}
                    </span>
                </div>

                <div className="w-28 flex justify-end shrink-0">
                    <span className={`inline-flex items-center gap-1 text-[10px] font-mono uppercase tracking-wider px-2 py-1 rounded-full ${strategy.has_config_schema ? "text-primary bg-surface2" : "text-muted bg-surface2"}`}>
                        <SlidersHorizontal size={9} />
                        {strategy.has_config_schema ? "Typed" : "Raw JSON"}
                    </span>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                    <button
                        onClick={onEdit}
                        disabled={!hasVersions}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${hasVersions ? "text-secondary border-border hover:text-primary hover:bg-surface2" : "text-muted border-border opacity-40 cursor-not-allowed"}`}
                    >
                        Edit Config
                    </button>
                    <button
                        onClick={onHistory}
                        disabled={!hasVersions}
                        className={`px-3 py-1.5 rounded-lg text-xs font-semibold border transition-colors ${hasVersions ? "text-secondary border-border hover:text-primary hover:border-muted" : "text-muted border-border opacity-40 cursor-not-allowed"}`}
                    >
                        History
                    </button>
                </div>
            </div>
        </motion.div>
    )
}

export default function StrategiesPage() {
    const { data: strategies, isLoading, isError } = useStrategies()
    const [editing, setEditing] = useState<Strategy | null>(null)
    const [viewingHistory, setViewingHistory] = useState<Strategy | null>(null)

    const totalStrategies = strategies?.length ?? 0
    const activeStrategies = strategies?.filter((s) => s.is_active).length ?? 0
    const totalVersions = strategies?.reduce((sum, s) => sum + s.version_count, 0) ?? 0

    return (
        <div className="flex flex-col gap-6">
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between">
                <div className="flex flex-col gap-1.5">
                    <p className="text-xs text-secondary">Configuration</p>
                    <h1 className="text-xl font-semibold tracking-tight text-primary leading-none">Strategies</h1>
                    <p className="text-xs text-secondary">Edit config as a new draft version, then activate it explicitly — nothing changes live until you say so.</p>
                </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.4, ease }} className="grid grid-cols-3 gap-2">
                {[
                    { icon: Layers, iconColor: "var(--color-secondary)", label: "Strategies", value: isLoading ? "—" : String(totalStrategies) },
                    { icon: Settings2, iconColor: "var(--color-success)", label: "Active", value: isLoading ? "—" : String(activeStrategies) },
                    { icon: ListTree, iconColor: "var(--color-secondary)", label: "Total Versions", value: isLoading ? "—" : String(totalVersions) }
                ].map((t) => (
                    <KpiTile key={t.label} {...t} />
                ))}
            </motion.div>

            {isLoading && (
                <div className="rounded-[var(--radius-card)] overflow-hidden border border-border">
                    {[...Array(3)].map((_, i) => (
                        <Skeleton key={i} className="h-16 rounded-none" />
                    ))}
                </div>
            )}

            {isError && (
                <div className="py-16 text-center rounded-[var(--radius-card)] bg-surface2 border border-border">
                    <p className="text-sm font-medium text-primary mb-1">Failed to load strategies</p>
                    <p className="text-xs text-secondary">Check that the backend is running</p>
                </div>
            )}

            {!isLoading && !isError && (strategies?.length ?? 0) === 0 && <EmptyState icon={Layers} title="No strategies found" />}

            {!isLoading && !isError && (strategies?.length ?? 0) > 0 && (
                <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="bg-surface border border-border rounded-[var(--radius-card)] shadow-[var(--shadow-border)]">
                    <div className="overflow-hidden rounded-[var(--radius-card)]">
                        {strategies?.map((s, i) => (
                            <StrategyRow key={s.id} strategy={s} index={i} onEdit={() => setEditing(s)} onHistory={() => setViewingHistory(s)} />
                        ))}
                    </div>
                </motion.div>
            )}

            {editing && (
                <StrategyConfigModal
                    strategy={editing}
                    onClose={() => setEditing(null)}
                    onCreated={() => {
                        const justEdited = editing
                        setEditing(null)
                        setViewingHistory(justEdited)
                    }}
                />
            )}

            {viewingHistory && <StrategyVersionHistory strategy={viewingHistory} onClose={() => setViewingHistory(null)} />}
        </div>
    )
}
