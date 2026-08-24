export interface CircuitBreaker {
  id: number
  type: string
  enabled: boolean
  params: Record<string, unknown>
  last_triggered_at: string | null
  last_reason: string | null
  updated_at: string
}

export interface UpdateCircuitBreakerRequest {
  enabled?: boolean
  params?: Record<string, unknown>
}
