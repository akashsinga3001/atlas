interface MiniRingProps {
    value: number
    max?: number
    size?: number
    strokeWidth?: number
    color?: string
    label?: string
}

export default function MiniRing({ value, max = 100, size = 48, strokeWidth = 4, color = "var(--color-accent)", label }: MiniRingProps) {
    const radius = (size - strokeWidth) / 2
    const circumference = 2 * Math.PI * radius
    const pct = Math.min(value / max, 1)
    const dash = pct * circumference

    return (
        <div className="relative flex items-center justify-center shrink-0" style={{ width: size, height: size }}>
            <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
                <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--color-border)" strokeWidth={strokeWidth} />
                <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke={color} strokeWidth={strokeWidth} strokeDasharray={`${dash} ${circumference}`} strokeLinecap="round" style={{ transition: "stroke-dasharray 1s cubic-bezier(0.23, 1, 0.32, 1)" }} />
            </svg>
            {label && (
                <span className="absolute text-[10px] font-bold font-mono" style={{ color }}>
                    {label}
                </span>
            )}
        </div>
    )
}
