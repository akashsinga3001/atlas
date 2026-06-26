"use client"

import { useEffect, useRef, useState } from "react"
import { createQuoteStream } from "../api/quotes"

export interface LiveQuote {
    last_price: number | null
    change_pct: number | null
    volume: number | null
    high: number | null
    low: number | null
}

export function useLivePnL(tickers: string[]): Record<string, LiveQuote> {
    const [quotes, setQuotes] = useState<Record<string, LiveQuote>>({})
    const esRef = useRef<EventSource | null>(null)
    const tickersKey = tickers.slice().sort().join(",")

    useEffect(() => {
        if (!tickers.length) return

        const es = createQuoteStream(tickers)
        esRef.current = es

        es.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data)
                if (!data.error) {
                    setQuotes(data)
                }
            } catch {
                // ignore malformed frames
            }
        }

        es.onerror = () => {
            es.close()
        }

        return () => {
            es.close()
            esRef.current = null
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [tickersKey])

    return quotes
}
