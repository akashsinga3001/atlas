import { apiClient } from "./client"
import { unwrap } from "./unwrap"
import type { CapitalAllocation, EquityCurvePoint, NavCurvePoint, PortfolioAnalytics, PortfolioStats } from "@/types/portfolio"

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
