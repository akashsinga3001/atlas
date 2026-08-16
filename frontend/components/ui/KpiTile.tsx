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
        <div className="flex flex-col justify-between gap-1.5 px-3 py-2.5 bg-surface border border-border rounded-[var(--radius-card)]" style={{ minHeight: 64 }}>
            <div className="flex items-center justify-between gap-2">
                <span className="text-[10px] font-medium text-secondary uppercase tracking-wide">{label}</span>
                <Icon size={13} strokeWidth={1.75} style={{ color: iconColor }} />
            </div>

            <div className="flex flex-col gap-0.5">
                <span className={`text-lg font-bold tracking-tight leading-none ${valueColor ?? "text-primary"}`}>{value}</span>
                {sub && <span className="text-[10px] text-muted truncate">{sub}</span>}
            </div>
        </div>
    )
}
