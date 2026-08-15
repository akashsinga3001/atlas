import { useQuery } from "@tanstack/react-query"
import { getOptionsPositions } from "../api/options"

export function useOptionsPositions(status?: string) {
    return useQuery({
        queryKey: ["options-positions", status],
        queryFn: () => getOptionsPositions(status)
    })
}
