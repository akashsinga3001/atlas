import { useQuery } from "@tanstack/react-query"
import { getStrategies } from "../api/strategies"

export function useStrategies() {
    return useQuery({ queryKey: ["strategies"], queryFn: getStrategies })
}
