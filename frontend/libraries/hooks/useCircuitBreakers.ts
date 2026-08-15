import { useQuery, useQueryClient, useMutation } from "@tanstack/react-query"
import { getCircuitBreakers, updateCircuitBreaker } from "../api/circuitBreakers"
import { UpdateCircuitBreakerPayload } from "../types/circuitBreakers"

export function useCircuitBreakers() {
    return useQuery({
        queryKey: ["circuit-breakers"],
        queryFn: getCircuitBreakers
    })
}

export function useUpdateCircuitBreaker() {
    const queryClient = useQueryClient()
    return useMutation({
        mutationFn: ({ id, payload }: { id: number; payload: UpdateCircuitBreakerPayload }) => updateCircuitBreaker(id, payload),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["circuit-breakers"] })
        }
    })
}
