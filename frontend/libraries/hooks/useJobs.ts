import { useQuery } from "@tanstack/react-query"
import { getJobs } from "../api/jobs"

export function useJobs() {
    return useQuery({
        queryKey: ["jobs"],
        queryFn: getJobs
    })
}
