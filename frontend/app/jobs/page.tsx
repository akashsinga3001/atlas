"use client"

import { useState } from "react"
import { useJobs } from "@/libraries/hooks/useJobs"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import client from "@/libraries/api/client"
import Skeleton from "@/components/ui/Skeleton"
import { motion, AnimatePresence } from "framer-motion"
import { Play, Loader, CheckCircle, XCircle, Database, TrendingUp, Clock, Zap, AlertCircle, X } from "lucide-react"
import { Job } from "@/libraries/types/job"
import { FieldInput, coerceFieldValue } from "@/components/forms/DynamicFieldInput"

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

const GROUP_CONFIG: Record<string, { label: string; icon: React.ElementType }> = {
    data_pipeline: { label: "Data Pipeline", icon: Database },
    trading: { label: "Trading", icon: TrendingUp }
}

// Parse schedule strings into structured parts
// Handles: "Daily 07:45", "Weekdays 15:20", "Monthly 08:30", "On-demand",
//          "Daily 08:00 + Live every 5m"
function ScheduleDisplay({ schedule }: { schedule: string }) {
    if (schedule === "On-demand") {
        return (
            <div className="flex items-center gap-1.5 shrink-0">
                <Zap size={11} style={{ color: "var(--color-primary)" }} />
                <span className="text-[11px] font-semibold" style={{ color: "var(--color-primary)" }}>
                    On-demand
                </span>
            </div>
        )
    }

    const parts = schedule.split(" + ")

    return (
        <div className="flex flex-col items-end gap-1 shrink-0">
            {parts.map((part) => {
                if (part.startsWith("Live")) {
                    const period = part.replace("Live ", "")
                    return (
                        <div key={part} className="flex items-center gap-1.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-success" />
                            <span className="text-[11px] font-mono text-success">Live</span>
                            <span className="text-[11px] font-mono text-muted">{period}</span>
                        </div>
                    )
                }

                const tokens = part.split(" ")
                const freq = tokens[0] // "Daily" | "Weekdays" | "Monthly"
                const time = tokens[1] // "07:45" | "08:00" etc.

                const freqColor: Record<string, string> = {
                    Daily: "var(--color-secondary)",
                    Weekdays: "var(--color-secondary)",
                    Monthly: "var(--color-primary)"
                }

                return (
                    <div key={part} className="flex items-center gap-2">
                        <span className="text-[10px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded bg-surface2" style={{ color: freqColor[freq] ?? "var(--color-secondary)" }}>
                            {freq}
                        </span>
                        {time && (
                            <div className="flex items-center gap-1">
                                <Clock size={10} className="text-muted" />
                                <span className="text-[12px] font-mono font-semibold text-secondary tabular-nums">{time}</span>
                            </div>
                        )}
                    </div>
                )
            })}
        </div>
    )
}

function JobParamModal({ job, onClose, onSubmit, isPending }: { job: Job; onClose: () => void; onSubmit: (params: Record<string, unknown>) => void; isPending: boolean }) {
    const [values, setValues] = useState<Record<string, string>>(() => {
        const init: Record<string, string> = {}
        job.parameter_fields.forEach((f) => {
            if (f.default != null) init[f.name] = String(f.default)
        })
        return init
    })
    const [errors, setErrors] = useState<Record<string, string>>({})

    const set = (name: string, value: string) => {
        setValues((v) => ({ ...v, [name]: value }))
        setErrors((e) => ({ ...e, [name]: "" }))
    }

    const submit = () => {
        const errs: Record<string, string> = {}
        job.parameter_fields.forEach((f) => {
            if (f.required && !values[f.name]) errs[f.name] = "Required"
        })
        if (Object.keys(errs).length) {
            setErrors(errs)
            return
        }

        const params: Record<string, unknown> = {}
        job.parameter_fields.forEach((f) => {
            const v = values[f.name]
            if (!v) return
            params[f.name] = coerceFieldValue(f, v)
        })
        onSubmit(params)
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div className="absolute inset-0" style={{ background: "var(--overlay-scrim)", backdropFilter: "blur(4px)" }} />
            <motion.div initial={{ opacity: 0, scale: 0.96, y: 8 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.96, y: 8 }} transition={{ duration: 0.18, ease: [0.23, 1, 0.32, 1] }} className="relative w-full max-w-md rounded-[var(--radius-card)] p-6 flex flex-col gap-5 bg-surface border border-border" style={{ boxShadow: "var(--shadow-large)" }} onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-xs text-secondary mb-0.5">Configure Run</p>
                        <h2 className="text-lg font-bold text-primary leading-tight">{job.display_name}</h2>
                    </div>
                    <button onClick={onClose} className="p-1.5 rounded-[var(--radius-card)] text-muted hover:text-primary hover:bg-surface2 transition-colors">
                        <X size={14} />
                    </button>
                </div>

                {/* Fields */}
                <div className="flex flex-col gap-4">
                    {job.parameter_fields.map((field) => (
                        <div key={field.name} className="flex flex-col gap-1.5">
                            <div className="flex items-center justify-between">
                                <label className="text-xs font-semibold text-primary capitalize">{field.name.replace(/_/g, " ")}</label>
                                {field.required ? (
                                    <span className="text-[10px] uppercase tracking-wide font-bold text-primary">
                                        Required
                                    </span>
                                ) : (
                                    <span className="text-[10px] uppercase tracking-wide text-muted">Optional</span>
                                )}
                            </div>
                            {field.description && <p className="text-[11px] text-secondary">{field.description}</p>}
                            <FieldInput field={field} value={values[field.name] ?? ""} onChange={(v) => set(field.name, v)} />
                            {errors[field.name] && <p className="text-[11px] text-danger">{errors[field.name]}</p>}
                        </div>
                    ))}
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end gap-2 pt-1">
                    <button onClick={onClose} className="px-4 py-2 rounded-[var(--radius-card)] text-xs font-semibold text-secondary border border-border hover:border-muted hover:text-primary transition-colors">
                        Cancel
                    </button>
                    <button onClick={submit} disabled={isPending} className="flex items-center gap-1.5 px-4 py-2 rounded-[var(--radius-card)] text-xs font-semibold transition-opacity bg-primary text-bg hover:opacity-90 disabled:opacity-50">
                        {isPending ? <Loader size={11} className="animate-spin" /> : <Play size={11} />}
                        {isPending ? "Queuing" : "Run"}
                    </button>
                </div>
            </motion.div>
        </div>
    )
}

