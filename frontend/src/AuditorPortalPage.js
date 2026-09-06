import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'

const FRAMEWORK_LABELS = { iso27001: 'ISO 27001', soc2: 'SOC 2', custom: 'Custom' }

// Public, no-account, read-only page an external auditor opens from a
// link created in the console's Auditor Access panel. Every file link
// below (evidence/policy) is itself a plain, unauthenticated GET keyed
// by the same access_token — unlike the questionnaire/agreement flows,
// there's no data to submit here, so a plain <a href> works; no blob-
// fetch-then-objectURL dance needed since there's no Authorization
// header to attach in the first place.
export default function AuditorPortalPage() {
  const { token } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch(`/api/public/auditor-access/${token}/`)
      .then(async (r) => {
        const body = await r.json().catch(() => null)
        if (!r.ok) throw new Error((body && body.detail) || 'This link is not valid or has expired.')
        return body
      })
      .then(setData)
      .catch((err) => setError(err.message))
  }, [token])

  if (error) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <h2>Link not valid</h2>
          <p className="panel-hint">{error}</p>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="marketing">
        <p className="empty-state" style={{ marginTop: 60, textAlign: 'center' }}>Loading…</p>
      </div>
    )
  }

  return (
    <div className="marketing">
      <header className="marketing-header">
        <div className="marketing-logo">{data.organization_name} — Auditor Access</div>
      </header>

      <section style={{ marginBottom: 32 }}>
        <h1 style={{ marginBottom: 6 }}>{data.title}</h1>
        <p className="panel-hint">
          {data.framework ? `Scoped to ${FRAMEWORK_LABELS[data.framework] || data.framework} only. ` : 'All frameworks in scope. '}
          This link expires {new Date(data.expires_at).toLocaleString()}.
        </p>
      </section>

      <section style={{ marginBottom: 40 }}>
        <h3 style={{ marginBottom: 10 }}>Controls ({data.controls.length})</h3>
        {data.controls.length === 0 ? (
          <p className="empty-state">No controls in scope.</p>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table>
              <thead>
                <tr>
                  <th>Framework</th>
                  <th>ID</th>
                  <th>Name</th>
                  <th>Description</th>
                  <th>Status</th>
                  <th>Owner</th>
                  <th>Evidence</th>
                </tr>
              </thead>
              <tbody>
                {data.controls.map((c) => (
                  <tr key={c.id}>
                    <td><span className="badge badge-neutral">{FRAMEWORK_LABELS[c.framework] || c.framework}</span></td>
                    <td>{c.identifier}</td>
                    <td>{c.name}</td>
                    <td style={{ maxWidth: 280 }}>{c.description || '—'}</td>
                    <td><span className="badge badge-neutral">{c.status.replace(/_/g, ' ')}</span></td>
                    <td>{c.owner || '—'}</td>
                    <td>
                      {c.evidence.length === 0 ? '—' : c.evidence.map((ev) => (
                        <div key={ev.id}>
                          <a href={ev.file}>{ev.title}</a>
                        </div>
                      ))}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>

      <section style={{ marginBottom: 40 }}>
        <h3 style={{ marginBottom: 10 }}>Approved policies ({data.policies.length})</h3>
        {data.policies.length === 0 ? (
          <p className="empty-state">No approved policies.</p>
        ) : (
          <table>
            <thead>
              <tr>
                <th>Doc ID</th>
                <th>Title</th>
                <th>Version</th>
                <th>Classification</th>
                <th>File</th>
              </tr>
            </thead>
            <tbody>
              {data.policies.map((p) => (
                <tr key={p.id}>
                  <td>{p.doc_id || '—'}</td>
                  <td>{p.title}</td>
                  <td>{p.version}</td>
                  <td><span className="badge badge-neutral">{p.classification}</span></td>
                  <td>{p.file ? <a href={p.file}>Download</a> : '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <footer className="marketing-footer">
        <p>This is a scoped, time-limited view generated for audit purposes only.</p>
      </footer>
    </div>
  )
}
