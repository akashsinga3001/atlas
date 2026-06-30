"use client"

import { useEffect, useRef, useState } from "react"

export function useCountUp(target: number, duration = 1200) {
    const [value, setValue] = useState(target)
    const fromRef = useRef(target)
    const startTime = useRef<number | null>(null)
    const frame = useRef<number>(0)
    const isFirstRun = useRef(true)

    useEffect(() => {
        // Animate the very first mount from 0; every subsequent change tweens from the last displayed value.
        const from = isFirstRun.current ? 0 : fromRef.current
        isFirstRun.current = false

        if (from === target) return
        startTime.current = null

        const tick = (now: number) => {
            if (!startTime.current) startTime.current = now
            const elapsed = now - startTime.current
            const progress = Math.min(elapsed / duration, 1)
            const eased = 1 - Math.pow(1 - progress, 3)
            setValue(from + (target - from) * eased)
            if (progress < 1) frame.current = requestAnimationFrame(tick)
            else {
                setValue(target)
                fromRef.current = target
            }
        }

        frame.current = requestAnimationFrame(tick)
        return () => cancelAnimationFrame(frame.current)
    }, [target, duration])

    return value
}
