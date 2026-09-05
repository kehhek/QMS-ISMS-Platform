import React, { useState } from 'react'

// Horizontal part-to-whole stacked bar. Mark spec per the dataviz skill:
// <=24px thick, a 2px surface-color gap between touching segments (flexbox
// `gap`, not a stroke — a stroke adds ink that isn't data), 4px rounded
// caps on the outer ends only, square where segments meet. Every segment
// is its own hover/focus hit target (the mark itself, no crosshair needed
// for a bar), so hovering or tabbing to a segment surfaces its exact value
// even when the segment is too narrow for an inline label.
export default function StackedBar({ segments, height = 20 }) {
  const [hovered, setHovered] = useState(null)
  const total = segments.reduce((sum, s) => sum + s.value, 0)
  const visible = segments.filter((s) => s.value > 0)

  if (total === 0) {
    return <div className="stacked-bar-empty">No data yet</div>
  }

  return (
    <div className="stacked-bar-wrap">
      <div className="stacked-bar" style={{ height }}>
        {visible.map((s, i) => {
          const pct = (s.value / total) * 100
          const isFirst = i === 0
          const isLast = i === visible.length - 1
          return (
            <div
              key={s.label}
              className="stacked-bar-segment"
              style={{
                width: `${pct}%`,
                background: s.color,
                borderTopLeftRadius: isFirst ? 4 : 0,
                borderBottomLeftRadius: isFirst ? 4 : 0,
                borderTopRightRadius: isLast ? 4 : 0,
                borderBottomRightRadius: isLast ? 4 : 0,
              }}
              tabIndex={0}
              role="img"
              aria-label={`${s.label}: ${s.value} of ${total}`}
              onMouseEnter={() => setHovered(s)}
              onMouseLeave={() => setHovered(null)}
              onFocus={() => setHovered(s)}
              onBlur={() => setHovered(null)}
            >
              {/* Only label inline when it actually fits — a clipped or
                  overflowing label is worse than none; the tooltip below
                  is this value's home when the segment is too narrow. */}
              {pct >= 12 && <span className="stacked-bar-inline-label">{s.value}</span>}
            </div>
          )
        })}
      </div>
      {/* Reserve the row so the layout doesn't jump when a tooltip appears. */}
      <div className="stacked-bar-tooltip-row">
        {hovered ? <><strong>{hovered.value}</strong> {hovered.label}</> : ' '}
      </div>
    </div>
  )
}
