import client from "./client"
import { Signal } from "../types/signal"

export async function getSignals(params?: { date_from?: string; date_to?: string; status?: string }): Promise<Signal[]> {
    const res = await client.get("/signals", { params })
    return res.data.data ?? []
}
