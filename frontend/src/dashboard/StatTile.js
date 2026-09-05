import React from 'react'

// Stat tile per the dataviz skill's figure contract: label (sentence case,
// no trailing colon) + value (semibold, proportional figures — never
// tabular-nums here, that's reserved for columns that must align).
export default function StatTile({ label, value }) {
  return (
    <div className="stat-tile">
      <div className="stat-tile-value">{value}</div>
      <div className="stat-tile-label">{label}</div>
    </div>
  )
}
