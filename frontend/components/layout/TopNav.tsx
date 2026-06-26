"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { useEffect, useState } from "react"
import { LayoutDashboard, TrendingUp, Zap, PieChart, Settings } from "lucide-react"

const links = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/holdings", label: "Holdings", icon: TrendingUp },
    { href: "/signals", label: "Signals", icon: Zap },
    { href: "/portfolio", label: "Portfolio", icon: PieChart },
    { href: "/jobs", label: "Jobs", icon: Settings }
]

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
                <span className={`w-1.5 h-1.5 rounded-full ${open ? "bg-green-400" : "bg-muted"}`} style={open ? { boxShadow: "0 0 6px rgba(74,222,128,0.6)" } : {}} />
                <span className="text-[11px] font-medium" style={{ color: open ? "rgba(74,222,128,0.9)" : "var(--color-muted)" }}>
                    {open ? "Market Open" : "Market Closed"}
                </span>
            </div>
            <div className="w-px h-3" style={{ background: "rgba(255,255,255,0.08)" }} />
            <span className="text-[12px] font-mono tabular-nums" style={{ color: "var(--color-secondary)" }}>{time} IST</span>
        </div>
    )
}

export default function TopNav() {
    const pathname = usePathname()

    return (
        <nav className="sticky top-0 z-50" style={{ height: 54, background: "rgba(10,10,10,0.85)", backdropFilter: "blur(12px)", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="max-w-[1440px] mx-auto h-full flex items-center gap-8 px-8">

                {/* Brand */}
                <div className="shrink-0">
                    <span className="text-lg font-bold tracking-tight" style={{ color: "var(--color-accent)" }}>Atlas</span>
                </div>

                {/* Divider */}
                <div className="w-px h-4 shrink-0" style={{ background: "rgba(255,255,255,0.08)" }} />

                {/* Nav links */}
                <div className="flex items-center gap-0.5">
                    {links.map(({ href, label, icon: Icon }) => {
                        const active = pathname === href
                        return (
                            <Link
                                key={href}
                                href={href}
                                className={`relative flex items-center gap-2 px-4 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 ${active ? "text-primary" : "text-secondary hover:text-primary hover:bg-white/[0.03]"}`}
                                style={active ? { background: "rgba(255,255,255,0.06)" } : {}}
                            >
                                <Icon size={14} strokeWidth={active ? 2 : 1.75} style={{ color: active ? "var(--color-accent)" : undefined }} />
                                {label}
                                {active && (
                                    <span
                                        className="absolute left-0 right-0 bottom-0 mx-3 rounded-t-full"
                                        style={{ height: 2, background: "var(--color-accent)", opacity: 0.8 }}
                                    />
                                )}
                            </Link>
                        )
                    })}
                </div>

                {/* Right — live clock + market status */}
                <div className="ml-auto">
                    <Clock />
                </div>
            </div>
        </nav>
    )
}
