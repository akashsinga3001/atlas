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
        <aside className="fixed top-0 left-0 h-screen w-56 bg-surface border-r border-border flex flex-col">
            <div className="px-6 py-5 border-b border-border">
                <span className="text-lg font-bold tracking-tight text-accent">Atlas</span>
            </div>
            <nav className="flex flex-col gap-1 p-3 flex-1">
                {links.map(({ href, label, icon: Icon }) => {
                    const active = pathname === href
                    return (
                        <Link key={href} href={href} className={`flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${active ? "bg-accent/10 text-accent" : "text-secondary hover:text-primary hover:bg-surface2"}`}>
                            <Icon size={16} strokeWidth={1.75} />
                            {label}
                        </Link>
                    )
                })}
            </nav>
        </aside>
    )
}
