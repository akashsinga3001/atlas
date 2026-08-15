"use client"

import { useState, useRef, useEffect } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { ChevronDown } from "lucide-react"
import { ParameterField } from "@/libraries/types/job"

export function EnumSelect({ options, value, onChange, required }: { options: string[]; value: string; onChange: (v: string) => void; required: boolean }) {
    const [open, setOpen] = useState(false)
    const ref = useRef<HTMLDivElement>(null)

    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
        }
        document.addEventListener("mousedown", handler)
        return () => document.removeEventListener("mousedown", handler)
    }, [])

    const displayed = value || (required ? options[0] : "")

    return (
        <div ref={ref} className="relative">
            <button type="button" onClick={() => setOpen((o) => !o)} className="w-full flex items-center justify-between px-3 py-2 rounded-lg text-sm font-mono text-primary border border-white/8 hover:border-white/16 focus:border-accent/40 focus:outline-none transition-colors" style={{ background: "var(--color-surface2)" }}>
                <span className={displayed ? "text-primary" : "text-muted"}>{displayed || "— optional —"}</span>
                <ChevronDown size={12} className={`text-muted transition-transform duration-150 ${open ? "rotate-180" : ""}`} />
            </button>

            <AnimatePresence>
                {open && (
                    <motion.div initial={{ opacity: 0, y: -4 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -4 }} transition={{ duration: 0.12 }} className="absolute z-10 left-0 right-0 mt-1 rounded-xl overflow-hidden" style={{ background: "var(--color-surface2)", border: "1px solid rgba(255,255,255,0.1)", boxShadow: "0 8px 32px rgba(0,0,0,0.5)" }}>
                        {!required && (
                            <button
                                type="button"
                                onClick={() => {
                                    onChange("")
                                    setOpen(false)
                                }}
                                className="w-full text-left px-3 py-2.5 text-sm font-mono text-muted hover:bg-white/4 transition-colors"
                            >
                                — optional —
                            </button>
                        )}
                        {options.map((o) => (
                            <button
                                key={o}
                                type="button"
                                onClick={() => {
                                    onChange(o)
                                    setOpen(false)
                                }}
                                className={`w-full text-left px-3 py-2.5 text-sm font-mono transition-colors flex items-center justify-between ${value === o ? "text-accent" : "text-primary hover:bg-white/4"}`}
                                style={value === o ? { background: "rgba(212,160,23,0.08)" } : {}}
                            >
                                {o}
                                {value === o && <span className="w-1.5 h-1.5 rounded-full" style={{ background: "var(--color-accent)" }} />}
                            </button>
                        ))}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}

export function coerceFieldValue(field: ParameterField, raw: string): unknown {
    if (field.type === "integer") return parseInt(raw, 10)
    if (field.type === "number") return parseFloat(raw)
    if (field.type === "array")
        return raw
            .split(",")
            .map((s) => s.trim())
            .filter(Boolean)
    return raw
}

export function FieldInput({ field, value, onChange }: { field: ParameterField; value: string; onChange: (v: string) => void }) {
    const base = "w-full px-3 py-2 rounded-lg text-sm font-mono text-primary bg-transparent border border-white/8 focus:border-accent/40 focus:outline-none transition-colors"

    if (field.type === "enum" && field.options) {
        return <EnumSelect options={field.options} value={value} onChange={onChange} required={field.required} />
    }

    if (field.type === "integer") {
        return <input type="number" value={value} onChange={(e) => onChange(e.target.value)} placeholder={field.default != null ? String(field.default) : undefined} className={base} />
    }

    if (field.type === "number") {
        return <input type="number" step="any" value={value} onChange={(e) => onChange(e.target.value)} placeholder={field.default != null ? String(field.default) : undefined} className={base} />
    }

    if (field.type === "array") {
        return <input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder="comma-separated values" className={base} />
    }

    return <input type="text" value={value} onChange={(e) => onChange(e.target.value)} placeholder={field.default != null ? String(field.default) : undefined} className={base} />
}
