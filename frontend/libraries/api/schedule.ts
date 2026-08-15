import client from "./client"
import { ScheduleEntry, ScheduleEntryInput } from "../types/schedule"

export async function getScheduleEntries(): Promise<ScheduleEntry[]> {
    const res = await client.get("/schedule")
    return res.data.data ?? []
}

export async function createScheduleEntry(input: ScheduleEntryInput): Promise<ScheduleEntry> {
    const res = await client.post("/schedule", input)
    if (!res.data.success) throw new Error(res.data.message ?? "Failed to create schedule entry")
    return res.data.data
}

export async function updateScheduleEntry(id: number, input: Partial<ScheduleEntryInput>): Promise<ScheduleEntry> {
    const res = await client.patch(`/schedule/${id}`, input)
    if (!res.data.success) throw new Error(res.data.message ?? "Failed to update schedule entry")
    return res.data.data
}

export async function toggleScheduleEntry(id: number, enabled: boolean): Promise<ScheduleEntry> {
    const res = await client.post(`/schedule/${id}/toggle`, { enabled })
    if (!res.data.success) throw new Error(res.data.message ?? "Failed to toggle schedule entry")
    return res.data.data
}

export async function deleteScheduleEntry(id: number): Promise<void> {
    const res = await client.delete(`/schedule/${id}`)
    if (!res.data.success) throw new Error(res.data.message ?? "Failed to delete schedule entry")
}
