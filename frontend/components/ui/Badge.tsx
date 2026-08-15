interface BadgeProps {
    label: string
    variant?: "green" | "red" | "amber" | "blue" | "muted"
}

export default function Badge({ label, variant = "muted" }: BadgeProps) {
    const variants = {
        green: "bg-success/10 text-success border-success/20",
        red: "bg-danger/10 text-danger border-danger/20",
        amber: "bg-warning/10 text-warning border-warning/20",
        blue: "bg-accent/10 text-accent border-accent/20",
        muted: "bg-muted/10 text-secondary border-muted/20"
    }

    return <span className={`inline-flex items-center px-2 py-0.5 rounded-[var(--radius-card)] text-[11px] font-semibold border ${variants[variant]}`}>{label}</span>
}
