import { defineStore } from "pinia"

import { createScheduleEntry, deleteScheduleEntry, fetchScheduleEntries, resyncSchedule, toggleScheduleEntry, updateScheduleEntry } from "@/services/api/schedule"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { CreateScheduleEntryRequest, ScheduleEntry, UpdateScheduleEntryRequest } from "@/types/schedule"

export const useScheduleStore = defineStore("schedule", {
  state: (): { resource: ResourceState<ScheduleEntry[]> } => ({
    resource: createResourceState<ScheduleEntry[]>(),
  }),
  getters: {
    entries: (state) => state.resource.data ?? [],
  },
  actions: {
    async fetch() {
      await loadResource(this.resource, fetchScheduleEntries)
    },
    async create(request: CreateScheduleEntryRequest) {
      const result = await createScheduleEntry(request)
      if (!result.error) await this.fetch()
      return result
    },
    async update(entryId: number, request: UpdateScheduleEntryRequest) {
      const result = await updateScheduleEntry(entryId, request)
      if (!result.error) await this.fetch()
      return result
    },
    async toggle(entryId: number, enabled: boolean) {
      const result = await toggleScheduleEntry(entryId, enabled)
      if (!result.error) await this.fetch()
      return result
    },
    async remove(entryId: number) {
      const result = await deleteScheduleEntry(entryId)
      if (!result.error) await this.fetch()
      return result
    },
    async resync() {
      return resyncSchedule()
    },
  },
})