function JobRow({ job, index }: { job: Job; index: number }) {
    const [modalOpen, setModalOpen] = useState(false)
    const queryClient = useQueryClient()
    const hasParams = job.parameter_fields?.length > 0

    const { mutate, isPending } = useMutation({
        mutationFn: (params: Record<string, unknown> = {}) => client.post("/jobs/trigger", { job_name: job.name, parameters: params }),
        onSuccess: () => {
            setModalOpen(false)
            queryClient.invalidateQueries({ queryKey: ["jobs"] })
        }
    })

    const handleRun = () => {
        if (hasParams) setModalOpen(true)
        else mutate({})
    }

    const lastRunStatus = job.last_run_status
    const dotColor = lastRunStatus === "success" ? "var(--color-success)" : lastRunStatus === "failure" ? "var(--color-danger)" : lastRunStatus === "running" || lastRunStatus === "queued" ? "var(--color-warning)" : "var(--color-muted)"

    const lastRunLabel = (() => {
        if (!job.last_run_at) return null
        const d = new Date(job.last_run_at)
        const now = new Date()
        const diffMs = now.getTime() - d.getTime()
        const diffMins = Math.floor(diffMs / 60000)
        const diffHrs = Math.floor(diffMins / 60)
        const diffDays = Math.floor(diffHrs / 24)
        if (diffMins < 1) return "just now"
        if (diffMins < 60) return `${diffMins}m ago`
        if (diffHrs < 24) return `${diffHrs}h ago`
        return `${diffDays}d ago`
    })()

    return (
        <motion.div initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.04, duration: 0.3, ease }}>
            <div className="flex items-center gap-5 px-5 py-3.5 hover:bg-surface2/60 transition-colors border-b border-border">
                {/* Status dot */}
                <div className="w-1.5 h-1.5 rounded-full shrink-0 transition-colors duration-500" style={{ background: dotColor }} />

                {/* Name + description */}
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-primary leading-none mb-0.5">{job.display_name}</p>
                    <p className="text-xs text-secondary truncate">{job.description}</p>
                </div>

                {/* Last run info */}
                <div className="w-44 flex flex-col items-end gap-0.5 shrink-0">
                    {lastRunLabel ? (
                        <>
                            <div className="flex items-center gap-1.5">
                                {lastRunStatus === "success" && <CheckCircle size={11} className="text-success" />}
                                {lastRunStatus === "failure" && <XCircle size={11} className="text-danger" />}
                                {(lastRunStatus === "running" || lastRunStatus === "queued") && <Loader size={11} className="text-warning animate-spin" />}
                                <span className={`text-[11px] font-semibold ${lastRunStatus === "success" ? "text-success" : lastRunStatus === "failure" ? "text-danger" : lastRunStatus === "running" || lastRunStatus === "queued" ? "text-warning" : "text-muted"}`}>{lastRunStatus === "running" ? "Running" : lastRunStatus === "queued" ? "Queued" : lastRunStatus === "success" ? "Succeeded" : "Failed"}</span>
                            </div>
                            <div className="flex items-center gap-1 text-[10px] text-muted">
                                <Clock size={9} />
                                <span className="font-mono">{lastRunLabel}</span>
                                {job.last_run_duration && <span className="font-mono">· {job.last_run_duration.toFixed(1)}s</span>}
                            </div>
                        </>
                    ) : (
                        <span className="text-[11px] text-muted font-mono">Never run</span>
                    )}
                </div>

                {/* Schedule */}
                <div className="w-48 flex justify-end">
                    <ScheduleDisplay schedule={job.schedule} />
                </div>

                {/* Run button */}
                <button onClick={handleRun} disabled={isPending || lastRunStatus === "running" || lastRunStatus === "queued"} className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-[var(--radius-card)] text-xs font-semibold transition-all duration-200 border ${isPending || lastRunStatus === "running" ? "text-secondary border-border opacity-50 cursor-not-allowed" : "text-secondary border-border hover:text-primary hover:bg-surface2"}`}>
                    {isPending ? <Loader size={11} className="animate-spin" /> : <Play size={11} />}
                    {isPending ? "Queuing" : "Run"}
                </button>
            </div>

            <AnimatePresence>{modalOpen && <JobParamModal job={job} onClose={() => setModalOpen(false)} onSubmit={(params) => mutate(params)} isPending={isPending} />}</AnimatePresence>
        </motion.div>
    )
}

function JobGroup({ title, icon: Icon, jobs, startIndex }: { title: string; icon: React.ElementType; jobs: Job[]; startIndex: number }) {
    if (jobs.length === 0) return null
    return (
        <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 + startIndex * 0.02, duration: 0.4, ease }}>
            <div className="flex flex-col gap-2">
                {/* Group header */}
                <div className="flex items-center gap-2 px-1">
                    <Icon size={12} className="text-muted" strokeWidth={1.75} />
                    <span className="text-xs font-medium text-secondary">{title}</span>
                    <span className="text-[10px] text-muted ml-1">{jobs.length} jobs</span>
                </div>

                {/* Rows */}
                <div className="bg-surface border border-border rounded-[var(--radius-card)] shadow-[var(--shadow-border)]">
                    <div className="overflow-hidden rounded-[var(--radius-card)]">
                        {jobs.map((job, i) => (
                            <JobRow key={job.name} job={job} index={startIndex + i} />
                        ))}
                    </div>
                </div>
            </div>
        </motion.div>
    )
}

export default function JobsPage() {
    const { data: jobs, isLoading, isError } = useJobs()

    const automated = jobs?.filter((j) => j.schedule !== "On-demand").length ?? 0
    const manual = jobs?.filter((j) => j.schedule === "On-demand").length ?? 0

    // Derive groups in the order they appear in GROUP_CONFIG, then any unknown groups after
    const groupKeys = jobs ? [...new Set([...Object.keys(GROUP_CONFIG), ...jobs.map((j) => j.group)])] : []
    const grouped = groupKeys.map((key) => ({ key, jobs: jobs?.filter((j) => j.group === key) ?? [] })).filter((g) => g.jobs.length > 0)

    return (
        <div className="flex flex-col gap-6">
            {/* Hero */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between">
                <div className="flex flex-col gap-1.5">
                    <p className="text-xs text-secondary">Automation</p>
                    <h1 className="text-xl font-semibold tracking-tight text-primary leading-none">Jobs</h1>
                </div>
                <div className="flex items-end gap-6 px-4 py-2.5 bg-surface border border-border rounded-[var(--radius-card)]">
                    <div className="flex flex-col items-end gap-0.5">
                        <span className="text-[11px] text-secondary">Scheduled</span>
                        {isLoading ? <Skeleton className="h-6 w-8" /> : <span className="text-2xl font-semibold leading-none text-primary">{automated}</span>}
                    </div>
                    <div className="flex flex-col items-end gap-0.5">
                        <span className="text-[11px] text-secondary">On-demand</span>
                        {isLoading ? <Skeleton className="h-6 w-8" /> : <span className="text-2xl font-semibold leading-none text-primary">{manual}</span>}
                    </div>
                </div>
            </motion.div>

            {/* Loading */}
            {isLoading && (
                <div className="flex flex-col gap-4">
                    {[...Array(2)].map((_, g) => (
                        <div key={g} className="flex flex-col gap-2">
                            <Skeleton className="h-4 w-32 rounded" />
                            <div className="rounded-[var(--radius-card)] overflow-hidden border border-border">
                                {[...Array(5)].map((_, i) => (
                                    <Skeleton key={i} className="h-14 rounded-none" />
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Error */}
            {isError && (
                <div className="py-16 text-center rounded-[var(--radius-card)] bg-surface2 border border-border">
                    <p className="text-sm font-medium text-primary mb-1">Failed to load jobs</p>
                    <p className="text-xs text-secondary">Check that the backend is running</p>
                </div>
            )}

            {/* Job groups */}
            {!isLoading && !isError && (
                <div className="flex flex-col gap-5">
                    {grouped.map(({ key, jobs: groupJobs }, gi) => {
                        const startIndex = grouped.slice(0, gi).reduce((acc, g) => acc + g.jobs.length, 0)
                        const config = GROUP_CONFIG[key] ?? { label: key, icon: Zap }
                        return <JobGroup key={key} title={config.label} icon={config.icon} jobs={groupJobs} startIndex={startIndex} />
                    })}
                </div>
            )}
        </div>
    )
}
