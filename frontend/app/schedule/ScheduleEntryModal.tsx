"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { motion } from "framer-motion"
import { Loader, Save, X } from "lucide-react"
import { ScheduleEntry, ScheduleEntryInput } from "@/libraries/types/schedule"
import { updateScheduleEntry } from "@/libraries/api/schedule"

const CRON_FIELDS: { key: "minute" | "hour" | "day_of_week" | "day_of_month" | "month_of_year"; label: string; hint: string }[] = [
    { key: "minute", label: "Minute", hint: "0-59, */10, 20,50" },
    { key: "hour", label: "Hour", hint: "0-23, 9-15" },
    { key: "day_of_week", label: "Day of Week", hint: "0-6 (Mon=0), 1-5" },
    { key: "day_of_month", label: "Day of Month", hint: "1-31" },
    { key: "month_of_year", label: "Month", hint: "1-12" }
]

export default function ScheduleEntryModal({ entry, onClose }: { entry: ScheduleEntry; onClose: () => void }) {
    const queryClient = useQueryClient()

    const [cron, setCron] = useState({ minute: entry.minute, hour: entry.hour, day_of_week: entry.day_of_week, day_of_month: entry.day_of_month, month_of_year: entry.month_of_year })
    const [description, setDescription] = useState(entry.description ?? "")
    const [kwargsText, setKwargsText] = useState(JSON.stringify(entry.kwargs, null, 2))
    const [jsonError, setJsonError] = useState<string | null>(null)
    const [formError, setFormError] = useState<string | null>(null)

    const { mutate, isPending } = useMutation({
        mutationFn: (input: Partial<ScheduleEntryInput>) => updateScheduleEntry(entry.id, input),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["schedule"] })
            onClose()
        },
        onError: (err: unknown) => setFormError(err instanceof Error ? err.message : "Failed to save changes.")
    })

    const submit = () => {
        setFormError(null)
        let kwargs: Record<string, unknown>
        try {
            kwargs = JSON.parse(kwargsText)
            setJsonError(null)
        } catch {
            setJsonError("Not valid JSON — fix the syntax before saving.")
            return
        }
        mutate({ ...cron, kwargs, description: description || null })
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div className="absolute inset-0" style={{ background: "var(--overlay-scrim)", backdropFilter: "blur(4px)" }} />
            <motion.div
                initial={{ opacity: 0, scale: 0.96, y: 8 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96, y: 8 }}
                transition={{ duration: 0.18, ease: [0.23, 1, 0.32, 1] }}
                className="relative w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-[var(--radius-card)] p-6 flex flex-col gap-5 bg-surface border border-border"
                style={{ boxShadow: "var(--shadow-large)" }}
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-xs text-secondary mb-0.5">Edit Schedule Entry</p>
                        <h2 className="text-lg font-bold text-primary leading-tight">{entry.name}</h2>
                        <p className="text-[11px] text-secondary mt-1 font-mono">{entry.task}</p>
                    </div>
                    <button onClick={onClose} className="p-1.5 rounded-lg text-muted hover:text-primary hover:bg-surface2 transition-colors">
                        <X size={14} />
                    </button>
                </div>

                <div className="grid grid-cols-2 gap-3">
                    {CRON_FIELDS.map((f) => (
                        <div key={f.key} className="flex flex-col gap-1">
                            <label className="text-xs font-semibold text-primary">{f.label}</label>
                            <input
                                type="text"
                                value={cron[f.key]}
                                onChange={(e) => setCron((c) => ({ ...c, [f.key]: e.target.value }))}
                                placeholder={f.hint}
                                className="w-full px-3 py-2 rounded-[var(--radius-card)] text-sm font-mono text-primary bg-surface2 border border-border focus:border-accent focus:outline-none transition-colors"
                            />
                            <span className="text-[10px] text-muted">{f.hint}</span>
                        </div>
                    ))}
                </div>

                <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-primary">Description</label>
                    <input
                        type="text"
                        value={description}
                        onChange={(e) => setDescription(e.target.value)}
                        className="w-full px-3 py-2 rounded-[var(--radius-card)] text-sm text-primary bg-surface2 border border-border focus:border-accent focus:outline-none transition-colors"
                    />
                </div>

                <div className="flex flex-col gap-1.5">
                    <label className="text-xs font-semibold text-primary">Kwargs (JSON)</label>
                    <textarea
                        value={kwargsText}
                        onChange={(e) => {
                            setKwargsText(e.target.value)
                            setJsonError(null)
                        }}
                        rows={6}
                        spellCheck={false}
                        className="w-full px-3 py-2 rounded-[var(--radius-card)] text-xs font-mono text-primary bg-surface2 border border-border focus:border-accent focus:outline-none transition-colors"
                    />
                    {jsonError && <p className="text-[11px] text-danger">{jsonError}</p>}
                </div>

                <p className="text-[11px] text-secondary border border-border rounded-[var(--radius-card)] px-3 py-2">Changes take effect within one beat tick — no restart needed. Editing does not change the task itself, only when/how it runs.</p>

                {formError && <p className="text-[11px] text-danger border border-danger/20 bg-danger/5 rounded-[var(--radius-card)] px-3 py-2">{formError}</p>}

                <div className="flex items-center justify-end gap-2 pt-1">
                    <button onClick={onClose} className="px-4 py-2 rounded-lg text-xs font-semibold text-secondary border border-border hover:border-muted hover:text-primary transition-colors">
                        Cancel
                    </button>
                    <button
                        onClick={submit}
                        disabled={isPending}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-opacity bg-primary text-bg hover:opacity-90 disabled:opacity-50"
                    >
                        {isPending ? <Loader size={11} className="animate-spin" /> : <Save size={11} />}
                        {isPending ? "Saving" : "Save"}
                    </button>
                </div>
            </motion.div>
        </div>
    )
}
