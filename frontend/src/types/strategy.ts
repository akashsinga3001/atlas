export type StrategyRunStatus = "PENDING" | "RUNNING" | "COMPLETED" | "FAILED"

export type ConfigFieldType = "string" | "integer" | "number" | "enum" | "array"

export interface ConfigField {
  name: string
  type: ConfigFieldType
  required: boolean
  default: unknown
  description: string
  options?: unknown[]
}

export interface StrategyVersion {
  id: number
  strategy_id: number
  version: number
  config: Record<string, unknown>
  implementation_class: string
  exit_evaluator_class: string | null
  is_active: boolean
  created_at: string
}

export interface Strategy {
  id: number
  code: string
  name: string
  is_active: boolean
  has_config_schema: boolean
  config_fields: ConfigField[]
  active_version: StrategyVersion | null
  version_count: number
  open_positions_count: number
  last_run_status: StrategyRunStatus | null
  last_run_at: string | null
}

export interface StrategyRun {
  id: number
  strategy_version_id: number
  version: number
  status: StrategyRunStatus
  started_at: string | null
  completed_at: string | null
  signal_count: number | null
  error_message: string | null
}
