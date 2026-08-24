import type { ConfigField } from "./strategy"

export type JobRunStatus = "queued" | "running" | "success" | "failure" | "stale"

export interface Job {
  name: string
  display_name: string
  description: string
  group: string
  schedule: string
  parameter_fields: ConfigField[]
  last_run_at: string | null
  last_run_status: JobRunStatus | null
  last_run_duration: number | null
  last_run_error: string | null
}

export interface JobTriggerRequest {
  job_name: string
  parameters?: Record<string, unknown>
}
