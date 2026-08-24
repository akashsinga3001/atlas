/** Builds the SSE stream URL for live quotes — proxied through Vite dev server, same origin as the app. */
export function quoteStreamUrl(tickers: string[]): string {
  const params = new URLSearchParams({ tickers: tickers.join(",") })
  return `/api/v1/quotes/stream?${params.toString()}`
}
