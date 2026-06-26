import { useQuery } from "@tanstack/react-query"
import { getSignals } from "../api/signals"

export function useSignals(params?: { date_from?: string; date_to?: string; status?: string }) {
    return useQuery({
        queryKey: ["signals", params],
        queryFn: () => getSignals(params)
    })
}
