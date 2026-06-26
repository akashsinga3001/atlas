"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { LayoutDashboard, TrendingUp, Zap, PieChart, Settings } from "lucide-react"

const links = [
    { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
    { href: "/holdings", label: "Holdings", icon: TrendingUp },
    { href: "/signals", label: "Signals", icon: Zap },
    { href: "/portfolio", label: "Portfolio", icon: PieChart },
    { href: "/jobs", label: "Jobs", icon: Settings }
]

export default function Sidebar() {
    const pathname = usePathname()

    return (
        <aside className="sticky top-0 h-screen w-56 flex-shrink-0 flex flex-col" style={{ background: "#0d0d0d", borderRight: "1px solid rgba(255,255,255,0.05)" }}>

            {/* Brand */}
            <div className="px-5 pt-8 pb-7">
                <span className="block text-2xl font-bold tracking-tight leading-none" style={{ color: "var(--color-accent)" }}>Atlas</span>
                <span className="block text-[10px] uppercase tracking-[0.25em] mt-1.5" style={{ color: "var(--color-muted)" }}>Trading Desk</span>
            </div>

            {/* Separator */}
            <div style={{ height: 1, background: "rgba(255,255,255,0.05)", margin: "0 20px" }} />

            {/* Nav */}
            <nav className="flex flex-col gap-0.5 px-3 pt-4 flex-1">
                {links.map(({ href, label, icon: Icon }) => {
                    const active = pathname === href
                    return (
                        <Link key={href} href={href} className={`relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-[13px] font-medium transition-all duration-150 ${active ? "text-primary" : "text-secondary hover:text-primary"}`}
                            style={active ? { background: "rgba(255,255,255,0.05)" } : {}}>
                            {active && <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-r-full" style={{ background: "var(--color-accent)" }} />}
                            <Icon size={15} strokeWidth={active ? 2 : 1.75} style={{ color: active ? "var(--color-accent)" : undefined }} />
                            {label}
                        </Link>
                    )
                })}
            </nav>

            {/* Footer */}
            <div className="px-5 py-5" style={{ borderTop: "1px solid rgba(255,255,255,0.04)" }}>
                <span className="text-[10px]" style={{ color: "var(--color-muted)" }}>v0.1.0 · internal</span>
            </div>
        </aside>
    )
}
