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
        sm: "p-4",
        md: "p-6",
        lg: "p-8"
    }

    return (
        <div className={`${variants[variant]} rounded-[var(--radius-card)] shadow-[var(--shadow-border)] ${paddings[padding]} ${hover ? "transition-shadow duration-200 hover:shadow-[var(--shadow-medium)] cursor-pointer" : ""} ${className}`} {...props}>
            {children}
        </div>
    )
}
