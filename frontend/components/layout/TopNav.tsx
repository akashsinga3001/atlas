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
                <span className={`hud-dot ${open ? "hud-dot-live live-pulse" : ""}`} style={!open ? { background: "var(--color-muted)" } : {}} />
                <span className="text-[11px] font-medium" style={{ color: open ? "rgba(74,222,128,0.9)" : "var(--color-muted)" }}>
                    {open ? "Market Open" : "Market Closed"}
                </span>
            </div>
            <div className="w-px h-3" style={{ background: "rgba(255,255,255,0.08)" }} />
            <span className="text-[12px] font-mono tabular-nums" style={{ color: "var(--color-secondary)" }}>
                {time} IST
            </span>
        </div>
    )
}

export default function TopNav() {
    const pathname = usePathname()

    return (
        <nav className="sticky top-0 z-50" style={{ height: 54, background: "rgba(10,10,10,0.85)", backdropFilter: "blur(12px)", borderBottom: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="max-w-360 mx-auto h-full flex items-center gap-8 px-8">
                {/* Brand */}
                <div className="shrink-0 flex items-center gap-2.5">
                    <svg width="28" height="28" viewBox="0 0 28 28" fill="none" aria-hidden="true">
                        <circle cx="14" cy="14" r="12" stroke="#C9A84C" strokeWidth="1.25" opacity="0.35" />
                        <line x1="2" y1="14" x2="9" y2="14" stroke="#C9A84C" strokeWidth="1.5" strokeLinecap="round" />
                        <line x1="19" y1="14" x2="26" y2="14" stroke="#C9A84C" strokeWidth="1.5" strokeLinecap="round" />
                        <line x1="14" y1="2" x2="14" y2="9" stroke="#C9A84C" strokeWidth="1.5" strokeLinecap="round" />
                        <line x1="14" y1="19" x2="14" y2="26" stroke="#C9A84C" strokeWidth="1.5" strokeLinecap="round" />
                        <circle cx="14" cy="14" r="2.5" fill="#C9A84C" />
                        <polyline points="7,19 11,14 15,17 21,9" fill="none" stroke="#C9A84C" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" />
                        <circle cx="21" cy="9" r="2" fill="#C9A84C" />
                    </svg>
                    <div className="flex flex-col gap-1">
                        <span className="text-lg font-bold tracking-tight leading-none" style={{ color: "var(--color-accent)" }}>
                            Atlas
                        </span>
                        <span className="font-mono text-[9px] uppercase tracking-[0.18em] leading-none" style={{ color: "var(--color-secondary)" }}>
                            Trading System
                        </span>
                    </div>
                </div>

                {/* Divider */}
                <div className="w-px h-4 shrink-0" style={{ background: "rgba(255,255,255,0.08)" }} />

                {/* Nav links */}
                <div className="flex items-center gap-2">
                    {links.map(({ href, label, icon: Icon }) => {
                        const active = pathname === href
                        return (
                            <Link key={href} href={href} className={`relative flex flex-col items-center gap-0 px-4 py-2 rounded-lg text-[13px] font-medium transition-all duration-150 ${active ? "text-primary" : "text-secondary hover:text-primary hover:bg-white/3"}`} style={active ? { background: "rgba(255,255,255,0.06)" } : {}}>
                                <span className="flex items-center gap-1.5">
                                    <Icon size={14} strokeWidth={active ? 2 : 1.75} style={{ color: active ? "var(--color-accent)" : undefined }} />
                                    {label}
                                </span>
                                {active && <span className="nav-active-dot absolute bottom-0.5 left-1/2 -translate-x-1/2 w-4 h-[2px] rounded-full" style={{ background: "var(--color-accent)", boxShadow: "0 0 8px rgba(212,160,23,0.6)" }} />}
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
