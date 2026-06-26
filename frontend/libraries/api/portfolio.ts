import client from "./client"
import { PortfolioStats, EquityCurvePoint } from "../types/portfolio"

export async function getPortfolioStats(): Promise<PortfolioStats> {
    const res = await client.get("/portfolio/stats")
    return res.data.data
}

export async function getEquityCurve(): Promise<EquityCurvePoint[]> {
    const res = await client.get("/portfolio/equity-curve")
    return res.data.data ?? []
}
