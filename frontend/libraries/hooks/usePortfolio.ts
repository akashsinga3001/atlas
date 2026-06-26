import { useQuery } from "@tanstack/react-query"
import { getPortfolioStats, getEquityCurve } from "../api/portfolio"

export function usePortfolioStats() {
    return useQuery({
        queryKey: ["portfolio", "stats"],
        queryFn: getPortfolioStats
    })
}

export function useEquityCurve() {
    return useQuery({
        queryKey: ["portfolio", "equity-curve"],
        queryFn: getEquityCurve
    })
}
