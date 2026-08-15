"use client"

import { useEffect, useState } from "react"
import { usePathname } from "next/navigation"
import { ChevronDown } from "lucide-react"
import KillSwitchControl from "./KillSwitchControl"
import ThemeToggle from "./ThemeToggle"

const PAGE_LABELS: Record<string, string> = {
    dashboard: "Dashboard",
    holdings: "Holdings",
    options: "Options",
    signals: "Signals",
    portfolio: "Portfolio",
    strategies: "Strategies",
    jobs: "Jobs",
    schedule: "Schedule"
}

function isMarketOpen() {
    const now = new Date(new Date().toLocaleString("en-US", { timeZone: "Asia/Kolkata" }))
    const day = now.getDay()
    if (day === 0 || day === 6) return false
    const mins = now.getHours() * 60 + now.getMinutes()
    return mins >= 9 * 60 + 15 && mins < 15 * 60 + 30
}

function Clock() {
    const [time, setTime] = useState("")
    const [open, setOpen] = useState(false)

    useEffect(() => {
        const tick = () => {
            const now = new Date()
            setTime(now.toLocaleTimeString("en-IN", { timeZone: "Asia/Kolkata", hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }))
            setOpen(isMarketOpen())
        }
        tick()
        const id = setInterval(tick, 1000)
        return () => clearInterval(id)
    }, [])

    return (
        <div className="flex items-center gap-3">
            <div className="flex items-center gap-1.5">
                <span className={`inline-block w-1.5 h-1.5 rounded-full ${open ? "bg-success" : "bg-muted"}`} />
                <span className={`text-[11px] font-medium ${open ? "text-success" : "text-muted"}`}>{open ? "Market Open" : "Market Closed"}</span>
            </div>
            <div className="w-px h-3 bg-border" />
            <span className="text-[12px] tabular-nums text-secondary">{time} IST</span>
        </div>
    )
}

export default function TopNav() {
    const pathname = usePathname()
    const segment = pathname.split("/")[1] ?? ""
    const label = PAGE_LABELS[segment] ?? segment

    return (
        <header className="sticky top-0 z-40 h-14 bg-bg border-b border-border">
            <div className="h-full flex items-center px-6">
                <div className="flex items-center gap-1.5 text-sm text-secondary">
                    <span className="flex items-center gap-1">
                        Atlas
                        <ChevronDown size={13} className="text-muted" />
                    </span>
                    {label && (
                        <>
                            <span className="text-muted">/</span>
                            <span className="text-primary font-medium">{label}</span>
                        </>
                    )}
                </div>
                <div className="ml-auto flex items-center gap-4">
                    <KillSwitchControl />
                    <Clock />
                    <div className="w-px h-4 bg-border" />
                    <ThemeToggle />
                </div>
            </div>
        </header>
    )
}
