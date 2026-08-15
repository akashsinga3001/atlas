import { useQuery } from "@tanstack/react-query"
import { getScheduleEntries } from "../api/schedule"

export function useSchedule() {
    return useQuery({
        queryKey: ["schedule"],
        queryFn: getScheduleEntries,
        refetchInterval: 15000
    })
}
