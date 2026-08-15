"use client"

import { useEffect, useState } from "react"
import { useTheme } from "next-themes"
import { Sun, Moon, Monitor } from "lucide-react"

const options = [
    { value: "light", icon: Sun, label: "Light" },
    { value: "dark", icon: Moon, label: "Dark" },
    { value: "system", icon: Monitor, label: "System" }
] as const

export default function ThemeToggle() {
    const { theme, setTheme } = useTheme()
    const [mounted, setMounted] = useState(false)
    useEffect(() => setMounted(true), [])

    if (!mounted) return <div className="w-[84px] h-7" />

    return (
        <div className="flex items-center gap-0.5 p-0.5 rounded-[var(--radius-card)] bg-surface2 border border-border">
            {options.map(({ value, icon: Icon, label }) => (
                <button key={value} type="button" onClick={() => setTheme(value)} aria-label={label} title={label} className={`flex items-center justify-center w-6 h-6 rounded transition-colors ${theme === value ? "bg-surface text-primary" : "text-secondary hover:text-primary"}`} style={theme === value ? { boxShadow: "var(--shadow-small)" } : undefined}>
                    <Icon size={13} strokeWidth={1.75} />
                </button>
            ))}
        </div>
    )
}
