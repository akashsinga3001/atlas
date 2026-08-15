import client from "./client"
import { PortfolioStats, EquityCurvePoint, PortfolioAnalytics, NavCurvePoint, CashFlow, FlowType, CapitalAllocation } from "../types/portfolio"

export async function getPortfolioStats(): Promise<PortfolioStats> {
    const res = await client.get("/portfolio/stats")
    return res.data.data
}

export async function getEquityCurve(): Promise<EquityCurvePoint[]> {
    const res = await client.get("/portfolio/equity-curve")
    return res.data.data ?? []
}

export async function getPortfolioAnalytics(): Promise<PortfolioAnalytics> {
    const res = await client.get("/portfolio/analytics")
    return res.data.data
}

export async function getCapitalAllocation(): Promise<CapitalAllocation> {
    const res = await client.get("/portfolio/capital-allocation")
    return res.data.data
}

export async function getNavCurve(): Promise<NavCurvePoint[]> {
    const res = await client.get("/portfolio/nav-curve")
    return res.data.data ?? []
}

export async function getCashFlows(): Promise<CashFlow[]> {
    const res = await client.get("/fund/cashflow")
    return res.data.data ?? []
}

export async function createCashFlow(payload: { flow_type: FlowType; amount: number; flow_date: string; note?: string }): Promise<CashFlow> {
    const res = await client.post("/fund/cashflow", payload)
    return res.data.data
}
