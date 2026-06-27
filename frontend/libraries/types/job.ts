export interface ParameterField {
    name: string
    type: "string" | "integer" | "array" | "enum"
    required: boolean
    default: string | number | null
    description: string
    options?: string[]
}

export interface Job {
    name: string
    display_name: string
    schedule: string
    description: string
    group: string
    parameter_fields: ParameterField[]
    last_run_at?: string | null
    last_run_status?: "running" | "success" | "failure" | null
    last_run_duration?: number | null
    last_run_error?: string | null
}
