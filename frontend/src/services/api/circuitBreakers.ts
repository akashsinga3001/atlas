import { apiClient } from "./client"
import { unwrap } from "./unwrap"
import type { CircuitBreaker, UpdateCircuitBreakerRequest } from "@/types/circuitBreaker"

export function fetchCircuitBreakers() {
  return unwrap<CircuitBreaker[]>(() => apiClient.get("/circuit-breakers"))
}

export function updateCircuitBreaker(breakerId: number, request: UpdateCircuitBreakerRequest) {
  return unwrap<CircuitBreaker>(() => apiClient.patch(`/circuit-breakers/${breakerId}`, request))
}
