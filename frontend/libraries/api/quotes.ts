const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"

export function createQuoteStream(tickers: string[]): EventSource {
    const url = `${BASE_URL}/quotes/stream?tickers=${tickers.join(",")}`
    return new EventSource(url)
}
