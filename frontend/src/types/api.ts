export interface APIResponse<T> {
  success: boolean
  message: string
  data: T | null
  errors: Record<string, unknown> | null
  meta: Record<string, unknown> | null
}
