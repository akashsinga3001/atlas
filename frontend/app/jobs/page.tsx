"use client"

import { useState } from "react"
import { useJobs } from "@/libraries/hooks/useJobs"
import { useMutation } from "@tanstack/react-query"
import client from "@/libraries/api/client"
import Skeleton from "@/components/ui/Skeleton"
import { motion } from "framer-motion"
import { Play, Loader, CheckCircle, Database, TrendingUp, Clock, Zap, RefreshCw } from "lucide-react"
import { Job } from "@/libraries/types/job"

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

const DATA_PIPELINE_JOBS = ["KITE_TOKEN_REFRESH", "SECURITIES_IMPORT", "SECURITIES_ENRICHMENT", "OHLCV_IMPORT", "FEATURE_GENERATION"]
const TRADING_JOBS = ["STRATEGY_EXECUTION", "TRADE_ENTRY", "TRADE_EXIT", "POSITION_SYNC", "TRADE_RECONCILIATION"]

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

function JobRow({ job, index }: { job: Job; index: number }) {
    const [triggered, setTriggered] = useState(false)

    const { mutate, isPending } = useMutation({
        mutationFn: () => client.post("/jobs/trigger", { job_name: job.name }),
        onSuccess: () => {
            setTriggered(true)
            setTimeout(() => setTriggered(false), 4000)
        }
    })

    return (
        <motion.div initial={{ opacity: 0, x: -6 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.04, duration: 0.3, ease }}>
            <div className="flex items-center gap-5 px-5 py-3.5 hover:bg-white/2 transition-colors" style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                {/* Status dot */}
                <div className={`w-1.5 h-1.5 rounded-full shrink-0 transition-colors duration-500 ${triggered ? "bg-green-400" : "bg-muted"}`} style={triggered ? { boxShadow: "0 0 6px rgba(74,222,128,0.5)" } : {}} />

                {/* Name + description */}
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-primary leading-none mb-0.5">{job.display_name}</p>
                    <p className="text-xs text-secondary truncate">{job.description}</p>
                </div>

                {/* Schedule */}
                <div className="w-52 flex justify-end">
                    <ScheduleDisplay schedule={job.schedule} />
                </div>

                {/* Run button */}
                <button onClick={() => mutate()} disabled={isPending || triggered} className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border ${triggered ? "text-green-400 border-green-400/20" : isPending ? "text-secondary border-white/8 opacity-50 cursor-not-allowed" : "text-accent border-accent/20 hover:bg-accent/10"}`} style={triggered ? { background: "rgba(74,222,128,0.06)" } : {}}>
                    {isPending ? <Loader size={11} className="animate-spin" /> : triggered ? <CheckCircle size={11} /> : <Play size={11} />}
                    {triggered ? "Done" : isPending ? "Running" : "Run"}
                </button>
            </div>
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

    const pipeline = jobs?.filter((j) => DATA_PIPELINE_JOBS.includes(j.name)) ?? []
    const trading = jobs?.filter((j) => TRADING_JOBS.includes(j.name)) ?? []
    const automated = jobs?.filter((j) => j.schedule !== "On-demand").length ?? 0
    const manual = jobs?.filter((j) => j.schedule === "On-demand").length ?? 0

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
                    <JobGroup title="Data Pipeline" icon={Database} jobs={pipeline} startIndex={0} />
                    <JobGroup title="Trading" icon={TrendingUp} jobs={trading} startIndex={pipeline.length} />
                </div>
            )}
        </div>
    )
}
