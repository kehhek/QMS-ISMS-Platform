import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import StatusBadge from './StatusBadge'
import { requestSignature } from './PromptDialog'

export const KIND_LABELS = {
  audit: 'Audit',
  corrective_action: 'Corrective/Preventive Action',
  risk: 'Risk treatment',
  training: 'Security awareness training',
  custom: 'Custom event',
}

// Categorical identity colors, one per event kind — the dataviz skill's
// validated 8-slot categorical theme (fixed order, CVD-checked adjacent
// pairs), using slots 1-5. Used only as a small dot next to the title,
// never as a filled background with text on it — text stays in normal
// ink (see styles.css), the dot alone carries identity, per the skill's
// "text wears text tokens, never the series color" rule.
const KIND_COLORS = {
  audit: '#2a78d6',
  corrective_action: '#eb6834',
  risk: '#1baf7a',
  training: '#eda100',
  custom: '#e87ba4',
}

export function KindDot({ kind }) {
  return (
    <span
      style={{
        display: 'inline-block', width: 8, height: 8, borderRadius: '50%',
        background: KIND_COLORS[kind] || '#999', marginRight: 6, flexShrink: 0,
      }}
    />
  )
}

// Where to PATCH a reschedule and which date field each event kind
// actually stores it under — one lookup table instead of five near-
// identical branches wherever a caller needs it.
const RESCHEDULE_TARGET = {
  audit: { path: (id) => `/audits/${id}/`, field: 'scheduled_date' },
  corrective_action: { path: (id) => `/corrective-actions/${id}/`, field: 'due_date' },
  risk: { path: (id) => `/risks/${id}/`, field: 'target_date' },
  training: { path: (id) => `/training-records/${id}/`, field: 'due_date' },
  custom: { path: (id) => `/calendar-events/${id}/`, field: 'date' },
}

function EventRow({ event, tone, token, onChange }) {
  const [draftDate, setDraftDate] = useState(event.date)
  const [rescheduling, setRescheduling] = useState(false)
  // The row's key (kind+id) stays stable across a reload even though its
  // data refreshes — React reuses this component instance rather than
  // remounting it, so draftDate would otherwise still show whatever date
  // was here at first mount if reschedule is opened a second time after
  // a save already changed event.date underneath it.
  const startReschedule = () => {
    setDraftDate(event.date)
    setRescheduling(true)
  }
  const [error, setError] = useState(null)

  const daysFromToday = Math.round((new Date(event.date) - new Date(new Date().toDateString())) / 86400000)
  const relative =
    tone === 'danger'
      ? `${Math.abs(daysFromToday)} day${Math.abs(daysFromToday) === 1 ? '' : 's'} overdue`
      : daysFromToday === 0
        ? 'due today'
        : `in ${daysFromToday} day${daysFromToday === 1 ? '' : 's'}`

  const run = (promise) => promise.then(() => { setError(null); onChange() }).catch((err) => setError(err.message))

  const saveReschedule = () => {
    const target = RESCHEDULE_TARGET[event.kind]
    setRescheduling(false)
    run(apiFetch(target.path(event.id), token, {
      method: 'PATCH',
      body: JSON.stringify({ [target.field]: draftDate }),
    }))
  }

  const markDone = async () => {
    if (event.kind === 'audit') {
      run(apiFetch(`/audits/${event.id}/`, token, {
        method: 'PATCH',
        body: JSON.stringify({ status: 'completed', completed_date: toIsoDate(new Date()) }),
      }))
    } else if (event.kind === 'corrective_action') {
      // Same signed-close flow as the Corrective Actions tab — closing a
      // CAPA is a deliberate, electronically-signed act, not a checkbox.
      const result = await requestSignature({
        title: 'Close this CAPA',
        message: 'This is your electronic signature verifying the fix was effective.',
        notesField: { name: 'effectiveness_notes', label: 'Effectiveness verification notes (what evidence shows the fix worked?)' },
        confirmLabel: 'Close',
      })
      if (!result) return
      run(apiFetch(`/corrective-actions/${event.id}/close/`, token, {
        method: 'POST',
        body: JSON.stringify({ password: result.password, effectiveness_notes: result.effectiveness_notes || '' }),
      }))
    } else if (event.kind === 'risk') {
      run(apiFetch(`/risks/${event.id}/`, token, {
        method: 'PATCH',
        body: JSON.stringify({ status: 'closed' }),
      }))
    } else if (event.kind === 'training') {
      run(apiFetch(`/training-records/${event.id}/complete/`, token, { method: 'POST' }))
    }
  }

  const removeCustom = () => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Delete "${event.title}"? This can't be undone.`)) return
    run(apiFetch(`/calendar-events/${event.id}/`, token, { method: 'DELETE' }))
  }

  return (
    <tr>
      <td><KindDot kind={event.kind} />{KIND_LABELS[event.kind] || event.kind}</td>
      <td>{event.title}</td>
      <td>
        {rescheduling ? (
          <div className="cell-actions">
            <input type="date" value={draftDate} onChange={(e) => setDraftDate(e.target.value)} />
            <button onClick={saveReschedule}>Save</button>
            <button onClick={() => { setRescheduling(false); setDraftDate(event.date) }}>Cancel</button>
          </div>
        ) : (
          event.date
        )}
      </td>
      <td><span className={`badge badge-${tone}`}>{relative}</span></td>
      <td>{event.status ? <StatusBadge value={event.status} /> : '—'}</td>
      <td>
        {error && <p className="error-text" style={{ margin: '0 0 4px' }}>{error}</p>}
        <div className="cell-actions">
          {!rescheduling && <button onClick={startReschedule}>Reschedule</button>}
          {event.kind === 'custom' ? (
            <button onClick={removeCustom}>Delete</button>
          ) : (
            <button onClick={markDone}>
              {event.kind === 'corrective_action' ? 'Close' : event.kind === 'training' ? 'Mark complete' : 'Mark done'}
            </button>
          )}
        </div>
      </td>
    </tr>
  )
}

