import client from "./client"
import { Trade } from "../types/trade"

export async function getTrades(status?: string): Promise<Trade[]> {
    const res = await client.get("/trades", { params: status ? { status } : {} })
    return res.data.data ?? []
}
