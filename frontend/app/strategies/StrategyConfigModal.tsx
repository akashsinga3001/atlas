"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { motion } from "framer-motion"
import { Loader, Save, X } from "lucide-react"
import { FieldInput, coerceFieldValue } from "@/components/forms/DynamicFieldInput"
import { Strategy } from "@/libraries/types/strategy"
import { createVersion, StrategyConfigError } from "@/libraries/api/strategies"

export default function StrategyConfigModal({ strategy, onClose, onCreated }: { strategy: Strategy; onClose: () => void; onCreated: () => void }) {
    const queryClient = useQueryClient()
    const activeConfig = strategy.active_version?.config ?? {}

    const [values, setValues] = useState<Record<string, string>>(() => {
        const init: Record<string, string> = {}
        strategy.config_fields.forEach((f) => {
            const current = activeConfig[f.name]
            init[f.name] = current !== undefined ? String(current) : f.default != null ? String(f.default) : ""
        })
        return init
    })
    const [rawJson, setRawJson] = useState(() => JSON.stringify(activeConfig, null, 2))
    const [jsonError, setJsonError] = useState<string | null>(null)
    const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({})
    const [formError, setFormError] = useState<string | null>(null)

    const set = (name: string, value: string) => {
        setValues((v) => ({ ...v, [name]: value }))
        setFieldErrors((e) => ({ ...e, [name]: "" }))
    }

    const { mutate, isPending } = useMutation({
        mutationFn: (config: Record<string, unknown>) => createVersion(strategy.id, config),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["strategies"] })
            onCreated()
        },
        onError: (err: unknown) => {
            if (err instanceof StrategyConfigError) {
                setFormError(err.message)
                const perField: Record<string, string> = {}
                err.fieldErrors.forEach((fe) => {
                    const name = String(fe.loc[0])
                    perField[name] = fe.msg
                })
                setFieldErrors(perField)
            } else {
                setFormError("Failed to save — check the backend is reachable.")
            }
        }
    })

    const submitTyped = () => {
        setFormError(null)
        const missing: Record<string, string> = {}
        strategy.config_fields.forEach((f) => {
            if (f.required && !values[f.name]) missing[f.name] = "Required"
        })
        if (Object.keys(missing).length) {
            setFieldErrors(missing)
            return
        }
        const config: Record<string, unknown> = {}
        strategy.config_fields.forEach((f) => {
            if (values[f.name] === "") return
            config[f.name] = coerceFieldValue(f, values[f.name])
        })
        mutate(config)
    }

    const submitRaw = () => {
        setFormError(null)
        try {
            const parsed = JSON.parse(rawJson)
            setJsonError(null)
            mutate(parsed)
        } catch {
            setJsonError("Not valid JSON — fix the syntax before saving.")
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div className="absolute inset-0" style={{ background: "var(--overlay-scrim)", backdropFilter: "blur(4px)" }} />
            <motion.div
                initial={{ opacity: 0, scale: 0.96, y: 8 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96, y: 8 }}
                transition={{ duration: 0.18, ease: [0.23, 1, 0.32, 1] }}
                className="relative w-full max-w-lg max-h-[85vh] overflow-y-auto rounded-[var(--radius-card)] p-6 flex flex-col gap-5 bg-surface border border-border"
                style={{ boxShadow: "var(--shadow-large)" }}
                onClick={(e) => e.stopPropagation()}
            >
                <div className="flex items-start justify-between">
                    <div>
                        <p className="text-xs text-secondary mb-0.5">Edit Config — Draft Version</p>
                        <h2 className="text-lg font-bold text-primary leading-tight">{strategy.name}</h2>
                        <p className="text-[11px] text-secondary mt-1">Saves as a new inactive version. Nothing changes live until you activate it in History.</p>
                    </div>
                    <button onClick={onClose} className="p-1.5 rounded-[var(--radius-card)] text-muted hover:text-primary hover:bg-surface2 transition-colors">
                        <X size={14} />
                    </button>
                </div>

                {strategy.has_config_schema ? (
                    <div className="flex flex-col gap-4">
                        {strategy.config_fields.map((field) => (
                            <div key={field.name} className="flex flex-col gap-1.5">
                                <div className="flex items-center justify-between">
                                    <label className="text-xs font-semibold text-primary capitalize">{field.name.replace(/_/g, " ")}</label>
                                    {field.required ? (
                                        <span className="text-[10px] uppercase tracking-wide font-bold text-primary">
                                            Required
                                        </span>
                                    ) : (
                                        <span className="text-[10px] uppercase tracking-wide text-muted">Optional</span>
                                    )}
                                </div>
                                {field.description && <p className="text-[11px] text-secondary">{field.description}</p>}
                                <FieldInput field={field} value={values[field.name] ?? ""} onChange={(v) => set(field.name, v)} />
                                {fieldErrors[field.name] && <p className="text-[11px] text-danger">{fieldErrors[field.name]}</p>}
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="flex flex-col gap-1.5">
                        <p className="text-[11px] text-secondary">No typed schema registered for this strategy — edit the raw config JSON directly.</p>
                        <textarea
                            value={rawJson}
                            onChange={(e) => {
                                setRawJson(e.target.value)
                                setJsonError(null)
                            }}
                            rows={14}
                            spellCheck={false}
                            className="w-full px-3 py-2 rounded-[var(--radius-card)] text-xs font-mono text-primary bg-surface2 border border-border focus:border-accent focus:outline-none transition-colors"
                        />
                        {jsonError && <p className="text-[11px] text-danger">{jsonError}</p>}
                    </div>
                )}

                {formError && <p className="text-[11px] text-danger border border-danger/20 bg-danger/5 rounded-[var(--radius-card)] px-3 py-2">{formError}</p>}

                <div className="flex items-center justify-end gap-2 pt-1">
                    <button onClick={onClose} className="px-4 py-2 rounded-[var(--radius-card)] text-xs font-semibold text-secondary border border-border hover:border-muted hover:text-primary transition-colors">
                        Cancel
                    </button>
                    <button
                        onClick={strategy.has_config_schema ? submitTyped : submitRaw}
                        disabled={isPending}
                        className="flex items-center gap-1.5 px-4 py-2 rounded-[var(--radius-card)] text-xs font-semibold transition-opacity bg-primary text-bg hover:opacity-90 disabled:opacity-50"
                    >
                        {isPending ? <Loader size={11} className="animate-spin" /> : <Save size={11} />}
                        {isPending ? "Saving" : "Save as Draft"}
                    </button>
                </div>
            </motion.div>
        </div>
    )
}
