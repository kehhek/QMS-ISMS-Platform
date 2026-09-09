import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import useCrudPanel from './useCrudPanel'

const EMPTY_FORM = { title: '', description: '', content_type: '', object_id: '' }

export default function EvidencePanel({ token }) {
  const [contentTypes, setContentTypes] = useState([])
  const [file, setFile] = useState(null)
  const {
    items: evidence, error, setError, form, setForm, load,
    editingId, editForm, setEditForm, startEdit, cancelEdit, remove,
  } = useCrudPanel('/evidence/', token, EMPTY_FORM)

  // Not the hook's generic saveEdit: editForm.file is the file's URL
  // string (from the list response), and EvidenceSerializer's `file` is a
  // real FileField — sending that string back as "file" would fail
  // validation ("not a file"). Only title/description are editable here.
  const saveEvidenceEdit = () => {
    apiFetch(`/evidence/${editingId}/`, token, {
      method: 'PATCH',
      body: JSON.stringify({ title: editForm.title, description: editForm.description }),
    })
      .then(() => {
        cancelEdit()
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (!token) return
    apiFetch('/content-types/', token)
      .then((data) => {
        setContentTypes(data)
        if (data.length && !form.content_type) {
          setForm((f) => ({ ...f, content_type: data[0].id }))
        }
      })
      .catch(() => setContentTypes([]))
    // eslint-disable-next-line
  }, [token])

  const download = (ev) => {
    // A plain <a href> to the media URL doesn't reliably work here: the
    // dev server's proxy bypasses proxying for anything that looks like
    // an HTML navigation (checks the Accept header), so a clicked link
    // falls through to the SPA instead of reaching Django. Fetching it
    // ourselves goes through the same path as every other API call.
    fetch(ev.file, { headers: { Authorization: `Token ${token}` } })
      .then((r) => {
        if (!r.ok) throw new Error(`Download failed (${r.status})`)
        return r.blob()
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = ev.title || 'evidence'
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
      })
      .catch((err) => setError(err.message))
  }

  const upload = (e) => {
    e.preventDefault()
    if (!file) {
      setError('Choose a file first.')
      return
    }
    const body = new FormData()
    body.append('title', form.title)
    body.append('description', form.description)
    body.append('content_type', form.content_type)
    body.append('object_id', form.object_id)
    body.append('file', file)

    apiFetch('/evidence/', token, { method: 'POST', body })
      .then(() => {
        setForm({ ...form, title: '', description: '', object_id: '' })
        setFile(null)
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view evidence.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Files are encrypted at rest. "Attach to" + ID identifies the record this is evidence for
        (e.g. pick "incident" and the incident's numeric id from its own tab). Only the title and
        description can be edited after upload — re-upload as a new entry to replace the file itself.
      </p>
      <form onSubmit={upload} className="toolbar">
        <input
          placeholder="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          required
        />
        <select
          value={form.content_type}
          onChange={(e) => setForm({ ...form, content_type: e.target.value })}
        >
          {contentTypes.map((ct) => (
            <option key={ct.id} value={ct.id}>{ct.model}</option>
          ))}
        </select>
        <input
          placeholder="Record ID"
          type="number"
          value={form.object_id}
          onChange={(e) => setForm({ ...form, object_id: e.target.value })}
          style={{ width: 90 }}
          required
        />
        <input type="file" onChange={(e) => setFile(e.target.files[0])} />
        <button type="submit" className="btn-primary">Upload</button>
      </form>
      {evidence.length === 0 ? (
        <p className="empty-state">No evidence uploaded yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Description</th>
              <th>Attached To</th>
              <th>Uploaded By</th>
              <th>Uploaded At</th>
              <th>File</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {evidence.map((ev) => (
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
                  <td>{ev.content_type_name} #{ev.object_id}</td>
                  <td>{ev.uploaded_by_username || '—'}</td>
                  <td>{new Date(ev.uploaded_at).toLocaleString()}</td>
                  <td><button onClick={() => download(ev)}>Download</button></td>
                  <td>
                    <div className="cell-actions">
                      <button onClick={saveEvidenceEdit}>Save</button>
                      <button onClick={cancelEdit}>Cancel</button>
                    </div>
                  </td>
                </tr>
              ) : (
                <tr key={ev.id}>
                  <td>{ev.title}</td>
                  <td>{ev.description || '—'}</td>
                  <td>{ev.content_type_name} #{ev.object_id}</td>
                  <td>{ev.uploaded_by_username || '—'}</td>
                  <td>{new Date(ev.uploaded_at).toLocaleString()}</td>
                  <td><button onClick={() => download(ev)}>Download</button></td>
                  <td>
                    <div className="cell-actions">
                      <button onClick={() => startEdit(ev)}>Edit</button>
                      <button onClick={() => remove(ev, `"${ev.title}"`)}>Delete</button>
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
