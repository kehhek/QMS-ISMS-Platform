import React from 'react'
import useCrudPanel from './useCrudPanel'
import StatusBadge from './StatusBadge'
import ExportCsvButton from './ExportCsvButton'

const TYPE_OPTIONS = ['corrective', 'preventive']
const STATUS_OPTIONS = ['open', 'in_progress', 'verified', 'closed']
const EMPTY_FORM = { title: '', description: '', action_type: 'corrective' }

export default function CorrectiveActionsPanel({ token }) {
  const {
    items: actions, error, form, setForm, create,
    editingId, editForm, setEditForm, startEdit, cancelEdit, saveEdit, remove,
  } = useCrudPanel('/corrective-actions/', token, EMPTY_FORM)

  if (!token) return <p className="empty-state">Set a token above to view corrective actions.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <form onSubmit={(e) => { e.preventDefault(); create() }} className="toolbar">
        <input
          placeholder="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          required
        />
        <select value={form.action_type} onChange={(e) => setForm({ ...form, action_type: e.target.value })}>
          {TYPE_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <button type="submit" className="btn-primary">Add CAPA</button>
        <ExportCsvButton token={token} path="/corrective-actions/" filename="corrective-actions.csv" />
      </form>
      {actions.length === 0 ? (
        <p className="empty-state">No corrective actions yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Type</th>
              <th>Status</th>
              <th>Owner</th>
              <th>Audit</th>
              <th>Risk</th>
              <th>Due</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {actions.map((a) => (
              editingId === a.id ? (
                <tr key={a.id}>
                  <td>
                    <input value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} />
                  </td>
                  <td>
                    <select value={editForm.action_type} onChange={(e) => setEditForm({ ...editForm, action_type: e.target.value })}>
                      {TYPE_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </td>
                  <td>
                    <select value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}>
                      {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                    </select>
                  </td>
                  <td>
                    <input value={editForm.owner} onChange={(e) => setEditForm({ ...editForm, owner: e.target.value })} style={{ width: 100 }} />
                  </td>
                  <td>{a.audit ?? '—'}</td>
                  <td>{a.risk ?? '—'}</td>
                  <td>
                    <input
                      type="date" value={editForm.due_date || ''}
                      onChange={(e) => setEditForm({ ...editForm, due_date: e.target.value || null })}
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
                  <td>{a.action_type}</td>
                  <td><StatusBadge value={a.status} /></td>
                  <td>{a.owner || '—'}</td>
                  <td>{a.audit ?? '—'}</td>
                  <td>{a.risk ?? '—'}</td>
                  <td>{a.due_date || '—'}</td>
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
