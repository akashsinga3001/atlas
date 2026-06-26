import { HTMLAttributes } from "react"

interface CardProps extends HTMLAttributes<HTMLDivElement> {
    variant?: "default" | "elevated" | "accent"
    hover?: boolean
    padding?: "sm" | "md" | "lg"
}

export default function Card({ variant = "default", hover = false, padding = "md", className = "", children, ...props }: CardProps) {
    const variants = {
        default: "card-base",
        elevated: "card-base bg-surface2",
        accent: "card-accent"
    }

    const paddings = {
        sm: "p-4",
        md: "p-6",
        lg: "p-8"
    }

    return (
        <div className={`${variants[variant]} ${paddings[padding]} ${hover ? "card-hover cursor-pointer" : ""} ${className}`} {...props}>
            {children}
        </div>
    )
}
