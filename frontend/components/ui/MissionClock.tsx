"use client"

import { useEffect, useState } from "react"

export default function MissionClock() {
    const [now, setNow] = useState<Date | null>(null)

    useEffect(() => {
        setNow(new Date())
        const interval = setInterval(() => setNow(new Date()), 1000)
        return () => clearInterval(interval)
    }, [])

    if (!now) return null

    const time = now.toLocaleTimeString("en-IN", { hour12: false })
    const date = now.toLocaleDateString("en-IN", { weekday: "short", day: "2-digit", month: "short" })

    return (
        <div className="flex items-center gap-2 font-mono text-[11px] text-secondary">
            <span className="hud-dot hud-dot-live live-pulse" />
            <span className="tracking-wider">{date}</span>
            <span className="text-muted">·</span>
            <span className="text-primary font-semibold tracking-wider">{time}</span>
        </div>
    )
}
