import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'

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
    // eslint-disable-next-line react-hooks/exhaustive-deps
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

  if (!token) return <p>Set a token above to view documents.</p>

  return (
    <div>
      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      <form onSubmit={createDocument} style={{ marginBottom: 16 }}>
        <input
          placeholder="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          style={{ marginRight: 8 }}
        />
        <input
          placeholder="Content"
          value={form.content}
          onChange={(e) => setForm({ ...form, content: e.target.value })}
          style={{ marginRight: 8, width: 300 }}
        />
        <button type="submit">Add Document</button>
      </form>
      <table border="1" cellPadding="6" style={{ borderCollapse: 'collapse', width: '100%' }}>
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
              <td>{d.status}</td>
              <td>{d.version}</td>
              <td>{d.owner_username || '—'}</td>
              <td>{new Date(d.updated_at).toLocaleString()}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
