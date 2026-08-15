import client from "./client"
import { KillSwitchStatus } from "../types/killSwitch"

export async function getKillSwitchStatus(): Promise<KillSwitchStatus> {
    const res = await client.get("/kill-switch")
    return res.data.data
}

export async function activateKillSwitch(reason: string): Promise<KillSwitchStatus> {
    const res = await client.post("/kill-switch/activate", { reason })
    if (!res.data.success) throw new Error(res.data.message ?? "Failed to pause new entries")
    return res.data.data
}

export async function deactivateKillSwitch(): Promise<KillSwitchStatus> {
    const res = await client.post("/kill-switch/deactivate")
    if (!res.data.success) throw new Error(res.data.message ?? "Failed to resume new entries")
    return res.data.data
}
