// Validated 8-hue categorical palette (fixed order — the CVD-safety mechanism, never
// cycled or re-ranked). Each pair is [light, dark]; consuming code picks by theme.
// Passes CVD/contrast checks for adjacent pairs (stacked bars, bar lists) in both modes.
const CATEGORICAL_PALETTE: [string, string][] = [
  ["#2a78d6", "#3987e5"], // blue
  ["#eb6834", "#d95926"], // orange
  ["#1baf7a", "#199e70"], // aqua
  ["#eda100", "#c98500"], // yellow
  ["#e87ba4", "#d55181"], // magenta
  ["#008300", "#008300"], // green
  ["#4a3aa7", "#9085e9"], // violet
  ["#e34948", "#e66767"], // red
]

const OTHER_COLOR: [string, string] = ["#898781", "#898781"] // muted ink — reserved for the folded "Other" bucket, never a real category's slot

/**
 * Assign a stable categorical color per label. Slots are assigned by alphabetical order
 * among the labels passed in (not by value/rank) so a label's color doesn't shift just
 * because its size changed relative to the others — "color follows the entity, never its
 * rank". Past the 8-hue ceiling, later labels (alphabetically) fold to the muted "Other"
 * color rather than generating a 9th hue, which would be indistinguishable under CVD.
 */
export function assignCategoricalColors(labels: string[], theme: "light" | "dark" = "light"): Map<string, string> {
  const modeIndex = theme === "dark" ? 1 : 0
  const sorted = [...new Set(labels)].sort((a, b) => a.localeCompare(b))
  const map = new Map<string, string>()
  sorted.forEach((label, i) => {
    map.set(label, i < CATEGORICAL_PALETTE.length ? CATEGORICAL_PALETTE[i][modeIndex] : OTHER_COLOR[modeIndex])
  })
  return map
}
