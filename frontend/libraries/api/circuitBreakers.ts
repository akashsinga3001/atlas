import client from "./client"
import { CircuitBreaker, UpdateCircuitBreakerPayload } from "../types/circuitBreakers"

export async function getCircuitBreakers(): Promise<CircuitBreaker[]> {
    const res = await client.get("/circuit-breakers")
    return res.data.data ?? []
}

export async function updateCircuitBreaker(id: number, payload: UpdateCircuitBreakerPayload): Promise<CircuitBreaker> {
    const res = await client.patch(`/circuit-breakers/${id}`, payload)
    return res.data.data
}
