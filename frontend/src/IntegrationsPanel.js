import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import StatusBadge from './StatusBadge'

const PROVIDERS = [
  {
    value: 'github',
    label: 'GitHub',
    configFields: [
      { key: 'owner', placeholder: 'GitHub org/user (e.g. acme-corp)' },
      { key: 'repo', placeholder: 'Repo name (e.g. backend)' },
      { key: 'branch', placeholder: 'Branch (default: main)' },
    ],
    credentialFields: [
      { key: 'token', placeholder: 'Personal access token (repo scope)', type: 'password' },
    ],
    checksDescription: 'Checks branch protection and required PR reviews on your default branch.',
  },
  {
    value: 'aws',
    label: 'AWS (S3)',
    configFields: [
      { key: 'bucket', placeholder: 'S3 bucket name' },
      { key: 'region', placeholder: 'Region (default: us-east-1)' },
    ],
    credentialFields: [
      { key: 'access_key_id', placeholder: 'Access key ID', type: 'password' },
      { key: 'secret_access_key', placeholder: 'Secret access key', type: 'password' },
    ],
    checksDescription: 'Checks default bucket encryption and public access block.',
  },
]

function emptyForm(providerValue) {
  const provider = PROVIDERS.find((p) => p.value === providerValue) || PROVIDERS[0]
  const config = {}
  provider.configFields.forEach((f) => { config[f.key] = '' })
  const credentials = {}
  provider.credentialFields.forEach((f) => { credentials[f.key] = '' })
  return { provider: provider.value, name: '', config, credentials }
}

function IntegrationCheckHistory({ integrationId, token }) {
  const [items, setItems] = useState(null)

  useEffect(() => {
    apiFetch(`/integration-check-results/?integration=${integrationId}`, token)
      .then((data) => setItems(unwrapList(data)))
      .catch(() => setItems([]))
    // eslint-disable-next-line
  }, [integrationId])

  if (items === null) return <p className="empty-state">Loading…</p>
  if (items.length === 0) return <p className="empty-state">No checks run yet — click Sync.</p>

  return (
    <table>
      <thead>
        <tr>
          <th>Check</th>
          <th>Result</th>
          <th>Detail</th>
          <th>Checked at</th>
        </tr>
      </thead>
      <tbody>
        {items.map((r) => (
          <tr key={r.id}>
            <td>{r.label}</td>
            <td><span className={`badge ${r.passed ? 'badge-success' : 'badge-danger'}`}>{r.passed ? 'pass' : 'fail'}</span></td>
            <td style={{ maxWidth: 360 }}>{r.detail}</td>
            <td>{new Date(r.checked_at).toLocaleString()}</td>
          </tr>
        ))}
      </tbody>
    </table>
  )
}

