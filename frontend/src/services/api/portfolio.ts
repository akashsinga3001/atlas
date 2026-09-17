import { apiClient } from "./client"
import { unwrap } from "./unwrap"
import type { CapitalAllocation, EquityCurvePoint, LiveAccountValue, NavCurvePoint, PortfolioAnalytics, PortfolioStats, SectorExposure, StrategyPerformance, TodayPnlSummary } from "@/types/portfolio"

export function fetchLiveAccountValue() {
  return unwrap<LiveAccountValue>(() => apiClient.get("/portfolio/live"))
}

export function fetchTodayPnl() {
  return unwrap<TodayPnlSummary>(() => apiClient.get("/portfolio/today-pnl"))
}

export function fetchStrategyPerformance() {
  return unwrap<StrategyPerformance[]>(() => apiClient.get("/portfolio/strategy-performance"))
}

export function fetchSectorExposure() {
  return unwrap<SectorExposure>(() => apiClient.get("/portfolio/sector-exposure"))
}

export function fetchPortfolioStats() {
  return unwrap<PortfolioStats>(() => apiClient.get("/portfolio/stats"))
}

export function fetchEquityCurve() {
  return unwrap<EquityCurvePoint[]>(() => apiClient.get("/portfolio/equity-curve"))
}

export function fetchNavCurve() {
  return unwrap<NavCurvePoint[]>(() => apiClient.get("/portfolio/nav-curve"))
}

export function fetchCapitalAllocation() {
  return unwrap<CapitalAllocation>(() => apiClient.get("/portfolio/capital-allocation"))
}

export function fetchPortfolioAnalytics() {
  return unwrap<PortfolioAnalytics>(() => apiClient.get("/portfolio/analytics"))
}
