interface StatProps {
    label: string
    value: string | number
    delta?: number
    deltaLabel?: string
    mono?: boolean
}

export default function Stat({ label, value, delta, deltaLabel, mono = true }: StatProps) {
    const isPositive = delta !== undefined && delta >= 0
    const deltaColor = delta === undefined ? "" : isPositive ? "text-green-400" : "text-red-400"
    const deltaSign = delta !== undefined && delta > 0 ? "+" : ""

    return (
        <div className="flex flex-col gap-1">
            <span className="text-xs text-secondary uppercase tracking-widest">{label}</span>
            <span className={`text-2xl font-bold text-primary ${mono ? "font-mono" : ""}`}>{value}</span>
            {delta !== undefined && (
                <span className={`text-xs ${deltaColor}`}>
                    {deltaSign}
                    {delta}%{deltaLabel ? ` ${deltaLabel}` : ""}
                </span>
            )}
        </div>
    )
}
