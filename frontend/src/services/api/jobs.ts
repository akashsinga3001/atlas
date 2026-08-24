import { apiClient } from "./client"
import { unwrap } from "./unwrap"
import type { Job, JobTriggerRequest } from "@/types/job"

export function fetchJobs() {
  return unwrap<Job[]>(() => apiClient.get("/jobs"))
}

export function triggerJob(request: JobTriggerRequest) {
  return unwrap<null>(() => apiClient.post("/jobs/trigger", request))
}
