import { motion } from "framer-motion"

export default function Toggle({ checked, onChange, disabled }: { checked: boolean; onChange: () => void; disabled?: boolean }) {
    return (
        <button
            type="button"
            role="switch"
            aria-checked={checked}
            disabled={disabled}
            onClick={onChange}
            className={`relative w-9 h-5 rounded-full transition-colors duration-200 ${disabled ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}`}
            style={{ background: checked ? "var(--color-accent)" : "var(--color-border)" }}
        >
            <motion.span layout transition={{ type: "spring", stiffness: 500, damping: 30 }} className="absolute top-0.5 w-4 h-4 rounded-full bg-white" style={{ left: checked ? "18px" : "2px" }} />
        </button>
    )
}
