import { apiClient } from "./client"
import { unwrap } from "./unwrap"
import type { Strategy, StrategyRun, StrategyVersion } from "@/types/strategy"

export function fetchStrategies() {
  return unwrap<Strategy[]>(() => apiClient.get("/strategies"))
}

export function setStrategyActive(strategyId: number, isActive: boolean) {
  return unwrap<Strategy>(() => apiClient.patch(`/strategies/${strategyId}`, { is_active: isActive }))
}

export function fetchVersionHistory(strategyId: number) {
  return unwrap<StrategyVersion[]>(() => apiClient.get(`/strategies/${strategyId}/versions`))
}

export function fetchRunHistory(strategyId: number) {
  return unwrap<StrategyRun[]>(() => apiClient.get(`/strategies/${strategyId}/runs`))
}

export function createVersion(strategyId: number, config: Record<string, unknown>) {
  return unwrap<StrategyVersion>(() => apiClient.post(`/strategies/${strategyId}/versions`, { config }))
}

export function activateVersion(strategyId: number, versionId: number) {
  return unwrap<StrategyVersion>(() => apiClient.post(`/strategies/${strategyId}/versions/${versionId}/activate`))
}
