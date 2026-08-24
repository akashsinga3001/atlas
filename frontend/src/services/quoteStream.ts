import { quoteStreamUrl } from "@/services/api/quotes"
import type { ConnectionState, QuoteMap } from "@/types/quote"

const RECONNECT_DELAYS_MS = [1000, 2000, 5000, 10000]

export interface QuoteStreamHandle {
  close: () => void
}

/**
 * Opens a resilient SSE connection to /api/v1/quotes/stream.
 *
 * Replaces the old useLivePnL hook's behavior of closing the connection on any error with
 * no reconnect — that made a single transient hiccup look like a permanent data outage.
 * Here, a stream error triggers a backoff-scheduled reconnect instead of giving up, and the
 * last known-good quotes are never cleared — onStateChange reports the connection health
 * separately from onUpdate's data, so the UI can show "reconnecting" without blanking prices.
 */
export function createQuoteStream(tickers: string[], onUpdate: (quotes: QuoteMap) => void, onStateChange: (state: ConnectionState) => void): QuoteStreamHandle {
  let source: EventSource | null = null
  let reconnectAttempt = 0
  let reconnectTimer: ReturnType<typeof setTimeout> | null = null
  let closed = false

  function connect(): void {
    if (closed || !tickers.length) return

    onStateChange(reconnectAttempt === 0 ? "connecting" : "reconnecting")
    source = new EventSource(quoteStreamUrl(tickers))

    source.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (payload.error) return
        reconnectAttempt = 0
        onStateChange("live")
        onUpdate(payload as QuoteMap)
      } catch {
        // malformed frame — ignore, wait for the next one
      }
    }

    source.onerror = () => {
      source?.close()
      source = null
      if (closed) return
      onStateChange("reconnecting")
      const delay = RECONNECT_DELAYS_MS[Math.min(reconnectAttempt, RECONNECT_DELAYS_MS.length - 1)]
      reconnectAttempt += 1
      reconnectTimer = setTimeout(connect, delay)
    }
  }

  connect()

  return {
    close: () => {
      closed = true
      if (reconnectTimer) clearTimeout(reconnectTimer)
      source?.close()
      onStateChange("disconnected")
    },
  }
}
