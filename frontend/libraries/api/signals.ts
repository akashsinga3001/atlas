import client from "./client"
import { Signal } from "../types/signal"

export async function getSignals(params?: { date_from?: string; date_to?: string; status?: string; strategy?: string }): Promise<Signal[]> {
    const res = await client.get("/signals", { params })
    return res.data.data ?? []
}

export interface SignalForwardDataPoint {
    date: string
    close: number
    stop_price: number | null
    atr_14: number | null
    mtm_pct: number | null
    exit_triggered: boolean
}

export interface SignalPerformanceSummary {
    signal_close: number | null
    latest_close: number | null
    perf_since_signal: number | null
    max_close: number | null
    max_perf: number | null
    days_since_signal: number
    exit_triggered_on: string | null
    trade_pnl_pct: number | null
    simulated: boolean
}

export interface SignalPerformance {
    signal: Signal & {
        fill_price: number | null
        fill_quantity: number | null
        entry_date: string | null
        exit_date: string | null
        exit_reason: string | null
        timeout_date: string | null
    }
    forward_data: SignalForwardDataPoint[]
    summary: SignalPerformanceSummary
}

export async function getSignalPerformance(signalId: number): Promise<SignalPerformance> {
    const res = await client.get(`/signals/${signalId}/performance`)
    return res.data.data
}
