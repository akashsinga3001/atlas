"use client"

import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { motion, AnimatePresence } from "framer-motion"
import { CheckCircle2, Loader, Rocket, X } from "lucide-react"
import HudCorners from "@/components/ui/HudCorners"
import Badge from "@/components/ui/Badge"
import Skeleton from "@/components/ui/Skeleton"
import { useStrategyVersions } from "@/libraries/hooks/useStrategyVersions"
import { Strategy, StrategyVersion } from "@/libraries/types/strategy"
import { activateVersion } from "@/libraries/api/strategies"

function timeAgo(iso: string) {
    const diffMs = Date.now() - new Date(iso).getTime()
    const mins = Math.floor(diffMs / 60000)
    if (mins < 1) return "just now"
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return `${Math.floor(hrs / 24)}d ago`
}

function ActivateConfirm({ strategy, version, currentActive, onCancel, onConfirmed }: { strategy: Strategy; version: StrategyVersion; currentActive?: StrategyVersion; onCancel: () => void; onConfirmed: () => void }) {
    const queryClient = useQueryClient()
    const { mutate, isPending, error } = useMutation({
        mutationFn: () => activateVersion(strategy.id, version.id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["strategies"] })
            queryClient.invalidateQueries({ queryKey: ["strategy-versions", strategy.id] })
            onConfirmed()
        }
    })

    return (
        <div className="rounded-xl p-4 flex flex-col gap-3" style={{ background: "rgba(212,160,23,0.06)", border: "1px solid rgba(212,160,23,0.2)" }}>
            <p className="text-xs text-primary">
                Activate version <span className="font-mono font-semibold">v{version.version}</span> for <span className="font-semibold">{strategy.name}</span>?
                {currentActive && (
                    <>
                        {" "}
                        Version <span className="font-mono font-semibold">v{currentActive.version}</span> will be deactivated.
                    </>
                )}
            </p>
            <p className="text-[11px] text-secondary">The live Celery schedule still points at a fixed version ID until TODO #23 ships — activating here does not change what's currently scheduled.</p>
            {error && <p className="text-[11px] text-red-400">Failed to activate — try again.</p>}
            <div className="flex items-center justify-end gap-2">
                <button onClick={onCancel} className="px-3 py-1.5 rounded-lg text-xs font-semibold text-secondary border border-white/8 hover:text-primary transition-colors">
                    Cancel
                </button>
                <button onClick={() => mutate()} disabled={isPending} className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold border" style={{ background: "rgba(212,160,23,0.15)", color: "var(--color-accent)", borderColor: "rgba(212,160,23,0.3)" }}>
                    {isPending ? <Loader size={11} className="animate-spin" /> : <Rocket size={11} />}
                    {isPending ? "Activating" : "Confirm Activate"}
                </button>
            </div>
        </div>
    )
}

function VersionRow({ strategy, version, currentActive }: { strategy: Strategy; version: StrategyVersion; currentActive?: StrategyVersion }) {
    const [expanded, setExpanded] = useState(false)
    const [confirming, setConfirming] = useState(false)

    return (
        <div className="rounded-xl p-4 flex flex-col gap-2" style={{ background: "rgba(255,255,255,0.02)", border: "1px solid rgba(255,255,255,0.06)" }}>
            <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2.5">
                    <span className="font-mono text-sm font-bold text-primary">v{version.version}</span>
                    {version.is_active ? <Badge label="Active" variant="green" /> : <Badge label="Inactive" variant="muted" />}
                    <span className="text-[11px] text-muted font-mono">{timeAgo(version.created_at)}</span>
                </div>
                <div className="flex items-center gap-2">
                    <button onClick={() => setExpanded((e) => !e)} className="text-[11px] text-secondary hover:text-primary transition-colors">
                        {expanded ? "Hide config" : "View config"}
                    </button>
                    {!version.is_active && !confirming && (
                        <button onClick={() => setConfirming(true)} className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[11px] font-semibold text-accent border border-accent/25 hover:bg-accent/10 transition-colors">
                            <Rocket size={10} />
                            Activate
                        </button>
                    )}
                    {version.is_active && (
                        <span className="flex items-center gap-1 text-[11px] text-green-400">
                            <CheckCircle2 size={11} />
                            Live
                        </span>
                    )}
                </div>
            </div>

            <AnimatePresence>
                {expanded && (
                    <motion.pre initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: "auto" }} exit={{ opacity: 0, height: 0 }} className="overflow-hidden text-[11px] font-mono text-secondary rounded-lg p-3 whitespace-pre-wrap" style={{ background: "rgba(0,0,0,0.25)" }}>
                        {JSON.stringify(version.config, null, 2)}
                    </motion.pre>
                )}
            </AnimatePresence>

            {confirming && <ActivateConfirm strategy={strategy} version={version} currentActive={currentActive} onCancel={() => setConfirming(false)} onConfirmed={() => setConfirming(false)} />}
        </div>
    )
}

export default function StrategyVersionHistory({ strategy, onClose }: { strategy: Strategy; onClose: () => void }) {
    const { data: versions, isLoading } = useStrategyVersions(strategy.id)

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4" onClick={onClose}>
            <div className="absolute inset-0" style={{ background: "rgba(0,0,0,0.7)", backdropFilter: "blur(4px)" }} />
            <motion.div
                initial={{ opacity: 0, scale: 0.96, y: 8 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.96, y: 8 }}
                transition={{ duration: 0.18, ease: [0.23, 1, 0.32, 1] }}
                className="relative w-full max-w-xl max-h-[85vh] overflow-y-auto rounded-2xl p-6 flex flex-col gap-4"
                style={{ background: "var(--color-surface)", border: "1px solid rgba(255,255,255,0.08)", boxShadow: "0 24px 64px rgba(0,0,0,0.6)" }}
                onClick={(e) => e.stopPropagation()}
            >
                <HudCorners opacity={0.4} />
                <div className="flex items-start justify-between">
                    <div>
                        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-secondary mb-0.5">Version History</p>
                        <h2 className="text-lg font-bold text-primary leading-tight">{strategy.name}</h2>
                    </div>
                    <button onClick={onClose} className="p-1.5 rounded-lg text-muted hover:text-primary hover:bg-white/6 transition-colors">
                        <X size={14} />
                    </button>
                </div>

                {isLoading && (
                    <div className="flex flex-col gap-2">
                        {[...Array(2)].map((_, i) => (
                            <Skeleton key={i} className="h-16 rounded-xl" />
                        ))}
                    </div>
                )}

                {!isLoading && (
                    <div className="flex flex-col gap-2.5">
                        {(versions ?? []).map((v) => (
                            <VersionRow key={v.id} strategy={strategy} version={v} currentActive={versions?.find((x) => x.is_active)} />
                        ))}
                    </div>
                )}
            </motion.div>
        </div>
    )
}
