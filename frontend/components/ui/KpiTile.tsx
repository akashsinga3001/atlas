import { LucideIcon } from "lucide-react"
import MiniRing from "./MiniRing"
import HudCorners from "./HudCorners"

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

export default function KpiTile({ icon: Icon, iconColor, label, value, valueColor, sub, ring, ringColor }: KpiTileProps) {
    return (
        <div className="relative flex flex-col gap-2.5 px-3 py-3 hud-panel card-hover">
            <HudCorners opacity={0.25} />
            <div className="flex items-center justify-between">
                <Icon size={14} style={{ color: iconColor }} strokeWidth={2} />
                {ring !== undefined && <MiniRing value={ring} max={100} size={20} strokeWidth={2} color={ringColor} />}
            </div>
            <div className="flex flex-col gap-0.5">
                <span className="flex items-baseline gap-1.5 min-w-0">
                    <span className={`text-lg font-bold font-mono leading-none ${valueColor ?? "text-primary"}`}>{value}</span>
                    {sub && <span className="text-[10px] text-muted truncate">{sub}</span>}
                </span>
                <span className="hud-label-sm text-[9px]">{label}</span>
            </div>
        </div>
    )
}
