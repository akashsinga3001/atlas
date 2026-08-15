import { useQuery } from "@tanstack/react-query"
import { getKillSwitchStatus } from "../api/killSwitch"

export function useKillSwitch() {
    return useQuery({
        queryKey: ["kill-switch"],
        queryFn: getKillSwitchStatus,
        refetchInterval: 10000
    })
}
