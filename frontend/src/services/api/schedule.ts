import { apiClient } from "./client"
import { unwrap } from "./unwrap"
import type { CreateScheduleEntryRequest, ScheduleEntry, UpdateScheduleEntryRequest } from "@/types/schedule"

export function fetchScheduleEntries() {
  return unwrap<ScheduleEntry[]>(() => apiClient.get("/schedule"))
}

export function createScheduleEntry(request: CreateScheduleEntryRequest) {
  return unwrap<ScheduleEntry>(() => apiClient.post("/schedule", request))
}

export function updateScheduleEntry(entryId: number, request: UpdateScheduleEntryRequest) {
  return unwrap<ScheduleEntry>(() => apiClient.patch(`/schedule/${entryId}`, request))
}

export function toggleScheduleEntry(entryId: number, enabled: boolean) {
  return unwrap<ScheduleEntry>(() => apiClient.post(`/schedule/${entryId}/toggle`, { enabled }))
}

export function deleteScheduleEntry(entryId: number) {
  return unwrap<null>(() => apiClient.delete(`/schedule/${entryId}`))
}

export function resyncSchedule() {
  return unwrap<{ synced: number; failed: string[]; total: number }>(() => apiClient.post("/schedule/resync"))
}
