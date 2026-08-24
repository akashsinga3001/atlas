import type { ResourceState } from "@/types/resource"
import type { ApiResult } from "@/services/api/types"

/**
 * Runs a fetch against a ResourceState, mutating it in place.
 *
 * A failed refresh sets status to "error" and records the message, but never clears
 * existing data — the screen keeps showing the last known-good state instead of
 * collapsing into a false "no data" empty state. This is the direct fix for the old
 * frontend's "refresh failure looks like empty data" bug.
 */
export async function loadResource<T>(state: ResourceState<T>, fetcher: () => Promise<ApiResult<T>>): Promise<void> {
  state.status = state.data === null ? "loading" : "refreshing"
  state.error = null

  const result = await fetcher()

  if (result.error) {
    state.status = "error"
    state.error = result.message ?? "Request failed"
    return
  }

  state.data = result.data
  state.status = "success"
  state.lastUpdatedAt = Date.now()
}

/** True once lastUpdatedAt is older than thresholdMs — drives a staleness badge without hiding the data itself. */
export function isStale(lastUpdatedAt: number | null, thresholdMs = 60_000): boolean {
  if (lastUpdatedAt === null) return false
  return Date.now() - lastUpdatedAt > thresholdMs
}
