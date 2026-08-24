export type ResourceStatus = "idle" | "loading" | "success" | "error" | "refreshing"

export interface ResourceState<T> {
  data: T | null
  status: ResourceStatus
  error: string | null
  lastUpdatedAt: number | null
}

export function createResourceState<T>(initial: T | null = null): ResourceState<T> {
  return { data: initial, status: "idle", error: null, lastUpdatedAt: null }
}
