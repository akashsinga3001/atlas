import { useQuery } from "@tanstack/react-query"
import { getTrades } from "../api/trades"

export function useTrades(status?: string) {
    return useQuery({
        queryKey: ["trades", status],
        queryFn: () => getTrades(status)
    })
}
