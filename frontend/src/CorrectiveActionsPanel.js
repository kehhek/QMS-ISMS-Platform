import React from 'react'
import { apiFetch } from './api'
import useCrudPanel from './useCrudPanel'
import StatusBadge from './StatusBadge'
import ExportCsvButton from './ExportCsvButton'
import { requestSignature } from './PromptDialog'

const TYPE_OPTIONS = ['corrective', 'preventive']
// 'closed' is deliberately excluded here — closing requires the signed
// close() action below, not a plain status edit (see
// CorrectiveActionViewSet.perform_update on the backend, which rejects
// a direct PATCH to closed).
const EDITABLE_STATUS_OPTIONS = ['open', 'investigation', 'action_planned', 'action_implemented', 'verification']
const EMPTY_FORM = { title: '', description: '', action_type: 'corrective' }

export default function CorrectiveActionsPanel({ token }) {
  const {
    items: actions, error, setError, form, setForm, create, load,
    editingId, editForm, setEditForm, startEdit, cancelEdit, saveEdit, remove,
  } = useCrudPanel('/corrective-actions/', token, EMPTY_FORM)

  const closeCapa = async (capa) => {
    const result = await requestSignature({
      title: 'Close this CAPA',
      message: 'This is your electronic signature verifying the fix was effective.',
      notesField: { name: 'effectiveness_notes', label: 'Effectiveness verification notes (what evidence shows the fix worked?)' },
      confirmLabel: 'Close',
    })
    if (!result) return
    apiFetch(`/corrective-actions/${capa.id}/close/`, token, {
      method: 'POST',
      body: JSON.stringify({ password: result.password, effectiveness_notes: result.effectiveness_notes || '' }),
    })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view corrective actions.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Open → Investigation → Action Planned → Action Implemented → Verification → Closed.
        Closing requires re-entering your password and an effectiveness verification note — the
        same electronic-signature pattern as document approval.
      </p>
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
              <th>Root Cause</th>
              <th>Owner</th>
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
                      {EDITABLE_STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                    </select>
                  </td>
                  <td>
                    <input
                      value={editForm.root_cause}
                      onChange={(e) => setEditForm({ ...editForm, root_cause: e.target.value })}
                      style={{ width: 160 }}
                    />
                  </td>
                  <td>
                    <input value={editForm.owner} onChange={(e) => setEditForm({ ...editForm, owner: e.target.value })} style={{ width: 100 }} />
                  </td>
                  <td>
                    <input
                      type="date" value={editForm.due_date || ''}
                      onChange={(e) => setEditForm({ ...editForm, due_date: e.target.value || null })}
                    />
                  </td>
                  <td>
                    <div className="cell-actions">
                      <button onClick={() => saveEdit()}>Save</button>
                      <button onClick={cancelEdit}>Cancel</button>
                    </div>
                  </td>
                </tr>
              ) : (
                <tr key={a.id}>
                  <td>{a.title}</td>
                  <td>{a.action_type}</td>
                  <td>
                    <StatusBadge value={a.status} />
                    {a.status === 'closed' && a.effectiveness_notes && (
                      <div className="cell-wrap" style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>{a.effectiveness_notes}</div>
                    )}
                  </td>
                  <td>{a.root_cause || '—'}</td>
                  <td>{a.owner || '—'}</td>
                  <td>{a.due_date || '—'}</td>
                  <td>
                    <div className="cell-actions">
                      {a.status !== 'closed' && (
                        <>
                          <button onClick={() => startEdit(a)}>Edit</button>
                          <button onClick={() => closeCapa(a)}>Close</button>
                        </>
                      )}
                      <button onClick={() => remove(a, `"${a.title}"`)}>Delete</button>
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
