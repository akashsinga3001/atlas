const BACKEND_PORT = 8000

// SSE connections don't survive the Next.js rewrite proxy (it buffers/breaks chunked streaming
// responses), so this one endpoint bypasses it and talks to the backend directly, using whatever
// host the page was already loaded from — no hardcoded hostname/IP.
export function createQuoteStream(tickers: string[]): EventSource {
    const backendOrigin = `${window.location.protocol}//${window.location.hostname}:${BACKEND_PORT}`
    const url = `${backendOrigin}/api/v1/quotes/stream?tickers=${tickers.join(",")}`
    return new EventSource(url)
}
