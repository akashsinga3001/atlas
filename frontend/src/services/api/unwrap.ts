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
  } catch (err: any) {
    // Backend error responses (4xx/5xx) carry { success, message, ... } in the body, same shape
    // as a "success: false" 200 — prefer that over Axios's generic "Request failed with status
    // code NNN" so a real backend message (e.g. a NotFoundError's detail) still reaches the UI
    // now that the backend returns correct HTTP status codes instead of always 200.
    const backendMessage = err?.response?.data?.message
    const message = backendMessage ?? (err instanceof Error ? err.message : "Request failed")
    return { error: true, data: null, message }
  }
}
