// Animates a numeric value from its previous value to a new target via requestAnimationFrame,
// calling onUpdate with the eased intermediate value each frame. Used for hero figures (Total
// P&L, account size) so they count up on load/refresh instead of snapping — a deliberate small
// touch matching the reference dashboards' animated stat tiles, not a generic spinner.

function easeOutCubic(t: number): number {
  return 1 - Math.pow(1 - t, 3)
}

export function animateNumber(from: number, to: number, durationMs: number, onUpdate: (value: number) => void): void {
  const start = performance.now()
  const delta = to - from

  function tick(now: number) {
    const elapsed = now - start
    const progress = Math.min(elapsed / durationMs, 1)
    onUpdate(from + delta * easeOutCubic(progress))
    if (progress < 1) requestAnimationFrame(tick)
  }

  requestAnimationFrame(tick)
}
