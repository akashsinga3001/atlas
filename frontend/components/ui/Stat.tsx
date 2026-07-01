"use client"

import { useCountUp } from "@/libraries/hooks/useCountUp"

interface StatProps {
    label: string
    value: string | number
    numericValue?: number
    delta?: number
    deltaLabel?: string
    accent?: boolean
    size?: "sm" | "md" | "lg"
}

function AnimatedNumber({ value, accent }: { value: number; accent?: boolean }) {
    const count = useCountUp(value)
    return <span className={`font-mono tabular-nums ${accent ? "text-accent" : "text-primary"}`}>{Math.round(count).toLocaleString("en-IN")}</span>
}

export default function Stat({ label, value, numericValue, delta, deltaLabel, accent = false, size = "md" }: StatProps) {
    const isPositive = delta !== undefined && delta >= 0
    const deltaColor = delta === undefined ? "" : isPositive ? "text-green-400" : "text-red-400"
    const deltaSign = delta !== undefined && delta > 0 ? "+" : ""

    const sizes = {
        sm: "text-2xl",
        md: "text-4xl",
        lg: "text-5xl"
    }

    return (
        <div className="flex flex-col gap-2">
            <span className="font-mono text-xs text-secondary uppercase tracking-[0.15em] font-medium">{label}</span>
            <div className={`${sizes[size]} font-bold leading-none tracking-tight ${accent ? "text-accent" : "text-primary"}`}>{numericValue !== undefined ? <AnimatedNumber value={numericValue} accent={accent} /> : <span className={`font-mono ${accent ? "text-accent" : ""}`}>{value}</span>}</div>
            {delta !== undefined && (
                <span className={`text-xs font-medium ${deltaColor}`}>
                    {deltaSign}
                    {delta.toFixed(1)}%{deltaLabel ? <span className="text-secondary font-normal"> {deltaLabel}</span> : null}
                </span>
            )}
        </div>
    )
}
