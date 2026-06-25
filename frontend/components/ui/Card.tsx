import { HTMLAttributes } from "react"

interface CardProps extends HTMLAttributes<HTMLDivElement> {
    variant?: "default" | "elevated"
}

export default function Card({ variant = "default", className = "", children, ...props }: CardProps) {
    const base = "rounded-xl border border-border p-4"
    const variants = { default: "bg-surface", elevated: "bg-surface2" }

    return (
        <div className={`${base} ${variants[variant]} ${className}`} {...props}>
            {children}
        </div>
    )
}