export default function IntegrationsPanel({ token }) {
  const [items, setItems] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState(emptyForm('github'))
  const [testResult, setTestResult] = useState(null)
  const [syncingId, setSyncingId] = useState(null)
  const [historyId, setHistoryId] = useState(null)

  const load = () => {
    apiFetch('/integrations/', token)
      .then((data) => setItems(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const providerDef = PROVIDERS.find((p) => p.value === form.provider)

  const create = (e) => {
    e.preventDefault()
    apiFetch('/integrations/', token, { method: 'POST', body: JSON.stringify(form) })
      .then(() => {
        setForm(emptyForm(form.provider))
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const remove = (integ) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Disconnect "${integ.name}"? Stored credentials will be deleted.`)) return
    apiFetch(`/integrations/${integ.id}/`, token, { method: 'DELETE' })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  const testConnection = (integ) => {
    setTestResult(null)
    apiFetch(`/integrations/${integ.id}/test-connection/`, token, { method: 'POST' })
      .then((data) => setTestResult({ id: integ.id, ok: true, message: JSON.stringify(data) }))
      .catch((err) => setTestResult({ id: integ.id, ok: false, message: err.message }))
  }

  const sync = (integ) => {
    setSyncingId(integ.id)
    setError(null)
    apiFetch(`/integrations/${integ.id}/sync/`, token, { method: 'POST' })
      .then(() => { load(); setHistoryId(integ.id) })
      .catch((err) => setError(err.message))
      .finally(() => setSyncingId(null))
  }

  if (!token) return <p className="empty-state">Set a token above to view integrations.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Connect a real system so its controls get verified automatically instead of just marked
        Implemented by hand — a Sync re-checks the live system, updates the matching Control's
        status, and attaches a dated Evidence entry every time. Credentials are encrypted at rest and
        never shown again after saving. Only admins can connect, edit, or remove an integration.
      </p>

      <form onSubmit={create} className="toolbar" style={{ flexWrap: 'wrap', marginBottom: 16 }}>
        <select
          value={form.provider}
          onChange={(e) => setForm(emptyForm(e.target.value))}
        >
          {PROVIDERS.map((p) => <option key={p.value} value={p.value}>{p.label}</option>)}
        </select>
        <input
          placeholder="Display name (e.g. Acme Corp GitHub)"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          style={{ width: 240 }}
          required
        />
        {providerDef.configFields.map((f) => (
          <input
            key={f.key}
            placeholder={f.placeholder}
            value={form.config[f.key] || ''}
            onChange={(e) => setForm({ ...form, config: { ...form.config, [f.key]: e.target.value } })}
            style={{ width: 200 }}
          />
        ))}
        {providerDef.credentialFields.map((f) => (
          <input
            key={f.key}
            type={f.type || 'text'}
            placeholder={f.placeholder}
            value={form.credentials[f.key] || ''}
            onChange={(e) => setForm({ ...form, credentials: { ...form.credentials, [f.key]: e.target.value } })}
            style={{ width: 220 }}
          />
        ))}
        <button type="submit" className="btn-primary">Connect</button>
        <span className="panel-hint" style={{ width: '100%', margin: '4px 0 0' }}>{providerDef.checksDescription}</span>
      </form>

      {items.length === 0 ? (
        <p className="empty-state">No integrations connected yet.</p>
      ) : (
        <div style={{ display: 'grid', gap: 12 }}>
          {items.map((integ) => (
            <div key={integ.id} className="workflow-card">
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 8 }}>
                <div>
                  <strong>{integ.name}</strong>
                  <span className="badge badge-neutral" style={{ marginLeft: 8 }}>
                    {PROVIDERS.find((p) => p.value === integ.provider)?.label || integ.provider}
                  </span>
                  <p className="panel-hint" style={{ margin: '4px 0 0' }}>
                    {integ.last_synced_at
                      ? `Last synced ${new Date(integ.last_synced_at).toLocaleString()}`
                      : 'Never synced'}
                    {integ.last_error && <span className="error-text"> — {integ.last_error}</span>}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                  <StatusBadge value={integ.status} />
                  <button onClick={() => testConnection(integ)}>Test connection</button>
                  <button onClick={() => sync(integ)} disabled={syncingId === integ.id}>
                    {syncingId === integ.id ? 'Syncing…' : 'Sync now'}
                  </button>
                  <button onClick={() => setHistoryId(historyId === integ.id ? null : integ.id)}>
                    {historyId === integ.id ? 'Hide history' : 'View history'}
                  </button>
                  <button onClick={() => remove(integ)}>Disconnect</button>
                </div>
              </div>
              {testResult && testResult.id === integ.id && (
                <p className={testResult.ok ? 'success-text' : 'error-text'} style={{ marginTop: 8 }}>
                  {testResult.ok ? `Connection OK — ${testResult.message}` : testResult.message}
                </p>
              )}
              {historyId === integ.id && (
                <div style={{ marginTop: 12, overflowX: 'auto' }}>
                  <IntegrationCheckHistory integrationId={integ.id} token={token} />
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
