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
        <div className="flex flex-col justify-between gap-2 px-4 py-3.5 bg-surface border border-border rounded-[var(--radius-card)]" style={{ minHeight: 80 }}>
            <div className="flex items-center justify-between gap-2">
                <span className="text-xs font-medium text-secondary">{label}</span>
                <Icon size={14} strokeWidth={1.75} style={{ color: iconColor }} />
            </div>

            <div className="flex flex-col gap-0.5">
                <span className={`text-2xl font-semibold leading-none ${valueColor ?? "text-primary"}`}>{value}</span>
                {sub && <span className="text-[11px] text-muted truncate">{sub}</span>}
            </div>
        </div>
    )
}
