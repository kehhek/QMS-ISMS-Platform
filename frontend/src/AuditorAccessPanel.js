import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'

const FRAMEWORK_OPTIONS = [
  { value: '', label: 'All frameworks' },
  { value: 'iso27001', label: 'ISO 27001' },
  { value: 'soc2', label: 'SOC 2' },
]

function defaultExpiry() {
  // 14 days out, formatted for <input type="datetime-local">.
  const d = new Date(Date.now() + 14 * 24 * 60 * 60 * 1000)
  d.setSeconds(0, 0)
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

function statusOf(a) {
  if (a.revoked_at) return { label: 'revoked', tone: 'danger' }
  if (!a.is_active) return { label: 'expired', tone: 'neutral' }
  return { label: 'active', tone: 'success' }
}

export default function AuditorAccessPanel({ token }) {
  const [items, setItems] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState({ title: '', framework: '', notes: '', expires_at: defaultExpiry() })
  const [copiedId, setCopiedId] = useState(null)

  const load = () => {
    apiFetch('/auditor-access/', token)
      .then((data) => setItems(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const create = (e) => {
    e.preventDefault()
    apiFetch('/auditor-access/', token, {
      method: 'POST',
      body: JSON.stringify({ ...form, expires_at: new Date(form.expires_at).toISOString() }),
    })
      .then(() => {
        setForm({ title: '', framework: '', notes: '', expires_at: defaultExpiry() })
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const revoke = (a) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Revoke "${a.title}"? The link stops working immediately.`)) return
    apiFetch(`/auditor-access/${a.id}/revoke/`, token, { method: 'POST' })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  const copyLink = (a) => {
    const link = `${window.location.origin}/auditor/${a.access_token}`
    if (navigator.clipboard) {
      navigator.clipboard.writeText(link).then(() => {
        setCopiedId(a.id)
        setTimeout(() => setCopiedId(null), 2000)
      })
    }
  }

  if (!token) return <p className="empty-state">Set a token above to view auditor access links.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Give an external auditor a scoped, read-only link to exactly the controls (optionally one
        framework only), their attached evidence, and Approved policies they need to certify you —
        no account for them, and it stops working on its own at the expiry date, or immediately if
        you revoke it. Only admins can create or revoke a link.
      </p>

      <form onSubmit={create} className="toolbar" style={{ flexWrap: 'wrap' }}>
        <input
          placeholder="Title (e.g. ISO 27001 2026 Certification Audit)"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          style={{ width: 300 }}
          required
        />
        <select value={form.framework} onChange={(e) => setForm({ ...form, framework: e.target.value })}>
          {FRAMEWORK_OPTIONS.map((f) => <option key={f.value} value={f.value}>{f.label}</option>)}
        </select>
        <span className="field-label">Expires:</span>
        <input
          type="datetime-local"
          value={form.expires_at}
          onChange={(e) => setForm({ ...form, expires_at: e.target.value })}
          required
        />
        <input
          placeholder="Notes (e.g. auditor name/firm)"
          value={form.notes}
          onChange={(e) => setForm({ ...form, notes: e.target.value })}
          style={{ width: 220 }}
        />
        <button type="submit" className="btn-primary">Create link</button>
      </form>

      {items.length === 0 ? (
        <p className="empty-state">No auditor access links yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Framework</th>
              <th>Status</th>
              <th>Expires</th>
              <th>Last accessed</th>
              <th>Notes</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((a) => {
              const s = statusOf(a)
              return (
                <tr key={a.id}>
                  <td>{a.title}</td>
                  <td>{FRAMEWORK_OPTIONS.find((f) => f.value === a.framework)?.label || a.framework}</td>
                  <td><span className={`badge badge-${s.tone}`}>{s.label}</span></td>
                  <td>{new Date(a.expires_at).toLocaleString()}</td>
                  <td>{a.last_accessed_at ? new Date(a.last_accessed_at).toLocaleString() : 'never'}</td>
                  <td>{a.notes || '—'}</td>
                  <td>
                    <div className="cell-actions">
                      <button onClick={() => copyLink(a)}>
                        {copiedId === a.id ? 'Copied!' : 'Copy link'}
                      </button>
                      {s.label === 'active' && (
                        <button onClick={() => revoke(a)}>Revoke</button>
                      )}
                    </div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      )}
    </div>
  )
}
