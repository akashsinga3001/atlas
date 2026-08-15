import { useQuery } from "@tanstack/react-query"
import { getVersionHistory } from "../api/strategies"

export function useStrategyVersions(strategyId: number | null) {
    return useQuery({
        queryKey: ["strategy-versions", strategyId],
        queryFn: () => getVersionHistory(strategyId as number),
        enabled: strategyId !== null
    })
}
