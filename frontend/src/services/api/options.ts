import { apiClient } from "./client"
import { unwrap } from "./unwrap"
import type { OptionsPosition, OptionsPositionStatus } from "@/types/options"

export function fetchOptionsPositions(status?: OptionsPositionStatus) {
  return unwrap<OptionsPosition[]>(() => apiClient.get("/options/positions", { params: status ? { status } : undefined }))
}
