interface BadgeProps {
    label: string
    variant?: "green" | "red" | "amber" | "muted"
}

export default function Badge({ label, variant = "muted" }: BadgeProps) {
    const variants = {
        green: "bg-green-500/10 text-green-400 border-green-500/20",
        red: "bg-red-500/10 text-red-400 border-red-500/20",
        amber: "bg-accent/10 text-accent border-accent/20",
        muted: "bg-muted/10 text-secondary border-muted/20"
    }

    return <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-xs font-medium border ${variants[variant]}`}>{label}</span>
}
