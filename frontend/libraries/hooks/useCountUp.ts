"use client"

import { useEffect, useRef, useState } from "react"

export function useCountUp(target: number, duration = 1200) {
    const [value, setValue] = useState(0)
    const startTime = useRef<number | null>(null)
    const frame = useRef<number>(0)

    useEffect(() => {
        if (target === 0) return
        startTime.current = null

        const tick = (now: number) => {
            if (!startTime.current) startTime.current = now
            const elapsed = now - startTime.current
            const progress = Math.min(elapsed / duration, 1)
            const eased = 1 - Math.pow(1 - progress, 3)
            setValue(Math.floor(eased * target))
            if (progress < 1) frame.current = requestAnimationFrame(tick)
            else setValue(target)
        }

        frame.current = requestAnimationFrame(tick)
        return () => cancelAnimationFrame(frame.current)
    }, [target, duration])

    return value
}
