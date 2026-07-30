import type { NextConfig } from "next"

const nextConfig: NextConfig = {
    allowedDevOrigins: process.env.LAN_DEV_ORIGIN ? [process.env.LAN_DEV_ORIGIN] : [],
    async rewrites() {
        return [
            {
                source: "/api/v1/:path*",
                destination: "http://backend:8000/api/v1/:path*"
            }
        ]
    }
}

export default nextConfig
