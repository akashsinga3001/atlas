import type { APIResponse } from "@/types/api"
import type { ApiResult } from "./types"

/** Runs an Axios call returning APIResponse<T> and flattens it into { error, data }, catching failures here so components/stores never need try/catch. */
export async function unwrap<T>(call: () => Promise<{ data: APIResponse<T> }>): Promise<ApiResult<T>> {
  try {
    const response = await call()
    if (!response.data.success) {
      return { error: true, data: null, message: response.data.message }
    }
    return { error: false, data: response.data.data }
  } catch (err) {
    const message = err instanceof Error ? err.message : "Request failed"
    return { error: true, data: null, message }
  }
}
