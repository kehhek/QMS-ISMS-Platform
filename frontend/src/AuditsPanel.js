import React from 'react'
import useCrudPanel from './useCrudPanel'
import StatusBadge from './StatusBadge'
import ExportCsvButton from './ExportCsvButton'

const TYPE_OPTIONS = ['internal', 'external', 'certification']
const STATUS_OPTIONS = ['planned', 'in_progress', 'completed', 'cancelled']
const EMPTY_FORM = { title: '', scope: '', audit_type: 'internal' }

export default function AuditsPanel({ token }) {
  const {
    items: audits, error, form, setForm, create,
    editingId, editForm, setEditForm, startEdit, cancelEdit, saveEdit, remove,
  } = useCrudPanel('/audits/', token, EMPTY_FORM)

  if (!token) return <p className="empty-state">Set a token above to view audits.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Creating or editing an audit requires the "admin" or "auditor" role in this tenant (or superuser).
      </p>
      <form onSubmit={(e) => { e.preventDefault(); create() }} className="toolbar">
        <input
          placeholder="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          required
        />
        <select value={form.audit_type} onChange={(e) => setForm({ ...form, audit_type: e.target.value })}>
          {TYPE_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <button type="submit" className="btn-primary">Add Audit</button>
        <ExportCsvButton token={token} path="/audits/" filename="audits.csv" />
      </form>
      {audits.length === 0 ? (
        <p className="empty-state">No audits yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Type</th>
              <th>Status</th>
              <th>Auditor</th>
              <th>Scheduled</th>
              <th>Completed</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {audits.map((a) => (
              editingId === a.id ? (
                <tr key={a.id}>
                  <td>
                    <input value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} />
                  </td>
                  <td>
                    <select value={editForm.audit_type} onChange={(e) => setEditForm({ ...editForm, audit_type: e.target.value })}>
                      {TYPE_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </td>
                  <td>
                    <select value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}>
                      {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                    </select>
                  </td>
                  <td>
                    <input value={editForm.auditor} onChange={(e) => setEditForm({ ...editForm, auditor: e.target.value })} style={{ width: 110 }} />
                  </td>
                  <td>
                    <input
                      type="date" value={editForm.scheduled_date || ''}
                      onChange={(e) => setEditForm({ ...editForm, scheduled_date: e.target.value || null })}
                    />
                  </td>
                  <td>
                    <input
                      type="date" value={editForm.completed_date || ''}
                      onChange={(e) => setEditForm({ ...editForm, completed_date: e.target.value || null })}
                    />
                  </td>
                  <td>
                    <button onClick={saveEdit} style={{ marginRight: 4 }}>Save</button>
                    <button onClick={cancelEdit}>Cancel</button>
                  </td>
                </tr>
              ) : (
                <tr key={a.id}>
                  <td>{a.title}</td>
                  <td>{a.audit_type}</td>
                  <td><StatusBadge value={a.status} /></td>
                  <td>{a.auditor || '—'}</td>
                  <td>{a.scheduled_date || '—'}</td>
                  <td>{a.completed_date || '—'}</td>
                  <td>
                    <button onClick={() => startEdit(a)} style={{ marginRight: 4 }}>Edit</button>
                    <button onClick={() => remove(a, `"${a.title}"`)}>Delete</button>
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
