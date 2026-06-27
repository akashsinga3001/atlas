export interface Job {
    name: string
    display_name: string
    schedule: string
    description: string
    group: string
    last_run_at?: string | null
    last_run_status?: "running" | "success" | "failure" | null
    last_run_duration?: number | null
    last_run_error?: string | null
}
