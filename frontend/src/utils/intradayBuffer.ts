// Client-side, localStorage-backed buffer of {time, value} points for today only. There is no
// backend intraday (sub-daily) history anywhere — AccountSnapshot is one row per calendar day,
// full stop — so a true "1D" chart or hourly P&L breakdown isn't buildable from stored data.
// This buffer is the pragmatic substitute: every live refresh appends a point, persisted per
// browser/day so a reload doesn't lose it, but it only has data from whenever the dashboard was
// first opened today — not from market open, and a different browser/device starts empty.

const MAX_POINTS = 500

function todayKey(): string {
  return `atlas-intraday-${new Date().toISOString().slice(0, 10)}`
}

export interface IntradayPoint {
  time: number // epoch ms
  value: number
}

export function appendIntradayPoint(value: number): IntradayPoint[] {
  const key = todayKey()
  let points: IntradayPoint[] = []
  try {
    const raw = localStorage.getItem(key)
    points = raw ? JSON.parse(raw) : []
  } catch {
    points = []
  }

  points.push({ time: Date.now(), value })
  if (points.length > MAX_POINTS) points = points.slice(points.length - MAX_POINTS)

  try {
    localStorage.setItem(key, JSON.stringify(points))
    // Best-effort cleanup of any prior day's buffer so localStorage doesn't grow unbounded.
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i)
      if (k && k.startsWith("atlas-intraday-") && k !== key) localStorage.removeItem(k)
    }
  } catch {
    // localStorage unavailable (private window, quota) — buffer just won't persist this session
  }

  return points
}

export function readIntradayPoints(): IntradayPoint[] {
  try {
    const raw = localStorage.getItem(todayKey())
    return raw ? JSON.parse(raw) : []
  } catch {
    return []
  }
}
