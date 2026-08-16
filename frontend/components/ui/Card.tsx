import { HTMLAttributes } from "react"

interface CardProps extends HTMLAttributes<HTMLDivElement> {
    variant?: "default" | "elevated"
    hover?: boolean
    padding?: "sm" | "md" | "lg"
}

export default function Card({ variant = "default", hover = false, padding = "md", className = "", children, ...props }: CardProps) {
    const variants = {
        default: "bg-surface border border-border",
        elevated: "bg-surface2 border border-border"
    }

    const paddings = {
        sm: "p-3",
        md: "p-4",
        lg: "p-6"
    }

    return (
        <div className={`${variants[variant]} rounded-[var(--radius-card)] ${paddings[padding]} ${hover ? "transition-colors duration-200 hover:border-muted cursor-pointer" : ""} ${className}`} {...props}>
            {children}
        </div>
    )
}
