import client from "./client"
import { OptionsPosition } from "../types/options"

export async function getOptionsPositions(status?: string): Promise<OptionsPosition[]> {
    const res = await client.get("/options/positions", { params: status ? { status } : {} })
    return res.data.data ?? []
}
