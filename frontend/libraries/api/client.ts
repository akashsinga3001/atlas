import axios from "axios"

const client = axios.create({
    baseURL: process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1",
    timeout: 15000
})

export default client
