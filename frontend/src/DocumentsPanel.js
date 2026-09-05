import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import StatusBadge from './StatusBadge'

export default function DocumentsPanel({ token }) {
  const [documents, setDocuments] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ title: '', content: '' })

  const load = () => {
    apiFetch('/documents/', token)
      .then((data) => setDocuments(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const createDocument = (e) => {
    e.preventDefault()
    apiFetch('/documents/', token, { method: 'POST', body: JSON.stringify(form) })
      .then(() => {
        setForm({ title: '', content: '' })
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view documents.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <form onSubmit={createDocument} className="toolbar">
        <input
          placeholder="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          required
        />
        <input
          placeholder="Content"
          value={form.content}
          onChange={(e) => setForm({ ...form, content: e.target.value })}
          style={{ width: 300 }}
        />
        <button type="submit" className="btn-primary">Add Document</button>
      </form>
      {documents.length === 0 ? (
        <p className="empty-state">No documents yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Status</th>
              <th>Version</th>
              <th>Owner</th>
              <th>Updated</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((d) => (
              <tr key={d.id}>
                <td>{d.title}</td>
                <td><StatusBadge value={d.status} /></td>
                <td>{d.version}</td>
                <td>{d.owner_username || '—'}</td>
                <td>{new Date(d.updated_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
