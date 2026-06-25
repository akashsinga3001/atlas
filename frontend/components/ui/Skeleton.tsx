import { HTMLAttributes } from "react"

interface SkeletonProps extends HTMLAttributes<HTMLDivElement> {
    className?: string
}

export default function Skeleton({ className = "", ...props }: SkeletonProps) {
    return <div className={`animate-pulse rounded-md bg-surface2 ${className}`} {...props} />
}
