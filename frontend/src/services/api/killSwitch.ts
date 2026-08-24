import { apiClient } from "./client"
import { unwrap } from "./unwrap"
import type { KillSwitch } from "@/types/killSwitch"

export function fetchKillSwitchStatus() {
  return unwrap<KillSwitch>(() => apiClient.get("/kill-switch"))
}

export function activateKillSwitch(reason: string) {
  return unwrap<KillSwitch>(() => apiClient.post("/kill-switch/activate", { reason }))
}

export function deactivateKillSwitch() {
  return unwrap<KillSwitch>(() => apiClient.post("/kill-switch/deactivate"))
}
