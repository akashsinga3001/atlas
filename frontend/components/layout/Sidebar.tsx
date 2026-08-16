"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, TrendingUp, CandlestickChart, Zap, PieChart, SlidersHorizontal, Settings, CalendarClock } from "lucide-react"

const links = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/holdings", label: "Holdings", icon: TrendingUp },
    { href: "/options", label: "Options", icon: CandlestickChart },
    { href: "/signals", label: "Signals", icon: Zap },
    { href: "/portfolio", label: "Portfolio", icon: PieChart },
    { href: "/strategies", label: "Strategies", icon: SlidersHorizontal },
    { href: "/jobs", label: "Jobs", icon: Settings },
    { href: "/schedule", label: "Schedule", icon: CalendarClock }
]

export default function Sidebar() {
    const pathname = usePathname()

    return (
        <aside className="sticky top-0 h-screen w-60 shrink-0 flex flex-col bg-bg border-r border-border">
            <div className="px-5 pt-6 pb-5 border-b border-border">
                <span className="block text-lg font-bold tracking-tight leading-none text-primary">Atlas</span>
                <span className="block text-[11px] text-muted mt-1 uppercase tracking-wide">Trading System</span>
            </div>

            <nav className="flex flex-col px-3 pt-3 flex-1 overflow-y-auto">
                {links.map(({ href, label, icon: Icon }) => {
                    const active = pathname === href
                    return (
                        <Link key={href} href={href} className={`relative flex items-center gap-2.5 px-3 py-2 text-sm font-medium transition-colors ${active ? "text-primary" : "text-secondary hover:text-primary"}`}>
                            {active && <span className="absolute left-0 top-1.5 bottom-1.5 w-0.5 bg-accent" />}
                            <Icon size={16} strokeWidth={1.75} />
                            {label}
                        </Link>
                    )
                })}
            </nav>

            <div className="px-5 py-4 border-t border-border">
                <span className="text-[11px] text-muted">v0.1.0 · internal</span>
            </div>
        </aside>
    )
}
