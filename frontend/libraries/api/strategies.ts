import client from "./client"
import { Strategy, StrategyVersion } from "../types/strategy"

export interface PydanticFieldError {
    type: string
    loc: (string | number)[]
    msg: string
}

export class StrategyConfigError extends Error {
    fieldErrors: PydanticFieldError[]

    constructor(message: string, fieldErrors: PydanticFieldError[] = []) {
        super(message)
        this.fieldErrors = fieldErrors
    }
}

export async function getStrategies(): Promise<Strategy[]> {
    const res = await client.get("/strategies")
    return res.data.data ?? []
}

export async function getVersionHistory(strategyId: number): Promise<StrategyVersion[]> {
    const res = await client.get(`/strategies/${strategyId}/versions`)
    return res.data.data ?? []
}

export async function createVersion(strategyId: number, config: Record<string, unknown>): Promise<StrategyVersion> {
    const res = await client.post(`/strategies/${strategyId}/versions`, { config })
    if (!res.data.success) throw new StrategyConfigError(res.data.message, res.data.errors?.field_errors ?? [])
    return res.data.data
}

export async function activateVersion(strategyId: number, versionId: number): Promise<StrategyVersion> {
    const res = await client.post(`/strategies/${strategyId}/versions/${versionId}/activate`)
    if (!res.data.success) throw new StrategyConfigError(res.data.message)
    return res.data.data
}
