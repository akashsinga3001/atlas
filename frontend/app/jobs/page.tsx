"use client"

import { useState } from "react"
import { useJobs } from "@/libraries/hooks/useJobs"
import { useMutation } from "@tanstack/react-query"
import client from "@/libraries/api/client"
import Skeleton from "@/components/ui/Skeleton"
import { motion } from "framer-motion"
import { Play, Loader, CheckCircle } from "lucide-react"
import { Job } from "@/libraries/types/job"

const ease: [number, number, number, number] = [0.23, 1, 0.32, 1]

function JobRow({ job, index }: { job: Job; index: number }) {
    const [triggered, setTriggered] = useState(false)

    const { mutate, isPending } = useMutation({
        mutationFn: () => client.post("/jobs/trigger", { job_name: job.name }),
        onSuccess: () => {
            setTriggered(true)
            setTimeout(() => setTriggered(false), 3000)
        }
    })

    return (
        <motion.div initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: index * 0.04, duration: 0.35, ease }}>
            <div className="flex items-center gap-5 px-5 py-4 hover:bg-white/2 transition-colors" style={{ borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
                {/* Status dot */}
                <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${triggered ? "bg-green-400" : "bg-muted"}`} />

                {/* Name + description */}
                <div className="flex-1 min-w-0">
                    <p className="text-sm font-semibold text-primary leading-none mb-1">{job.display_name}</p>
                    <p className="text-xs text-secondary truncate">{job.description}</p>
                </div>

                {/* Schedule */}
                <span className="shrink-0 text-[10px] font-mono px-2.5 py-1 rounded-md border text-muted" style={{ background: "rgba(255,255,255,0.02)", borderColor: "rgba(255,255,255,0.06)" }}>
                    {job.schedule}
                </span>

                {/* Run button */}
                <button onClick={() => mutate()} disabled={isPending || triggered} className={`shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all duration-200 border ${triggered ? "text-green-400 border-green-400/20" : isPending ? "text-secondary border-white/8 opacity-50" : "text-accent border-accent/20 hover:bg-accent/10"}`} style={triggered ? { background: "rgba(74,222,128,0.06)" } : {}}>
                    {isPending ? <Loader size={11} className="animate-spin" /> : triggered ? <CheckCircle size={11} /> : <Play size={11} />}
                    {triggered ? "Done" : isPending ? "Running" : "Run"}
                </button>
            </div>
        </motion.div>
    )
}

export default function JobsPage() {
    const { data: jobs, isLoading, isError } = useJobs()

    return (
        <div className="flex flex-col gap-6">
            {/* Hero */}
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4, ease }} className="flex items-end justify-between">
                <div>
                    <p className="text-[10px] uppercase tracking-[0.2em] text-secondary mb-1">Automation</p>
                    <h1 className="text-4xl font-bold tracking-tight text-primary leading-none">Jobs</h1>
                </div>
                <div className="flex flex-col items-end gap-1">
                    <span className="text-[10px] uppercase tracking-[0.15em] text-secondary">Configured</span>
                    {isLoading ? <Skeleton className="h-12 w-16" /> : <span className="text-5xl font-bold font-mono leading-none text-primary">{jobs?.length ?? 0}</span>}
                </div>
            </motion.div>

            {/* Job list */}
            <motion.div initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.4, ease }}>
                <div className="rounded-2xl overflow-hidden" style={{ background: "var(--color-surface)", border: "1px solid rgba(255,255,255,0.05)" }}>
                    {/* List header */}
                    <div className="flex items-center gap-5 px-5 py-3" style={{ borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                        <div className="w-1.5 shrink-0" />
                        <span className="flex-1 text-[10px] uppercase tracking-[0.15em] text-secondary font-medium">Job</span>
                        <span className="shrink-0 text-[10px] uppercase tracking-[0.15em] text-secondary font-medium w-40 text-center">Schedule</span>
                        <span className="shrink-0 w-20" />
                    </div>

                    {isLoading && (
                        <div className="flex flex-col gap-0">
                            {[...Array(6)].map((_, i) => (
                                <Skeleton key={i} className="h-16 rounded-none" />
                            ))}
                        </div>
                    )}
                    {isError && (
                        <div className="py-16 text-center">
                            <p className="text-sm font-medium text-primary mb-1">Failed to load jobs</p>
                            <p className="text-xs text-secondary">Check that the backend is running</p>
                        </div>
                    )}
                    {!isLoading && !isError && jobs?.map((job, i) => <JobRow key={job.name} job={job} index={i} />)}
                </div>
            </motion.div>
        </div>
    )
}
