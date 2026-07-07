import { LucideIcon } from "lucide-react"

interface KpiTileProps {
    icon: LucideIcon
    iconColor: string
    label: string
    value: string
    valueColor?: string
    sub?: string
    ring?: number
    ringColor?: string
}

export default function KpiTile({ icon: Icon, iconColor, label, value, valueColor, sub }: KpiTileProps) {
    return (
        <div
            className="relative flex flex-col justify-between px-4 py-3.5 card-hover overflow-hidden"
            style={{
                background: "var(--color-surface)",
                border: "1px solid rgba(255,255,255,0.07)",
                borderLeft: `2px solid ${iconColor}`,
                borderRadius: 12,
                boxShadow: "0 4px 16px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.04)",
                minHeight: 80
            }}
        >
            {/* Background watermark icon */}
            <Icon size={52} strokeWidth={1.2} style={{ color: iconColor, opacity: 0.07, position: "absolute", bottom: -8, right: -6, pointerEvents: "none" }} />

            {/* Label */}
            <span
                style={{
                    fontFamily: "var(--font-mono), monospace",
                    fontSize: 9,
                    letterSpacing: "0.14em",
                    textTransform: "uppercase",
                    color: "var(--color-secondary)"
                }}
            >
                {label}
            </span>

            {/* Value */}
            <div className="flex flex-col gap-0.5 mt-2">
                <span className={`text-2xl font-bold font-mono leading-none ${valueColor ?? "text-primary"}`}>{value}</span>
                {sub && <span className="text-[10px] text-muted truncate font-mono">{sub}</span>}
            </div>
        </div>
    )
}
