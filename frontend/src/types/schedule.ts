export interface ScheduleEntry {
  id: number
  name: string
  task: string
  minute: string
  hour: string
  day_of_week: string
  day_of_month: string
  month_of_year: string
  kwargs: Record<string, unknown>
  enabled: boolean
  description: string | null
  group: string
  created_at: string
  updated_at: string
}

export interface CreateScheduleEntryRequest {
  name: string
  task: string
  minute?: string
  hour?: string
  day_of_week?: string
  day_of_month?: string
  month_of_year?: string
  kwargs?: Record<string, unknown>
  enabled?: boolean
  description?: string
  group?: string
}

export type UpdateScheduleEntryRequest = Partial<Omit<CreateScheduleEntryRequest, "name">>
