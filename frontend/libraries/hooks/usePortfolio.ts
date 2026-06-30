import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query"
import { getPortfolioStats, getEquityCurve, getPortfolioAnalytics, getNavCurve, getCashFlows, createCashFlow } from "../api/portfolio"

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

export function usePortfolioAnalytics() {
    return useQuery({
        queryKey: ["portfolio", "analytics"],
        queryFn: getPortfolioAnalytics
    })
}

export function useNavCurve() {
    return useQuery({
        queryKey: ["portfolio", "nav-curve"],
        queryFn: getNavCurve
    })
}

export function useCashFlows() {
    return useQuery({
        queryKey: ["fund", "cashflow"],
        queryFn: getCashFlows
    })
}

export function useCreateCashFlow() {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: createCashFlow,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["fund", "cashflow"] })
            queryClient.invalidateQueries({ queryKey: ["portfolio", "stats"] })
            queryClient.invalidateQueries({ queryKey: ["portfolio", "nav-curve"] })
        }
    })
}
