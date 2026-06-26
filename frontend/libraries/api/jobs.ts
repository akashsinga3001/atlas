import client from "./client"
import { Job } from "../types/job"

export async function getJobs(): Promise<Job[]> {
    const res = await client.get("/jobs")
    return res.data.data ?? []
}
