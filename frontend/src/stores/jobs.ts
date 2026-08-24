import { defineStore } from "pinia"

import { fetchJobs, triggerJob } from "@/services/api/jobs"
import { loadResource } from "@/stores/helpers/resource"
import { createResourceState } from "@/types/resource"
import type { ResourceState } from "@/types/resource"
import type { Job } from "@/types/job"

export const useJobsStore = defineStore("jobs", {
  state: (): { resource: ResourceState<Job[]> } => ({
    resource: createResourceState<Job[]>(),
  }),
  getters: {
    jobs: (state) => state.resource.data ?? [],
  },
  actions: {
    async fetch() {
      await loadResource(this.resource, fetchJobs)
    },
    async trigger(jobName: string, parameters?: Record<string, unknown>) {
      const result = await triggerJob({ job_name: jobName, parameters })
      if (!result.error) await this.fetch()
      return result
    },
  },
})
