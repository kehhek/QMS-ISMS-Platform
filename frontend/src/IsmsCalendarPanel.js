import React, { useEffect, useState } from 'react'
import { apiFetch } from './api'
import StatusBadge from './StatusBadge'

const KIND_LABELS = {
  audit: 'Audit',
  corrective_action: 'Corrective/Preventive Action',
  risk: 'Risk treatment',
  training: 'Security awareness training',
}

function EventRow({ event, tone }) {
  const daysFromToday = Math.round((new Date(event.date) - new Date(new Date().toDateString())) / 86400000)
  const relative =
    tone === 'danger'
      ? `${Math.abs(daysFromToday)} day${Math.abs(daysFromToday) === 1 ? '' : 's'} overdue`
      : daysFromToday === 0
        ? 'due today'
        : `in ${daysFromToday} day${daysFromToday === 1 ? '' : 's'}`

  return (
    <tr>
      <td><span className="badge badge-neutral">{KIND_LABELS[event.kind] || event.kind}</span></td>
      <td>{event.title}</td>
      <td>{event.date}</td>
      <td><span className={`badge badge-${tone}`}>{relative}</span></td>
      <td><StatusBadge value={event.status} /></td>
    </tr>
  )
}

function EventTable({ events, tone, emptyLabel }) {
  if (events.length === 0) return <p className="empty-state">{emptyLabel}</p>
  return (
    <table>
      <thead>
        <tr>
          <th>Type</th>
          <th>Title</th>
          <th>Date</th>
          <th>When</th>
          <th>Status</th>
        </tr>
      </thead>
      <tbody>
        {events.map((e) => <EventRow key={`${e.kind}-${e.id}`} event={e} tone={tone} />)}
      </tbody>
    </table>
  )
}

export default function IsmsCalendarPanel({ token }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    apiFetch('/isms-calendar/', token)
      .then(setData)
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  if (!token) return <p className="empty-state">Set a token above to view the ISMS calendar.</p>
  if (error) return <p className="error-text">{error}</p>
  if (!data) return <p className="empty-state">Loading…</p>

  return (
    <div>
      <p className="panel-hint">
        Every ISMS date that matters, in one place: planned audits, corrective/preventive action
        due dates, risk treatment target dates, and security awareness training due dates.
      </p>

      {data.overdue.length > 0 && (
        <p className="notice-box">
          {data.overdue.length} item{data.overdue.length === 1 ? ' is' : 's are'} past due — review below.
        </p>
      )}

      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h4>Past due ({data.overdue.length})</h4>
          <EventTable events={data.overdue} tone="danger" emptyLabel="Nothing overdue." />
        </div>
        <div className="dashboard-card">
          <h4>Upcoming ({data.upcoming.length})</h4>
          <EventTable events={data.upcoming} tone="warning" emptyLabel="Nothing scheduled yet." />
        </div>
      </div>
    </div>
  )
}
