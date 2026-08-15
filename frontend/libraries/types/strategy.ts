import { ParameterField } from "./job"

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
    config_fields: ParameterField[]
    active_version: StrategyVersion | null
    version_count: number
}
