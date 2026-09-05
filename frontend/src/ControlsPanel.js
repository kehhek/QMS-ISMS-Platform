import React, { useEffect, useState } from 'react'
import { apiFetch, apiFetchUrl, unwrapList, downloadFile } from './api'
import ExportCsvButton from './ExportCsvButton'

const STATUS_OPTIONS = ['not_implemented', 'partial', 'implemented', 'not_applicable']

const FRAMEWORK_LABELS = {
  iso27001: 'ISO 27001',
  soc2: 'SOC 2',
  custom: 'Custom',
}

function ControlAttachments({ token, control, contentTypeId }) {
  const [items, setItems] = useState(null) // null = not loaded yet
  const [error, setError] = useState(null)
  const [title, setTitle] = useState('')
  const [file, setFile] = useState(null)

  const load = () => {
    apiFetch(`/evidence/?content_type=${contentTypeId}&object_id=${control.id}`, token)
      .then((data) => setItems(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line
  }, [])

  const upload = (e) => {
    e.preventDefault()
    if (!file) {
      setError('Choose an image or document first.')
      return
    }
    const body = new FormData()
    body.append('title', title || file.name)
    body.append('content_type', contentTypeId)
    body.append('object_id', control.id)
    body.append('file', file)

    apiFetch('/evidence/', token, { method: 'POST', body })
      .then(() => {
        setTitle('')
        setFile(null)
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const download = (ev) => {
    // Same reasoning as EvidencePanel's download(): a bespoke authenticated
    // fetch, not a plain <a href>, since the dev proxy won't forward an
    // HTML-navigation-shaped request the way it forwards fetch() calls.
    fetch(ev.file, { headers: { Authorization: `Token ${token}` } })
      .then((r) => {
        if (!r.ok) throw new Error(`Download failed (${r.status})`)
        return r.blob()
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = ev.title || 'attachment'
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
      })
      .catch((err) => setError(err.message))
  }

  const remove = (ev) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Delete "${ev.title}"? This can't be undone.`)) return
    apiFetch(`/evidence/${ev.id}/`, token, { method: 'DELETE' })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  return (
    <div style={{ padding: '10px 4px' }}>
      {error && <p className="error-text">{error}</p>}
      <form onSubmit={upload} className="toolbar" style={{ flexWrap: 'wrap' }}>
        <input
          placeholder="Label (optional — defaults to filename)"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          style={{ width: 220 }}
        />
        <input
          type="file"
          accept="image/*,.pdf,.doc,.docx,.xls,.xlsx,.csv,.txt"
          onChange={(e) => setFile(e.target.files[0])}
        />
        <button type="submit" className="btn-primary">Attach</button>
      </form>
      {items === null ? (
        <p className="empty-state">Loading…</p>
      ) : items.length === 0 ? (
        <p className="empty-state">No images or documents attached to this control yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Uploaded by</th>
              <th>Uploaded at</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((ev) => (
              <tr key={ev.id}>
                <td>{ev.title}</td>
                <td>{ev.uploaded_by_username || '—'}</td>
                <td>{new Date(ev.uploaded_at).toLocaleString()}</td>
                <td>
                  <button onClick={() => download(ev)} style={{ marginRight: 4 }}>Download</button>
                  <button onClick={() => remove(ev)}>Delete</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

export default function ControlsPanel({ token }) {
  const [page, setPage] = useState(null) // raw paginated response
  const [framework, setFramework] = useState('')
  const [error, setError] = useState(null)
  const [controlContentTypeId, setControlContentTypeId] = useState(null)
  const [expandedId, setExpandedId] = useState(null)

  const load = (url) => {
    const req = url
      ? apiFetchUrl(url, token)
      : apiFetch(`/controls/${framework ? `?framework=${framework}` : ''}`, token)
    req.then(setPage).catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token, framework])

  useEffect(() => {
    if (!token) return
    apiFetch('/content-types/', token)
      .then((data) => {
        const control = data.find((ct) => ct.model === 'control')
        if (control) setControlContentTypeId(control.id)
      })
      .catch(() => setControlContentTypeId(null))
  }, [token])

  const updateControl = (control, changes) => {
    apiFetch(`/controls/${control.id}/`, token, { method: 'PATCH', body: JSON.stringify(changes) })
      .then((updated) => {
        setPage({
          ...page,
          results: page.results.map((c) => (c.id === updated.id ? updated : c)),
        })
        setError(null)
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view controls.</p>
  if (error && !page) return <p className="error-text">{error}</p>
  if (!page) return <p className="empty-state">Loading…</p>

  const controls = unwrapList(page)

  const downloadPdf = () => {
    setError(null)
    downloadFile('/reports/controls-status/', token, 'controls-status-report.pdf').catch((err) => setError(err.message))
  }

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Use "View / Add" on a control's row to attach screenshots, policy excerpts, or any other
        supporting image/document directly to that control — the same encrypted evidence store used
        everywhere else, filtered down to just this control.
      </p>
      <div className="toolbar">
        <span className="field-label">Framework:</span>
        <select value={framework} onChange={(e) => setFramework(e.target.value)}>
          <option value="">All ({page.count})</option>
          <option value="iso27001">ISO 27001</option>
          <option value="soc2">SOC 2</option>
        </select>
        <ExportCsvButton token={token} path="/controls/" filename="controls.csv" />
        <button type="button" onClick={downloadPdf}>Download PDF Report</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Framework</th>
            <th>ID</th>
            <th>Name</th>
            <th>Status</th>
            <th>Owner</th>
            <th>Attachments</th>
          </tr>
        </thead>
        <tbody>
          {controls.map((c) => (
            <React.Fragment key={c.id}>
              <tr>
                <td><span className="badge badge-neutral">{FRAMEWORK_LABELS[c.framework] || c.framework}</span></td>
                <td>{c.identifier}</td>
                <td>{c.name}</td>
                <td>
                  <select value={c.status} onChange={(e) => updateControl(c, { status: e.target.value })}>
                    {STATUS_OPTIONS.map((s) => (
                      <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>
                    ))}
                  </select>
                </td>
                <td>
                  <input
                    defaultValue={c.owner}
                    onBlur={(e) => {
                      if (e.target.value !== c.owner) updateControl(c, { owner: e.target.value })
                    }}
                    style={{ width: 120 }}
                  />
                </td>
                <td>
                  <button
                    type="button"
                    disabled={!controlContentTypeId}
                    onClick={() => setExpandedId(expandedId === c.id ? null : c.id)}
                  >
                    {expandedId === c.id ? 'Hide' : 'View / Add'}
                  </button>
                </td>
              </tr>
              {expandedId === c.id && controlContentTypeId && (
                <tr>
                  <td colSpan={6} style={{ background: 'var(--color-bg)' }}>
                    <ControlAttachments token={token} control={c} contentTypeId={controlContentTypeId} />
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
      <div className="pagination">
        <button disabled={!page.previous} onClick={() => load(page.previous)}>Previous</button>
        <span>{controls.length ? `showing ${controls.length} of ${page.count}` : ''}</span>
        <button disabled={!page.next} onClick={() => load(page.next)}>Next</button>
      </div>
    </div>
  )
}