export function EventTable({ events, tone, emptyLabel, token, onChange }) {
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
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {events.map((e) => (
          <EventRow key={`${e.kind}-${e.id}`} event={e} tone={tone} token={token} onChange={onChange} />
        ))}
      </tbody>
    </table>
  )
}

const WEEKDAY_LABELS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']

function toIsoDate(date) {
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

function MonthGrid({ monthCursor, setMonthCursor, eventsByDate }) {
  const year = monthCursor.getFullYear()
  const month = monthCursor.getMonth()
  const firstOfMonth = new Date(year, month, 1)
  const startWeekday = firstOfMonth.getDay()
  const daysInMonth = new Date(year, month + 1, 0).getDate()
  const todayIso = toIsoDate(new Date())

  const cells = []
  for (let i = 0; i < startWeekday; i++) cells.push(null)
  for (let day = 1; day <= daysInMonth; day++) cells.push(day)
  while (cells.length % 7 !== 0) cells.push(null)

  const monthLabel = monthCursor.toLocaleDateString(undefined, { month: 'long', year: 'numeric' })

  return (
    <div>
      <div className="toolbar" style={{ justifyContent: 'space-between' }}>
        <div>
          <button type="button" onClick={() => setMonthCursor(new Date(year, month - 1, 1))}>‹ Prev</button>
          <button
            type="button"
            onClick={() => setMonthCursor(new Date(new Date().getFullYear(), new Date().getMonth(), 1))}
            style={{ margin: '0 6px' }}
          >
            Today
          </button>
          <button type="button" onClick={() => setMonthCursor(new Date(year, month + 1, 1))}>Next ›</button>
        </div>
        <strong>{monthLabel}</strong>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, 1fr)', gap: 4 }}>
        {WEEKDAY_LABELS.map((w) => (
          <div key={w} style={{ fontSize: 11, color: 'var(--color-text-muted)', textAlign: 'center', padding: '4px 0' }}>
            {w}
          </div>
        ))}
        {cells.map((day, i) => {
          if (day === null) return <div key={i} />
          const iso = toIsoDate(new Date(year, month, day))
          const dayEvents = eventsByDate[iso] || []
          const isToday = iso === todayIso
          return (
            <div
              key={i}
              className="panel"
              style={{
                minHeight: 74, padding: 6, fontSize: 11,
                border: isToday ? '2px solid var(--color-primary)' : undefined,
              }}
            >
              <div style={{ fontWeight: isToday ? 700 : 400, marginBottom: 4 }}>{day}</div>
              {dayEvents.slice(0, 3).map((e) => (
                <div key={`${e.kind}-${e.id}`} style={{ display: 'flex', alignItems: 'center', marginBottom: 2 }} title={e.title}>
                  <KindDot kind={e.kind} />
                  <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{e.title}</span>
                </div>
              ))}
              {dayEvents.length > 3 && (
                <div style={{ color: 'var(--color-text-muted)' }}>+{dayEvents.length - 3} more</div>
              )}
            </div>
          )
        })}
      </div>
      <div className="toolbar" style={{ marginTop: 10 }}>
        {Object.entries(KIND_LABELS).map(([kind, label]) => (
          <span key={kind} style={{ display: 'inline-flex', alignItems: 'center', fontSize: 11, marginRight: 12 }}>
            <KindDot kind={kind} />{label}
          </span>
        ))}
      </div>
    </div>
  )
}

