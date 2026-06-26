"use client"

import { useJobs } from "@/libraries/hooks/useJobs"
import { useMutation } from "@tanstack/react-query"
import client from "@/libraries/api/client"
import PageHeader from "@/components/layout/PageHeader"
import Card from "@/components/ui/Card"
import Skeleton from "@/components/ui/Skeleton"
import EmptyState from "@/components/ui/EmptyState"
import { Settings, Play, Loader } from "lucide-react"
import { Job } from "@/libraries/types/job"
import { useState } from "react"

function JobCard({ job }: { job: Job }) {
    const [triggered, setTriggered] = useState(false)

    const { mutate, isPending } = useMutation({
        mutationFn: () => client.post("/jobs/trigger", { job_name: job.name }),
        onSuccess: () => {
            setTriggered(true)
            setTimeout(() => setTriggered(false), 3000)
        }
    })

    return (
        <Card className="flex items-start justify-between gap-4">
            <div className="flex flex-col gap-1 min-w-0">
                <p className="text-sm font-semibold text-primary">{job.display_name}</p>
                <p className="text-xs text-secondary">{job.description}</p>
                <p className="text-xs text-accent font-mono mt-1">{job.schedule}</p>
            </div>
            <button onClick={() => mutate()} disabled={isPending} className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-surface2 border border-border text-secondary hover:text-primary hover:border-accent/40 transition-colors disabled:opacity-50">
                {isPending ? <Loader size={12} className="animate-spin" /> : <Play size={12} />}
                {triggered ? "Triggered" : "Run"}
            </button>
        </Card>
    )
}

export default function JobsPage() {
    const { data: jobs, isLoading, isError } = useJobs()

    return (
        <div>
            <PageHeader title="Jobs" subtitle="Manage and trigger background tasks" />
            {isLoading && (
                <div className="flex flex-col gap-3">
                    {[...Array(6)].map((_, i) => (
                        <Skeleton key={i} className="h-20 w-full" />
                    ))}
                </div>
            )}
            {isError && <EmptyState icon={Settings} title="Failed to load jobs" description="Check that the backend is running" />}
            {!isLoading && !isError && jobs && (
                <div className="grid grid-cols-2 gap-3">
                    {jobs.map((job) => (
                        <JobCard key={job.name} job={job} />
                    ))}
                </div>
            )}
        </div>
    )
}
