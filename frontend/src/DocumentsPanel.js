import React from 'react'
import useCrudPanel from './useCrudPanel'
import StatusBadge from './StatusBadge'
import ExportCsvButton from './ExportCsvButton'

const EMPTY_FORM = { title: '', content: '' }

export default function DocumentsPanel({ token }) {
  const {
    items: documents, error, form, setForm, create,
    editingId, editForm, setEditForm, startEdit, cancelEdit, saveEdit, remove,
  } = useCrudPanel('/documents/', token, EMPTY_FORM)

  if (!token) return <p className="empty-state">Set a token above to view documents.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Status changes only through an approval workflow (see the Approvals tab) — it can't be
        edited directly here, so every "approved" document has a matching electronic signature.
      </p>
      <form onSubmit={(e) => { e.preventDefault(); create() }} className="toolbar">
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
        <ExportCsvButton token={token} path="/documents/" filename="documents.csv" />
      </form>
      {documents.length === 0 ? (
        <p className="empty-state">No documents yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Content</th>
              <th>Status</th>
              <th>Version</th>
              <th>Owner</th>
              <th>Updated</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents.map((d) => (
              editingId === d.id ? (
                <tr key={d.id}>
                  <td>
                    <input value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} />
                  </td>
                  <td>
                    <input
                      value={editForm.content}
                      onChange={(e) => setEditForm({ ...editForm, content: e.target.value })}
                      style={{ width: 220 }}
                    />
                  </td>
                  <td><StatusBadge value={d.status} /></td>
                  <td>{d.version}</td>
                  <td>{d.owner_username || '—'}</td>
                  <td>{new Date(d.updated_at).toLocaleString()}</td>
                  <td>
                    <button onClick={saveEdit} style={{ marginRight: 4 }}>Save</button>
                    <button onClick={cancelEdit}>Cancel</button>
                  </td>
                </tr>
              ) : (
                <tr key={d.id}>
                  <td>{d.title}</td>
                  <td>{d.content || '—'}</td>
                  <td><StatusBadge value={d.status} /></td>
                  <td>{d.version}</td>
                  <td>{d.owner_username || '—'}</td>
                  <td>{new Date(d.updated_at).toLocaleString()}</td>
                  <td>
                    <button onClick={() => startEdit(d)} style={{ marginRight: 4 }}>Edit</button>
                    <button onClick={() => remove(d, `"${d.title}"`)}>Delete</button>
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
