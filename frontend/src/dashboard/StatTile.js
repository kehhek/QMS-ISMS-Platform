import React from 'react'

// Argon Dashboard-style KPI card — a muted uppercase label and a large
// bold value. Scoped via the extra `stat-tile-argon` class (see
// styles.css) so this doesn't change the plain `.stat-tile` look
// DocumentsPanel/SecurityAwarenessPanel already use for their own status
// tiles elsewhere — this component itself is only ever used here on the
// Dashboard tab.
//
// `onClick` is optional — when given, this renders as a real <button> so
// the dashboard's tiles can jump straight to the relevant tab; omit it
// and this is a plain, inert card. `icon`/`accent` still work (a small
// gradient badge on the right) but no caller currently passes one — the
// icons were tried and then removed.
export default function StatTile({ label, value, onClick, title, icon, accent = 'primary' }) {
  const body = (
    <>
      <div className="stat-tile-text">
        <div className="stat-tile-label">{label}</div>
        <div className="stat-tile-value">{value}</div>
      </div>
      {icon && <div className={`stat-tile-icon stat-tile-icon-${accent}`}>{icon}</div>}
    </>
  )
  if (onClick) {
    return (
      <button type="button" className="stat-tile stat-tile-clickable stat-tile-argon" onClick={onClick} title={title}>
        {body}
      </button>
    )
  }
  return <div className="stat-tile stat-tile-argon">{body}</div>
}
