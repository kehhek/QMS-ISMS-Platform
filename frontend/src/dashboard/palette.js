// Two validated palettes (see dataviz skill: run scripts/validate_palette.js,
// don't eyeball). Neither is invented — both are checked before use.
//
// STATUS_PALETTE: the skill's fixed, pre-validated status colors
// (good/warning/serious/critical). Reserved for genuine severity — used
// here only for Incident severity, a textbook fit (low->critical maps
// directly onto good->critical).
export const STATUS_PALETTE = {
  good: '#0ca30c',
  warning: '#fab219',
  serious: '#ec835a',
  critical: '#d03b3b',
}

// ORDINAL_BLUE: one hue, light->dark, for genuinely ordered lifecycle
// stages (draft->review->approved, not_implemented->...->implemented,
// planned->...->completed). Validated with --ordinal: monotone lightness,
// adjacent steps >=0.06 apart, light end clears 2:1 against a white surface.
export const ORDINAL_BLUE = ['#86b6ef', '#5598e7', '#2a78d6', '#184f95']

// A 6-step version of the same ramp (same hue, monotone lightness) for
// lifecycle charts with more than 4 stages — e.g. CorrectiveAction's
// open -> investigation -> action_planned -> action_implemented ->
// verification -> closed. Validated with `--ordinal`: monotone L, all
// adjacent gaps >= 0.06, light end clears 2:1 on a white surface, single
// hue (spread 4°).
export const ORDINAL_BLUE_6 = ['#86b6ef', '#6e9bd2', '#5680b4', '#3f6597', '#274a79', '#0f2f5c']

// Evenly-spaced steps for a chart with fewer than 4 stages, keeping
// perceptual gaps as wide as possible rather than just taking the first N.
export function ordinalSteps(n) {
  if (n <= 1) return [ORDINAL_BLUE[2]]
  if (n === 2) return [ORDINAL_BLUE[0], ORDINAL_BLUE[3]]
  if (n === 3) return [ORDINAL_BLUE[0], ORDINAL_BLUE[2], ORDINAL_BLUE[3]]
  if (n === 4) return ORDINAL_BLUE
  if (n <= 6) return ORDINAL_BLUE_6.slice(0, n)
  return ORDINAL_BLUE_6
}

export const SEVERITY_COLORS = [
  STATUS_PALETTE.good, STATUS_PALETTE.warning, STATUS_PALETTE.serious, STATUS_PALETTE.critical,
]
