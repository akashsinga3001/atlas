export interface CircuitBreaker {
    id: number
    type: string
    enabled: boolean
    params: Record<string, number | string | boolean>
    last_triggered_at: string | null
    last_reason: string | null
    updated_at: string
}

export interface UpdateCircuitBreakerPayload {
    enabled?: boolean
    params?: Record<string, number | string | boolean>
}
