"use client"

import { useEffect, useRef, useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { motion, AnimatePresence } from "framer-motion"
import { AlertTriangle, Loader, ShieldCheck } from "lucide-react"
import { useKillSwitch } from "@/libraries/hooks/useKillSwitch"
import { activateKillSwitch, deactivateKillSwitch } from "@/libraries/api/killSwitch"

function timeAgo(iso: string) {
    const mins = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
    if (mins < 1) return "just now"
    if (mins < 60) return `${mins}m ago`
    const hrs = Math.floor(mins / 60)
    if (hrs < 24) return `${hrs}h ago`
    return `${Math.floor(hrs / 24)}d ago`
}

export default function KillSwitchControl() {
    const { data: status } = useKillSwitch()
    const [open, setOpen] = useState(false)
    const [confirmingPause, setConfirmingPause] = useState(false)
    const [reason, setReason] = useState("")
    const ref = useRef<HTMLDivElement>(null)
    const queryClient = useQueryClient()

    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (ref.current && !ref.current.contains(e.target as Node)) {
                setOpen(false)
                setConfirmingPause(false)
            }
        }
        document.addEventListener("mousedown", handler)
        return () => document.removeEventListener("mousedown", handler)
    }, [])

    const activateMutation = useMutation({
        mutationFn: () => activateKillSwitch(reason),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["kill-switch"] })
            setOpen(false)
            setConfirmingPause(false)
            setReason("")
        }
    })

    const deactivateMutation = useMutation({
        mutationFn: () => deactivateKillSwitch(),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ["kill-switch"] })
            setOpen(false)
        }
    })

    if (!status) return null
    const active = status.enabled

    return (
        <div ref={ref} className="relative">
            <button
                onClick={() => setOpen((o) => !o)}
                className="flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-semibold transition-colors"
                style={{ background: active ? "rgba(248,113,113,0.12)" : "rgba(74,222,128,0.08)", border: `1px solid ${active ? "rgba(248,113,113,0.3)" : "rgba(74,222,128,0.2)"}` }}
            >
                <span className={`hud-dot ${active ? "hud-dot-error live-pulse" : "hud-dot-live"}`} />
                <span style={{ color: active ? "#f87171" : "rgba(74,222,128,0.9)" }}>{active ? "Entries Paused" : "Trading Active"}</span>
            </button>

            <AnimatePresence>
                {open && (
                    <motion.div
                        initial={{ opacity: 0, y: -4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -4 }}
                        transition={{ duration: 0.15 }}
                        className="absolute right-0 mt-2 w-72 rounded-xl p-4 z-50"
                        style={{ background: "var(--color-surface)", border: "1px solid rgba(255,255,255,0.1)", boxShadow: "0 12px 40px rgba(0,0,0,0.5)" }}
                    >
                        {active ? (
                            <div className="flex flex-col gap-3">
                                <div className="flex items-center gap-2">
                                    <AlertTriangle size={14} className="text-red-400" />
                                    <span className="text-sm font-bold text-primary">New entries paused</span>
                                </div>
                                {status.reason && <p className="text-xs text-secondary">{status.reason}</p>}
                                {status.activated_at && <p className="text-[11px] text-muted font-mono">since {timeAgo(status.activated_at)}</p>}
                                <p className="text-[11px] text-secondary">Exits, trailing stops, and reconciliation keep running normally.</p>
                                <button
                                    onClick={() => deactivateMutation.mutate()}
                                    disabled={deactivateMutation.isPending}
                                    className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold transition-colors"
                                    style={{ background: "rgba(74,222,128,0.12)", color: "#4ade80", border: "1px solid rgba(74,222,128,0.25)" }}
                                >
                                    {deactivateMutation.isPending ? <Loader size={11} className="animate-spin" /> : <ShieldCheck size={11} />}
                                    Resume New Entries
                                </button>
                            </div>
                        ) : !confirmingPause ? (
                            <div className="flex flex-col gap-3">
                                <span className="text-sm font-bold text-primary">Trading active</span>
                                <p className="text-[11px] text-secondary">All entry and exit jobs running normally.</p>
                                <button onClick={() => setConfirmingPause(true)} className="flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-red-400 border border-red-500/25 hover:bg-red-500/10 transition-colors">
                                    <AlertTriangle size={11} />
                                    Pause New Entries
                                </button>
                            </div>
                        ) : (
                            <div className="flex flex-col gap-3">
                                <span className="text-sm font-bold text-primary">Why pause new entries?</span>
                                <textarea
                                    value={reason}
                                    onChange={(e) => setReason(e.target.value)}
                                    rows={3}
                                    placeholder="Required — shown in the audit trail and Discord alert"
                                    className="w-full px-3 py-2 rounded-lg text-xs text-primary bg-transparent border border-white/8 focus:border-red-400/40 focus:outline-none transition-colors"
                                    style={{ background: "var(--color-surface2)" }}
                                />
                                <div className="flex items-center gap-2">
                                    <button onClick={() => setConfirmingPause(false)} className="flex-1 px-3 py-2 rounded-lg text-xs font-semibold text-secondary border border-white/8 hover:text-primary transition-colors">
                                        Cancel
                                    </button>
                                    <button
                                        onClick={() => activateMutation.mutate()}
                                        disabled={!reason.trim() || activateMutation.isPending}
                                        className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 rounded-lg text-xs font-semibold text-red-400 border border-red-500/25 disabled:opacity-40 transition-colors"
                                    >
                                        {activateMutation.isPending ? <Loader size={11} className="animate-spin" /> : <AlertTriangle size={11} />}
                                        Confirm
                                    </button>
                                </div>
                            </div>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    )
}
