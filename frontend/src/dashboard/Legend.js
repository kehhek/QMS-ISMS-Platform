import React from 'react'

// A legend is always present for 2+ series (the dependable identity
// channel — never make the reader rely on color-matching alone).
export default function Legend({ items }) {
  return (
    <div className="chart-legend">
      {items.map((it) => (
        <span key={it.label} className="chart-legend-item">
          <span className="chart-legend-swatch" style={{ background: it.color }} />
          {it.label}
        </span>
      ))}
    </div>
  )
}
