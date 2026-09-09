import React from 'react'

// A legend is always present for 2+ series (the dependable identity
// channel — never make the reader rely on color-matching alone).
//
// `onItemClick(item)` is optional — when given, each row becomes a real
// button (drilling into that status elsewhere in the app); omit it and
// this renders exactly as it always did, plain inert labels.
export default function Legend({ items, onItemClick }) {
  return (
    <div className="chart-legend">
      {items.map((it) => {
        const swatch = <span className="chart-legend-swatch" style={{ background: it.color }} />
        if (onItemClick) {
          return (
            <button
              key={it.label}
              type="button"
              className="chart-legend-item chart-legend-item-clickable"
              onClick={() => onItemClick(it)}
              title={`View ${it.label} (${it.value})`}
            >
              {swatch}
              {it.label}
            </button>
          )
        }
        return (
          <span key={it.label} className="chart-legend-item">
            {swatch}
            {it.label}
          </span>
        )
      })}
    </div>
  )
}
