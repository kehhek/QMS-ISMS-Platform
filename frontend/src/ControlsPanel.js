import React, { useEffect, useState } from 'react'
import { apiFetch, apiFetchUrl, unwrapList, downloadFile } from './api'
import ExportCsvButton from './ExportCsvButton'
import StatusBadge from './StatusBadge'

const STATUS_OPTIONS = ['not_implemented', 'partial', 'implemented', 'not_applicable']

const FRAMEWORK_LABELS = {
  iso27001: 'ISO 27001',
  soc2: 'SOC 2',
  hipaa: 'HIPAA',
  gdpr: 'GDPR',
  pci_dss: 'PCI DSS',
  nist_csf: 'NIST CSF',
  custom: 'Custom',
}

// The two frameworks auto-seeded at registration aren't offered here —
// this is only the "add another certification" list.
const ADDITIONAL_FRAMEWORKS = ['hipaa', 'gdpr', 'pci_dss', 'nist_csf']

function FrameworkCoverage({ token, onSeeded }) {
  const [seededFrameworks, setSeededFrameworks] = useState(null)
  const [previewFramework, setPreviewFramework] = useState('')
  const [coverage, setCoverage] = useState(null)
  const [error, setError] = useState(null)

  const loadSeeded = () => {
    apiFetch('/controls/?page_size=1', token)
      .then(() => {
        // Cheap presence check per framework — a single COUNT-shaped call
        // per framework, not the whole control list.
        Promise.all(
          ADDITIONAL_FRAMEWORKS.map((f) =>
            apiFetch(`/controls/?framework=${f}&page_size=1`, token).then((d) => [f, d.count > 0]),
          ),
        ).then((pairs) => setSeededFrameworks(Object.fromEntries(pairs)))
      })
      .catch(() => setSeededFrameworks({}))
  }

  useEffect(() => {
    loadSeeded()
    // eslint-disable-next-line
  }, [])

  const preview = (fw) => {
    setPreviewFramework(fw)
    setCoverage(null)
    apiFetch(`/controls/framework-coverage/?framework=${fw}`, token)
      .then(setCoverage)
      .catch((err) => setError(err.message))
  }

  const addFramework = (fw) => {
    apiFetch('/controls/seed-framework/', token, { method: 'POST', body: JSON.stringify({ framework: fw }) })
      .then((data) => {
        setError(null)
        loadSeeded()
        onSeeded()
        // eslint-disable-next-line no-alert
        window.alert(`Added ${data.added_count} ${FRAMEWORK_LABELS[fw]} controls (${data.total_count} total).`)
      })
      .catch((err) => setError(err.message))
  }

  return (
    <div className="workflow-card" style={{ marginBottom: 16 }}>
      <p className="panel-hint" style={{ margin: '0 0 8px' }}>
        Pursuing another certification? Preview how much of it your existing ISO 27001/SOC 2 work
        already covers before adding it — controls that map to the same underlying requirement
        (e.g. access control, encryption, incident response) count as already covered once the
        source control is Implemented.
      </p>
      {error && <p className="error-text">{error}</p>}
      <div className="toolbar" style={{ flexWrap: 'wrap' }}>
        {ADDITIONAL_FRAMEWORKS.map((fw) => (
          <span key={fw} style={{ display: 'inline-flex', gap: 4, alignItems: 'center' }}>
            <button type="button" onClick={() => preview(fw)}>Preview {FRAMEWORK_LABELS[fw]}</button>
            {seededFrameworks && seededFrameworks[fw] ? (
              <span className="badge badge-success">added</span>
            ) : (
              <button type="button" onClick={() => addFramework(fw)}>+ Add</button>
            )}
          </span>
        ))}
      </div>
      {previewFramework && (
        coverage === null ? (
          <p className="empty-state">Loading…</p>
        ) : (
          <div style={{ marginTop: 10 }}>
            <div className="stat-row">
              <div className="stat-tile stat-tile-accent-success">
                <div className="stat-tile-value">{coverage.coverage_percent}%</div>
                <div className="stat-tile-label">already covered</div>
              </div>
              <div className="stat-tile">
                <div className="stat-tile-value">{coverage.already_covered_count}/{coverage.total_controls}</div>
                <div className="stat-tile-label">controls</div>
              </div>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table>
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Name</th>
                    <th>Already covered by</th>
                  </tr>
                </thead>
                <tbody>
                  {coverage.controls.map((c) => (
                    <tr key={c.identifier}>
                      <td>{c.identifier}</td>
                      <td>{c.name}</td>
                      <td>
                        {c.already_covered ? (
                          c.covering_controls.map((cc) => (
                            <span key={`${cc.framework}-${cc.identifier}`} className="badge badge-success" style={{ marginRight: 4 }}>
                              {FRAMEWORK_LABELS[cc.framework] || cc.framework} {cc.identifier}
                            </span>
                          ))
                        ) : (
                          <span className="badge badge-neutral">not yet</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )
      )}
    </div>
  )
}

function ControlMappings({ token, control }) {
  const [mappings, setMappings] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    apiFetch(`/controls/${control.id}/mappings/`, token)
      .then(setMappings)
      .catch((err) => setError(err.message))
    // eslint-disable-next-line
  }, [control.id])

  if (error) return <p className="error-text">{error}</p>
  if (mappings === null) return <p className="empty-state">Loading…</p>
  if (mappings.length === 0) return <p className="empty-state">No cross-framework mapping recorded for this control.</p>

  return (
    <div style={{ padding: '10px 4px' }}>
      <table>
        <thead>
          <tr>
            <th>Framework</th>
            <th>ID</th>
            <th>Theme</th>
            <th>In this tenant</th>
          </tr>
        </thead>
        <tbody>
          {mappings.map((m) => (
            <tr key={`${m.framework}-${m.identifier}`}>
              <td><span className="badge badge-neutral">{FRAMEWORK_LABELS[m.framework] || m.framework}</span></td>
              <td>{m.identifier}</td>
              <td>{m.theme}</td>
              <td>{m.seeded ? <StatusBadge value={m.status} /> : <span className="badge badge-neutral">not added yet</span>}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
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
  const [mappingsId, setMappingsId] = useState(null)

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

  const downloadSoa = () => {
    setError(null)
    const query = framework ? `?framework=${framework}` : ''
    downloadFile(`/reports/statement-of-applicability/${query}`, token, 'statement-of-applicability.pdf')
      .catch((err) => setError(err.message))
  }

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Use "View / Add" on a control's row to attach screenshots, policy excerpts, or any other
        supporting image/document directly to that control — the same encrypted evidence store used
        everywhere else, filtered down to just this control. Fill in "SoA Justification" (why a
        control is or isn't applicable) and "Download Statement of Applicability" generates the
        real ISO 27001 SoA document on demand — status, owner, and attached evidence are pulled
        live, not retyped. "Maps to" shows which other frameworks' controls cover the same
        underlying requirement.
      </p>

      <FrameworkCoverage token={token} onSeeded={load} />

      <div className="toolbar">
        <span className="field-label">Framework:</span>
        <select value={framework} onChange={(e) => setFramework(e.target.value)}>
          <option value="">All ({page.count})</option>
          {Object.entries(FRAMEWORK_LABELS).filter(([v]) => v !== 'custom').map(([value, label]) => (
            <option key={value} value={value}>{label}</option>
          ))}
        </select>
        <ExportCsvButton token={token} path="/controls/" filename="controls.csv" />
        <button type="button" onClick={downloadPdf}>Download PDF Report</button>
        <button type="button" onClick={downloadSoa}>Download Statement of Applicability</button>
      </div>
      <table>
        <thead>
          <tr>
            <th>Framework</th>
            <th>ID</th>
            <th>Name</th>
            <th>Status</th>
            <th>Owner</th>
            <th>SoA Justification</th>
            <th>Attachments</th>
            <th>Maps to</th>
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
                  <input
                    defaultValue={c.soa_justification}
                    placeholder="Why applicable / N/A"
                    title="Shown on the generated Statement of Applicability"
                    onBlur={(e) => {
                      if (e.target.value !== c.soa_justification) updateControl(c, { soa_justification: e.target.value })
                    }}
                    style={{ width: 180 }}
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
                <td>
                  <button type="button" onClick={() => setMappingsId(mappingsId === c.id ? null : c.id)}>
                    {mappingsId === c.id ? 'Hide' : 'Maps to'}
                  </button>
                </td>
              </tr>
              {expandedId === c.id && controlContentTypeId && (
                <tr>
                  <td colSpan={8} style={{ background: 'var(--color-bg)' }}>
                    <ControlAttachments token={token} control={c} contentTypeId={controlContentTypeId} />
                  </td>
                </tr>
              )}
              {mappingsId === c.id && (
                <tr>
                  <td colSpan={8} style={{ background: 'var(--color-bg)' }}>
                    <ControlMappings token={token} control={c} />
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
