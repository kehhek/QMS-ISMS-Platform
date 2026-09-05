import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import StatusBadge from './StatusBadge'

const STATUS_OPTIONS = ['active', 'under_review', 'inactive']

const EMPTY_FORM = {
  name: '', description: '', contact_name: '', contact_email: '',
  contact_phone: '', website: '', status: 'under_review', notes: '',
}

export default function SupplierPanel({ token }) {
  const [suppliers, setSuppliers] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState(null)

  const load = () => {
    apiFetch('/suppliers/', token)
      .then((data) => setSuppliers(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const createSupplier = (e) => {
    e.preventDefault()
    apiFetch('/suppliers/', token, { method: 'POST', body: JSON.stringify(form) })
      .then(() => {
        setForm(EMPTY_FORM)
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const startEdit = (s) => {
    setEditingId(s.id)
    setEditForm({ ...s })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditForm(null)
  }

  const saveEdit = () => {
    apiFetch(`/suppliers/${editingId}/`, token, { method: 'PATCH', body: JSON.stringify(editForm) })
      .then(() => {
        setEditingId(null)
        setEditForm(null)
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const deleteSupplier = (s) => {
    if (!window.confirm(`Delete supplier "${s.name}"? This can't be undone.`)) return
    apiFetch(`/suppliers/${s.id}/`, token, { method: 'DELETE' })
      .then(() => {
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view suppliers.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <form onSubmit={createSupplier} className="toolbar">
        <input
          placeholder="Name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
        <input
          placeholder="Contact name"
          value={form.contact_name}
          onChange={(e) => setForm({ ...form, contact_name: e.target.value })}
        />
        <input
          placeholder="Contact email"
          type="email"
          value={form.contact_email}
          onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
        />
        <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
          {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
        <button type="submit" className="btn-primary">Add Supplier</button>
      </form>

      {suppliers.length === 0 ? (
        <p className="empty-state">No suppliers yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Contact</th>
              <th>Email</th>
              <th>Status</th>
              <th>Website</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {suppliers.map((s) => (
              editingId === s.id ? (
                <tr key={s.id}>
                  <td>
                    <input value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
                  </td>
                  <td>
                    <input
                      value={editForm.contact_name}
                      onChange={(e) => setEditForm({ ...editForm, contact_name: e.target.value })}
                    />
                  </td>
                  <td>
                    <input
                      value={editForm.contact_email}
                      onChange={(e) => setEditForm({ ...editForm, contact_email: e.target.value })}
                    />
                  </td>
                  <td>
                    <select value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}>
                      {STATUS_OPTIONS.map((st) => <option key={st} value={st}>{st.replace('_', ' ')}</option>)}
                    </select>
                  </td>
                  <td>
                    <input value={editForm.website} onChange={(e) => setEditForm({ ...editForm, website: e.target.value })} />
                  </td>
                  <td>
                    <button onClick={saveEdit} style={{ marginRight: 4 }}>Save</button>
                    <button onClick={cancelEdit}>Cancel</button>
                  </td>
                </tr>
              ) : (
                <tr key={s.id}>
                  <td>{s.name}</td>
                  <td>{s.contact_name || '—'}</td>
                  <td>{s.contact_email || '—'}</td>
                  <td><StatusBadge value={s.status} /></td>
                  <td>{s.website ? <a href={s.website} target="_blank" rel="noreferrer">{s.website}</a> : '—'}</td>
                  <td>
                    <button onClick={() => startEdit(s)} style={{ marginRight: 4 }}>Edit</button>
                    <button onClick={() => deleteSupplier(s)}>Delete</button>
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
