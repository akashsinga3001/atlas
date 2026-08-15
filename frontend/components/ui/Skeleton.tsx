import { HTMLAttributes } from "react"

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
    className?: string
}

export default function Skeleton({ className = "", ...props }: SkeletonProps) {
    return <div className={`animate-pulse bg-surface2 rounded-[var(--radius-card)] ${className}`} {...props} />
}
