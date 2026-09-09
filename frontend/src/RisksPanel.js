import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import useCrudPanel from './useCrudPanel'
import ExportCsvButton from './ExportCsvButton'
import StatusBadge from './StatusBadge'

const STATUS_OPTIONS = ['open', 'mitigating', 'closed']
const EMPTY_FORM = { name: '', description: '', likelihood: 1, impact: 1, asset: '' }

export default function RisksPanel({ token }) {
  const [assets, setAssets] = useState([])
  const {
    items: risks, error, form, setForm, create,
    editingId, editForm, setEditForm, startEdit, cancelEdit, saveEdit, remove,
  } = useCrudPanel('/risks/', token, EMPTY_FORM)

  useEffect(() => {
    if (!token) return
    apiFetch('/assets/', token).then((data) => setAssets(unwrapList(data))).catch(() => setAssets([]))
  }, [token])

  const submitCreate = (e) => {
    e.preventDefault()
    create({ ...form, asset: form.asset || null })
  }

  if (!token) return <p className="empty-state">Set a token above to view risks.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <form onSubmit={submitCreate} className="toolbar">
        <input
          placeholder="Name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
        <input
          type="number"
          min="1"
          max="5"
          value={form.likelihood}
          onChange={(e) => setForm({ ...form, likelihood: Number(e.target.value) })}
          style={{ width: 60 }}
          title="Likelihood"
        />
        <input
          type="number"
          min="1"
          max="5"
          value={form.impact}
          onChange={(e) => setForm({ ...form, impact: Number(e.target.value) })}
          style={{ width: 60 }}
          title="Impact"
        />
        <select value={form.asset} onChange={(e) => setForm({ ...form, asset: e.target.value })}>
          <option value="">No linked asset</option>
          {assets.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
        </select>
        <button type="submit" className="btn-primary">Add Risk</button>
        <ExportCsvButton token={token} path="/risks/" filename="risks.csv" />
      </form>
      {risks.length === 0 ? (
        <p className="empty-state">No risks yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Status</th>
              <th>Likelihood</th>
              <th>Impact</th>
              <th>Asset</th>
              <th>Owner</th>
              <th>Target date</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {risks.map((r) => (
              editingId === r.id ? (
                <tr key={r.id}>
                  <td>
                    <input value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
                  </td>
                  <td>
                    <select value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}>
                      {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </td>
                  <td>
                    <input
                      type="number" min="1" max="5" style={{ width: 50 }}
                      value={editForm.likelihood}
                      onChange={(e) => setEditForm({ ...editForm, likelihood: Number(e.target.value) })}
                    />
                  </td>
                  <td>
                    <input
                      type="number" min="1" max="5" style={{ width: 50 }}
                      value={editForm.impact}
                      onChange={(e) => setEditForm({ ...editForm, impact: Number(e.target.value) })}
                    />
                  </td>
                  <td>
                    <select
                      value={editForm.asset || ''}
                      onChange={(e) => setEditForm({ ...editForm, asset: e.target.value || null })}
                    >
                      <option value="">No linked asset</option>
                      {assets.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
                    </select>
                  </td>
                  <td>
                    <input value={editForm.owner} onChange={(e) => setEditForm({ ...editForm, owner: e.target.value })} style={{ width: 100 }} />
                  </td>
                  <td>
                    <input
                      type="date" value={editForm.target_date || ''}
                      onChange={(e) => setEditForm({ ...editForm, target_date: e.target.value || null })}
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
                <tr key={r.id}>
                  <td>{r.name}</td>
                  <td><StatusBadge value={r.status} /></td>
                  <td>{r.likelihood}</td>
                  <td>{r.impact}</td>
                  <td>{r.asset_name || '—'}</td>
                  <td>{r.owner || '—'}</td>
                  <td>{r.target_date || '—'}</td>
                  <td>
                    <div className="cell-actions">
                      <button onClick={() => startEdit(r)}>Edit</button>
                      <button onClick={() => remove(r, `"${r.name}"`)}>Delete</button>
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
