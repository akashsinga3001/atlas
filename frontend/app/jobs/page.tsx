"use client"

import { useState, useRef, useEffect } from "react"
import { useJobs } from "@/libraries/hooks/useJobs"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import client from "@/libraries/api/client"
import Skeleton from "@/components/ui/Skeleton"
import { motion, AnimatePresence } from "framer-motion"
import { Play, Loader, CheckCircle, XCircle, Database, TrendingUp, Clock, Zap, AlertCircle, X, ChevronDown } from "lucide-react"
import { Job, ParameterField } from "@/libraries/types/job"

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
                <Zap size={11} style={{ color: "var(--color-accent)" }} />
                <span className="text-[11px] font-semibold" style={{ color: "var(--color-accent)" }}>
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
                            <span className="w-1.5 h-1.5 rounded-full bg-green-400" style={{ boxShadow: "0 0 5px rgba(74,222,128,0.6)" }} />
                            <span className="text-[11px] font-mono text-green-400">Live</span>
                            <span className="text-[11px] font-mono text-muted">{period}</span>
                        </div>
                    )
                }

                const tokens = part.split(" ")
                const freq = tokens[0] // "Daily" | "Weekdays" | "Monthly"
                const time = tokens[1] // "07:45" | "08:00" etc.

                const freqColor: Record<string, string> = {
                    Daily: "rgba(255,255,255,0.35)",
                    Weekdays: "rgba(255,255,255,0.35)",
                    Monthly: "rgba(212,160,23,0.7)"
                }

                return (
                    <div key={part} className="flex items-center gap-2">
                        <span className="text-[9px] font-bold uppercase tracking-[0.12em] px-1.5 py-0.5 rounded" style={{ background: "rgba(255,255,255,0.06)", color: freqColor[freq] ?? "rgba(255,255,255,0.35)" }}>
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

function EnumSelect({ options, value, onChange, required }: { options: string[]; value: string; onChange: (v: string) => void; required: boolean }) {
    const [open, setOpen] = useState(false)
    const ref = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
        }
        document.addEventListener("mousedown", handler)
        return () => document.removeEventListener("mousedown", handler)
    }, [])

    const displayed = value || (required ? options[0] : "")

    return (
        <div ref={ref} className="relative">
            <button type="button" onClick={() => setOpen((o) => !o)} className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-mono text-primary border border-white/8 hover:border-white/16 focus:border-accent/40 focus:outline-none transition-colors" style={{ background: "var(--color-surface2)" }}>
                <span className={displayed ? "text-primary" : "text-muted"}>{displayed || "— optional —"}</span>
                <ChevronDown size={12} className={`text-muted transition-transform duration-150 ${open ? "rotate-180" : ""}`} />
            </button>

            <AnimatePresence>
                {open && (
                    <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.12 }} className="absolute z-10 left-0 right-0 mt-1 rounded-xl overflow-hidden" style={{ background: "var(--color-surface2)", border: "1px solid rgba(255,255,255,0.1)", boxShadow: "0 8px 32px rgba(0,0,0,0.5)" }}>
                        {!required && (
                            <button
                                type="button"
                                onClick={() => {
                                    onChange("")
                                    setOpen(false)
                                }}
                                className="w-full text-left px-3 py-2.5 text-sm font-mono text-muted hover:bg-white/4 transition-colors"
                            >
                                — optional —
                            </button>
                        )}
                        {options.map((o) => (
                            <button
                                key={o}
                                type="button"
                                onClick={() => {
                                    onChange(o)
                                    setOpen(false)
                                }}
                                className={`w-full text-left px-3 py-2.5 text-sm font-mono transition-colors flex items-center justify-between ${value === o ? "text-accent" : "text-primary hover:bg-white/4"}`}
                                style={value === o ? { background: "rgba(212,160,23,0.08)" } : {}}
                            >
                                {o}
                                {value === o && <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--color-accent)" }} />}
                            </button>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

function FieldInput({ field, value, onChange }: { field: ParameterField; value: string; onChange: (v: string) => void }) {
    const base = "w-full px-3 py-2 rounded-lg text-sm font-mono text-primary bg-transparent border border-white/8 focus:border-accent/40 focus:outline-none transition-colors"

    if (field.type === "enum" && field.options) {
        return <EnumSelect options={field.options} value={value} onChange={onChange} required={field.required} />
    }

    if (field.type === "integer") {
        return <input type="number" value={value} onChange={(e) => onChange(e.target.value)} placeholder={field.default != null ? String(field.default) : undefined} className={base} />
    }

    if (field.type === "array") {
        return <input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder="comma-separated values" className={base} />
    }

    return <input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={field.default != null ? String(field.default) : undefined} className={base} />
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
            if (f.type === "integer") params[f.name] = parseInt(v, 10)
            else if (f.type === "array")
                params[f.name] = v
                    .split(",")
                    .map((s) => s.trim())
                    .filter(Boolean)
            else params[f.name] = v
        })
        onSubmit(params)
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div className="absolute inset-0" style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)" }} />
            <motion.div initial={{ opacity: 0, scale: 0.96, y: 8 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.96, y: 8 }} transition={{ duration: 0.18, ease: [0.23, 1, 0.32, 1] }} className="relative w-full max-w-md rounded-2xl p-6 flex flex-col gap-5" style={{ background: "var(--color-surface)", border: "1px solid rgba(255,255,255,0.08)", boxShadow: "0 24px 64px rgba(0,0,0,0.6)" }} onClick={(e) => e.stopPropagation()}>
                {/* Header */}
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-[10px] uppercase tracking-[0.2em] text-secondary mb-0.5">Configure Run</p>
                        <h2 className="text-lg font-bold text-primary leading-tight">{job.display_name}</h2>
                    </div>
                    <button onClick={onClose} className="p-1.5 rounded-lg text-muted hover:text-primary hover:bg-white/6 transition-colors">
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
                                    <span className="text-[9px] uppercase tracking-[0.12em] font-bold" style={{ color: "var(--color-accent)" }}>
                                        Required
                                    </span>
                                ) : (
                                    <span className="text-[9px] uppercase tracking-[0.12em] text-muted">Optional</span>
                                )}
                            </div>
                            {field.description && <p className="text-[11px] text-secondary">{field.description}</p>}
                            <FieldInput field={field} value={values[field.name] ?? ""} onChange={(v) => set(field.name, v)} />
                            {errors[field.name] && <p className="text-[11px] text-red-400">{errors[field.name]}</p>}
                        </div>
                    ))}
                </div>

                {/* Actions */}
                <div className="flex items-center justify-end gap-2 pt-1">
                    <button onClick={onClose} className="px-4 py-2 rounded-lg text-xs font-semibold text-secondary border border-white/8 hover:border-white/20 hover:text-primary transition-colors">
                        Cancel
                    </button>
                    <button onClick={submit} disabled={isPending} className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-semibold transition-all border" style={{ background: "rgba(212,160,23,0.12)", color: "var(--color-accent)", borderColor: "rgba(212,160,23,0.25)" }}>
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
    const dotColor = lastRunStatus === "success" ? "bg-green-400" : lastRunStatus === "failure" ? "bg-red-400" : lastRunStatus === "running" ? "bg-amber-400" : "bg-muted"
    const dotGlow = lastRunStatus === "success" ? "0 0 6px rgba(74,222,128,0.5)" : lastRunStatus === "failure" ? "0 0 6px rgba(248,113,113,0.5)" : lastRunStatus === "running" ? "0 0 6px rgba(251,191,36,0.5)" : "none"

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
            <div className="flex items-center gap-5 px-5 py-3.5 hover:bg-white/2 transition-colors" style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                {/* Status dot */}
                <div className={`w-1.5 h-1.5 rounded-full shrink-0 transition-colors duration-500 ${dotColor}`} style={{ boxShadow: dotGlow }} />

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
                                {lastRunStatus === "success" && <CheckCircle size={11} className="text-green-400" />}
                                {lastRunStatus === "failure" && <XCircle size={11} className="text-red-400" />}
                                {lastRunStatus === "running" && <Loader size={11} className="text-amber-400 animate-spin" />}
                                <span className={`text-[11px] font-semibold ${lastRunStatus === "success" ? "text-green-400" : lastRunStatus === "failure" ? "text-red-400" : lastRunStatus === "running" ? "text-amber-400" : "text-muted"}`}>{lastRunStatus === "running" ? "Running" : lastRunStatus === "success" ? "Succeeded" : "Failed"}</span>
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
                <button onClick={handleRun} disabled={isPending || lastRunStatus === "running"} className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border ${isPending || lastRunStatus === "running" ? "text-secondary border-white/8 opacity-50 cursor-not-allowed" : "text-accent border-accent/20 hover:bg-accent/10"}`}>
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
                    <span className="text-[10px] uppercase tracking-[0.15em] font-medium text-secondary">{title}</span>
                    <span className="text-[10px] text-muted ml-1">{jobs.length} jobs</span>
                </div>

                {/* Rows */}
                <div className="rounded-xl overflow-hidden" style={{ background: "var(--color-surface)", border: "1px solid rgba(255,255,255,0.05)" }}>
                    {jobs.map((job, i) => (
                        <JobRow key={job.name} job={job} index={startIndex + i} />
                    ))}
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
                <div>
                    <p className="text-[10px] uppercase tracking-[0.2em] text-secondary mb-1">Automation</p>
                    <h1 className="text-4xl font-bold tracking-tight text-primary leading-none">Jobs</h1>
                </div>
                <div className="flex items-end gap-8">
                    <div className="flex flex-col items-end gap-1">
                        <span className="text-[10px] uppercase tracking-[0.15em] text-secondary">Scheduled</span>
                        {isLoading ? <Skeleton className="h-12 w-16" /> : <span className="text-5xl font-bold font-mono leading-none text-primary">{automated}</span>}
                    </div>
                    <div className="flex flex-col items-end gap-1">
                        <span className="text-[10px] uppercase tracking-[0.15em] text-secondary">On-demand</span>
                        {isLoading ? <Skeleton className="h-12 w-16" /> : <span className="text-5xl font-bold font-mono leading-none text-accent">{manual}</span>}
                    </div>
                </div>
            </motion.div>

            {/* Loading */}
            {isLoading && (
                <div className="flex flex-col gap-4">
                    {[...Array(2)].map((_, g) => (
                        <div key={g} className="flex flex-col gap-2">
                            <Skeleton className="h-4 w-32 rounded" />
                            <div className="rounded-xl overflow-hidden" style={{ border: "1px solid rgba(255,255,255,0.05)" }}>
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
                <div className="py-16 text-center rounded-2xl bg-surface2 border border-white/4">
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
