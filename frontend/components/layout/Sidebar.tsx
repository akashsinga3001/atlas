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
            <div className="px-5 pt-6 pb-5">
                <span className="block text-lg font-semibold tracking-tight leading-none text-primary">Atlas</span>
                <span className="block text-[11px] text-muted mt-1">Trading System</span>
            </div>

            <nav className="flex flex-col gap-0.5 px-3 flex-1 overflow-y-auto">
                {links.map(({ href, label, icon: Icon }) => {
                    const active = pathname === href
                    return (
                        <Link key={href} href={href} className={`flex items-center gap-2.5 px-3 py-2 rounded-[var(--radius-card)] text-sm font-medium transition-colors ${active ? "bg-surface2 text-primary" : "text-secondary hover:text-primary hover:bg-surface2/60"}`}>
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
