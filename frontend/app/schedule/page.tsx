"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { motion } from "framer-motion"
import { CalendarClock, Database, TrendingUp, Pencil, CheckCircle2, Circle } from "lucide-react"
import { useSchedule } from "@/libraries/hooks/useSchedule"
import { toggleScheduleEntry } from "@/libraries/api/schedule"
import Skeleton from "@/components/ui/Skeleton"
import KpiTile from "@/components/ui/KpiTile"
import Toggle from "@/components/ui/Toggle"
import { ScheduleEntry } from "@/libraries/types/schedule"
import ScheduleEntryModal from "./ScheduleEntryModal"

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

const GROUP_CONFIG: Record<string, { label: string; icon: React.ElementType }> = {
    data_pipeline: { label: "Data Pipeline", icon: Database },
    trading: { label: "Trading", icon: TrendingUp }
}

function cronDisplay(entry: ScheduleEntry): string {
    const parts = [entry.minute, entry.hour, entry.day_of_week, entry.day_of_month, entry.month_of_year]
    if (parts.every((p) => p === "*")) return "Every minute"
    return `${entry.minute} ${entry.hour} ${entry.day_of_week} ${entry.day_of_month} ${entry.month_of_year}`
}

function ScheduleRow({ entry, index, onEdit }: { entry: ScheduleEntry; index: number; onEdit: () => void }) {
    const queryClient = useQueryClient()
    const { mutate, isPending } = useMutation({
        mutationFn: (enabled: boolean) => toggleScheduleEntry(entry.id, enabled),
        onSuccess: () => queryClient.invalidateQueries({ queryKey: ["schedule"] })
    })

    return (
        <motion.div initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.03, duration: 0.3, ease }}>
            <div className="flex items-center gap-5 px-5 py-3.5 hover:bg-surface2/60 transition-colors border-b border-border">
                <div className="shrink-0">
                    <Toggle checked={entry.enabled} onChange={() => mutate(!entry.enabled)} disabled={isPending} />
                </div>

                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                        <p className={`text-sm font-semibold leading-none ${entry.enabled ? "text-primary" : "text-muted"}`}>{entry.name}</p>
                        {entry.enabled ? <CheckCircle2 size={11} className="text-success" /> : <Circle size={11} className="text-muted" />}
                    </div>
                    <p className="text-[11px] text-secondary font-mono truncate mt-0.5">{entry.task}</p>
                </div>

                <div className="w-56 flex flex-col items-end gap-0.5 shrink-0">
                    <span className="text-[11px] font-mono font-semibold text-primary">{cronDisplay(entry)}</span>
                    {Object.keys(entry.kwargs).length > 0 && <span className="text-[10px] text-muted font-mono truncate max-w-56">{JSON.stringify(entry.kwargs)}</span>}
                </div>

                <button onClick={onEdit} className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold text-secondary border border-border hover:text-primary hover:border-muted transition-colors">
                    <Pencil size={11} />
                    Edit
                </button>
            </div>
        </motion.div>
    )
}

function ScheduleGroup({ title, icon: Icon, entries, startIndex, onEdit }: { title: string; icon: React.ElementType; entries: ScheduleEntry[]; startIndex: number; onEdit: (e: ScheduleEntry) => void }) {
    if (entries.length === 0) return null
    return (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + startIndex * 0.02, duration: 0.4, ease }}>
            <div className="flex flex-col gap-2">
                <div className="flex items-center gap-2 px-1">
                    <Icon size={12} className="text-muted" strokeWidth={1.75} />
                    <span className="text-xs font-medium text-secondary">{title}</span>
                    <span className="text-[10px] text-muted ml-1">{entries.length} entries</span>
                </div>
                <div className="bg-surface border border-border rounded-[var(--radius-card)] shadow-[var(--shadow-border)]">
                    <div className="overflow-hidden rounded-[var(--radius-card)]">
                        {entries.map((entry, i) => (
                            <ScheduleRow key={entry.id} entry={entry} index={startIndex + i} onEdit={() => onEdit(entry)} />
                        ))}
                    </div>
                </div>
            </div>
        </motion.div>
    )
}

export default function SchedulePage() {
    const { data: entries, isLoading, isError } = useSchedule()
    const [editing, setEditing] = useState<ScheduleEntry | null>(null)

    const total = entries?.length ?? 0
    const enabled = entries?.filter((e) => e.enabled).length ?? 0
    const disabled = total - enabled

    const groupKeys = entries ? [...new Set([...Object.keys(GROUP_CONFIG), ...entries.map((e) => e.group)])] : []
    const grouped = groupKeys.map((key) => ({ key, entries: entries?.filter((e) => e.group === key) ?? [] })).filter((g) => g.entries.length > 0)

    return (
        <div className="flex flex-col gap-6">
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between">
                <div>
                    <p className="text-xs text-secondary mb-1">Automation</p>
                    <h1 className="text-4xl font-bold tracking-tight text-primary leading-none">Schedule</h1>
                    <p className="text-xs text-secondary mt-2">When automated jobs run — toggle or edit without a redeploy. Changes take effect within one beat tick.</p>
                </div>
            </motion.div>

            <motion.div initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.4, ease }} className="grid grid-cols-3 gap-2">
                {[
                    { icon: CalendarClock, iconColor: "var(--color-accent)", label: "Total Entries", value: isLoading ? "—" : String(total) },
                    { icon: CheckCircle2, iconColor: "#4ade80", label: "Enabled", value: isLoading ? "—" : String(enabled) },
                    { icon: Circle, iconColor: "var(--color-muted)", label: "Disabled", value: isLoading ? "—" : String(disabled) }
                ].map((t) => (
                    <KpiTile key={t.label} {...t} />
                ))}
            </motion.div>

            {isLoading && (
                <div className="flex flex-col gap-4">
                    {[...Array(2)].map((_, g) => (
                        <div key={g} className="flex flex-col gap-2">
                            <Skeleton className="h-4 w-32 rounded" />
                            <div className="rounded-[var(--radius-card)] overflow-hidden border border-border">
                                {[...Array(4)].map((_, i) => (
                                    <Skeleton key={i} className="h-14 rounded-none" />
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {isError && (
                <div className="py-16 text-center rounded-[var(--radius-card)] bg-surface2 border border-border">
                    <p className="text-sm font-medium text-primary mb-1">Failed to load schedule</p>
                    <p className="text-xs text-secondary">Check that the backend is running</p>
                </div>
            )}

            {!isLoading && !isError && (
                <div className="flex flex-col gap-5">
                    {grouped.map(({ key, entries: groupEntries }, gi) => {
                        const startIndex = grouped.slice(0, gi).reduce((acc, g) => acc + g.entries.length, 0)
                        const config = GROUP_CONFIG[key] ?? { label: key, icon: CalendarClock }
                        return <ScheduleGroup key={key} title={config.label} icon={config.icon} entries={groupEntries} startIndex={startIndex} onEdit={setEditing} />
                    })}
                </div>
            )}

            {editing && <ScheduleEntryModal entry={editing} onClose={() => setEditing(null)} />}
        </div>
    )
}
