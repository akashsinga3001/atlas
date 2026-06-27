"use client"

import { useEffect, useRef, useState } from "react"

export function usePriceFlash(price: number | null | undefined): string {
    const prev = useRef<number | null>(null)
    const [flashClass, setFlashClass] = useState("")

    useEffect(() => {
        if (price == null) return
        if (prev.current !== null && price !== prev.current) {
            const cls = price > prev.current ? "flash-green" : "flash-red"
            setFlashClass(cls)
            const t = setTimeout(() => setFlashClass(""), 650)
            prev.current = price
            return () => clearTimeout(t)
        }
        prev.current = price
    }, [price])

    return flashClass
}
