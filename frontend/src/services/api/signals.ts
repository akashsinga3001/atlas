import { apiClient } from "./client"
import { unwrap } from "./unwrap"
import type { Signal, SignalPerformance } from "@/types/signal"

export interface SignalFilters {
  date_from?: string
  date_to?: string
  status?: string
  strategy?: string
}

export function fetchSignals(filters: SignalFilters = {}) {
  return unwrap<Signal[]>(() => apiClient.get("/signals", { params: filters }))
}

export function fetchSignalPerformance(signalId: number) {
  return unwrap<SignalPerformance>(() => apiClient.get(`/signals/${signalId}/performance`))
}