function CustomEventsSection({ token, onChange }) {
  const [events, setEvents] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ title: '', description: '', date: '' })
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState(null)

  const load = () => {
    apiFetch('/calendar-events/', token)
      .then((data) => setEvents(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => { if (token) load() }, [token]) // eslint-disable-line

  const create = (e) => {
    e.preventDefault()
    apiFetch('/calendar-events/', token, { method: 'POST', body: JSON.stringify(form) })
      .then(() => {
        setForm({ title: '', description: '', date: '' })
        setError(null)
        load()
        onChange()
      })
      .catch((err) => setError(err.message))
  }

  const startEdit = (ev) => { setEditingId(ev.id); setEditForm({ ...ev }) }
  const cancelEdit = () => { setEditingId(null); setEditForm(null) }

  const saveEdit = () => {
    apiFetch(`/calendar-events/${editingId}/`, token, { method: 'PATCH', body: JSON.stringify(editForm) })
      .then(() => {
        setEditingId(null)
        setEditForm(null)
        setError(null)
        load()
        onChange()
      })
      .catch((err) => setError(err.message))
  }

  const remove = (ev) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Delete "${ev.title}"? This can't be undone.`)) return
    apiFetch(`/calendar-events/${ev.id}/`, token, { method: 'DELETE' })
      .then(() => { setError(null); load(); onChange() })
      .catch((err) => setError(err.message))
  }

  return (
    <div style={{ marginTop: 24 }}>
      <h4>Custom Events</h4>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        For the one kind of date nothing else implies — an external audit visit, a board review.
        Adding/editing/deleting requires the admin or auditor role.
      </p>
      <form onSubmit={create} className="toolbar">
        <input
          placeholder="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          required
        />
        <input
          placeholder="Description (optional)"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          style={{ width: 200 }}
        />
        <input
          type="date"
          value={form.date}
          onChange={(e) => setForm({ ...form, date: e.target.value })}
          required
        />
        <button type="submit" className="btn-primary">Add Event</button>
      </form>
      {events.length === 0 ? (
        <p className="empty-state">No custom events yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Description</th>
              <th>Date</th>
              <th>Added by</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {events.map((ev) => (
              editingId === ev.id ? (
                <tr key={ev.id}>
                  <td>
                    <input value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} />
                  </td>
                  <td>
                    <input
                      value={editForm.description}
                      onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                      style={{ width: 160 }}
                    />
                  </td>
                  <td>
                    <input type="date" value={editForm.date} onChange={(e) => setEditForm({ ...editForm, date: e.target.value })} />
                  </td>
                  <td>{ev.created_by_username || '—'}</td>
                  <td>
                    <div className="cell-actions">
                      <button onClick={saveEdit}>Save</button>
                      <button onClick={cancelEdit}>Cancel</button>
                    </div>
                  </td>
                </tr>
              ) : (
                <tr key={ev.id}>
                  <td>{ev.title}</td>
                  <td>{ev.description || '—'}</td>
                  <td>{ev.date}</td>
                  <td>{ev.created_by_username || '—'}</td>
                  <td>
                    <div className="cell-actions">
                      <button onClick={() => startEdit(ev)}>Edit</button>
                      <button onClick={() => remove(ev)}>Delete</button>
                    </div>
                  </td>
                </tr>
              )
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default function IsmsCalendarPanel({ token }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [viewMode, setViewMode] = useState('month')
  const [monthCursor, setMonthCursor] = useState(() => {
    const now = new Date()
    return new Date(now.getFullYear(), now.getMonth(), 1)
  })

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

  const allEvents = [...data.overdue, ...data.upcoming]
  const eventsByDate = {}
  for (const e of allEvents) {
    if (!eventsByDate[e.date]) eventsByDate[e.date] = []
    eventsByDate[e.date].push(e)
  }

  return (
    <div>
      <p className="panel-hint">
        Every ISMS date that matters, in one place: planned audits, corrective/preventive action
        due dates, risk treatment target dates, security awareness training due dates, and any
        custom events you add below. Switch to List view to act on an item directly — reschedule
        it, or mark it done — without leaving this tab.
      </p>

      {data.overdue.length > 0 && (
        <p className="notice-box">
          {data.overdue.length} item{data.overdue.length === 1 ? ' is' : 's are'} past due — review below.
        </p>
      )}

      <div className="toolbar">
        <button
          className={viewMode === 'month' ? 'btn-primary' : undefined}
          onClick={() => setViewMode('month')}
        >
          Month
        </button>
        <button
          className={viewMode === 'list' ? 'btn-primary' : undefined}
          onClick={() => setViewMode('list')}
        >
          List
        </button>
      </div>

      {viewMode === 'month' ? (
        <MonthGrid monthCursor={monthCursor} setMonthCursor={setMonthCursor} eventsByDate={eventsByDate} />
      ) : (
        <div className="dashboard-grid">
          <div className="dashboard-card">
            <h4>Past due ({data.overdue.length})</h4>
            <EventTable events={data.overdue} tone="danger" emptyLabel="Nothing overdue." token={token} onChange={load} />
          </div>
          <div className="dashboard-card">
            <h4>Upcoming ({data.upcoming.length})</h4>
            <EventTable events={data.upcoming} tone="warning" emptyLabel="Nothing scheduled yet." token={token} onChange={load} />
          </div>
        </div>
      )}

      <CustomEventsSection token={token} onChange={load} />
    </div>
  )
}
