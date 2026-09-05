import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import useCrudPanel from './useCrudPanel'
import ExportCsvButton from './ExportCsvButton'
import StatusBadge from './StatusBadge'

const TYPE_OPTIONS = ['hardware', 'software', 'data', 'facility', 'service']
const SENSITIVITY_OPTIONS = ['public', 'internal', 'confidential', 'restricted']
const STATUS_OPTIONS = ['active', 'inactive', 'under_maintenance', 'retired']
const EMPTY_FORM = {
  asset_id: '', name: '', description: '', asset_type: 'hardware',
  sensitivity: 'internal', status: 'active', owner: '',
}

function OwnerSelect({ value, onChange, members }) {
  return (
    <select value={value || ''} onChange={(e) => onChange(e.target.value || null)}>
      <option value="">— default to me —</option>
      {members.map((m) => <option key={m.user} value={m.user}>{m.username}</option>)}
    </select>
  )
}

export default function AssetsPanel({ token }) {
  const [members, setMembers] = useState([])
  const {
    items: assets, error, form, setForm, create,
    editingId, editForm, setEditForm, startEdit, cancelEdit, saveEdit, remove,
  } = useCrudPanel('/assets/', token, EMPTY_FORM)

  useEffect(() => {
    if (!token) return
    apiFetch('/tenant/members/', token).then((data) => setMembers(unwrapList(data))).catch(() => setMembers([]))
  }, [token])

  const submitCreate = (e) => {
    e.preventDefault()
    create({ ...form, owner: form.owner || null })
  }

  if (!token) return <p className="empty-state">Set a token above to view assets.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        The things a risk can be about — hardware, software, data, facilities, and services.
        Anyone can register one; editing/reassigning needs admin or auditor; only admin can remove one.
      </p>
      <form onSubmit={submitCreate} className="toolbar" style={{ flexWrap: 'wrap' }}>
        <input
          placeholder="Asset ID (e.g. AST-014)"
          value={form.asset_id}
          onChange={(e) => setForm({ ...form, asset_id: e.target.value })}
          style={{ width: 130 }}
        />
        <input
          placeholder="Asset Name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
        <select value={form.asset_type} onChange={(e) => setForm({ ...form, asset_type: e.target.value })} title="Asset Type">
          {TYPE_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
        </select>
        <span className="field-label">Owner:</span>
        <OwnerSelect value={form.owner} onChange={(v) => setForm({ ...form, owner: v })} members={members} />
        <select
          value={form.sensitivity}
          onChange={(e) => setForm({ ...form, sensitivity: e.target.value })}
          title="Security & Compliance classification"
        >
          {SENSITIVITY_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })} title="Current Status">
          {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
        <button type="submit" className="btn-primary">Add Asset</button>
        <ExportCsvButton token={token} path="/assets/" filename="assets.csv" />
      </form>
      {assets.length === 0 ? (
        <p className="empty-state">No assets registered yet.</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Asset ID</th>
                <th>Asset Name</th>
                <th>Asset Type</th>
                <th>Asset Owner</th>
                <th>Security &amp; Compliance</th>
                <th>Current Status</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {assets.map((a) => (
                editingId === a.id ? (
                  <tr key={a.id}>
                    <td>
                      <input value={editForm.asset_id} onChange={(e) => setEditForm({ ...editForm, asset_id: e.target.value })} style={{ width: 90 }} />
                    </td>
                    <td>
                      <input value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
                    </td>
                    <td>
                      <select value={editForm.asset_type} onChange={(e) => setEditForm({ ...editForm, asset_type: e.target.value })}>
                        {TYPE_OPTIONS.map((t) => <option key={t} value={t}>{t}</option>)}
                      </select>
                    </td>
                    <td>
                      <OwnerSelect value={editForm.owner} onChange={(v) => setEditForm({ ...editForm, owner: v })} members={members} />
                    </td>
                    <td>
                      <select value={editForm.sensitivity} onChange={(e) => setEditForm({ ...editForm, sensitivity: e.target.value })}>
                        {SENSITIVITY_OPTIONS.map((s) => <option key={s} value={s}>{s}</option>)}
                      </select>
                    </td>
                    <td>
                      <select value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}>
                        {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
                      </select>
                    </td>
                    <td>
                      <button onClick={saveEdit} style={{ marginRight: 4 }}>Save</button>
                      <button onClick={cancelEdit}>Cancel</button>
                    </td>
                  </tr>
                ) : (
                  <tr key={a.id}>
                    <td>{a.asset_id || '—'}</td>
                    <td>{a.name}</td>
                    <td><span className="badge badge-neutral">{a.asset_type}</span></td>
                    <td>{a.owner_username || '—'}</td>
                    <td><span className="badge badge-neutral">{a.sensitivity}</span></td>
                    <td><StatusBadge value={a.status} /></td>
                    <td>
                      <button onClick={() => startEdit(a)} style={{ marginRight: 4 }}>Edit</button>
                      <button onClick={() => remove(a, `"${a.name}"`)}>Delete</button>
                    </td>
                  </tr>
                )
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
