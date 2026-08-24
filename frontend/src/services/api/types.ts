export interface ApiResult<T> {
  error: boolean
  data: T | null
  message?: string
}
