import { LucideIcon } from "lucide-react"

interface EmptyStateProps {
    icon: LucideIcon
    title: string
    description?: string
}

export default function EmptyState({ icon: Icon, title, description }: EmptyStateProps) {
    return (
        <div className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <Icon className="text-muted" size={32} strokeWidth={1.5} />
            <div className="flex flex-col gap-1">
                <p className="text-sm font-medium text-primary">{title}</p>
                {description && <p className="text-xs text-secondary">{description}</p>}
            </div>
        </div>
    )
}
