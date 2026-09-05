import React, { useEffect, useState } from 'react'
import { apiFetch } from './api'

function ChangePasswordSection({ token }) {
  const [form, setForm] = useState({ old_password: '', new_password: '' })
  const [error, setError] = useState(null)
  const [done, setDone] = useState(false)

  const submit = (e) => {
    e.preventDefault()
    setError(null)
    apiFetch('/accounts/password/change/', token, { method: 'POST', body: JSON.stringify(form) })
      .then(() => {
        setForm({ old_password: '', new_password: '' })
        setDone(true)
        setTimeout(() => setDone(false), 3000)
      })
      .catch((err) => setError(err.message))
  }

  return (
    <div className="panel" style={{ maxWidth: 360, marginTop: 24, padding: 14 }}>
      <h4 style={{ marginTop: 0 }}>Your account — change password</h4>
      {error && <p className="error-text">{error}</p>}
      <form onSubmit={submit}>
        <input
          type="password" placeholder="Current password" required
          value={form.old_password}
          onChange={(e) => setForm({ ...form, old_password: e.target.value })}
          style={{ width: '100%', marginBottom: 10 }}
        />
        <input
          type="password" placeholder="New password" required minLength={10}
          value={form.new_password}
          onChange={(e) => setForm({ ...form, new_password: e.target.value })}
          style={{ width: '100%', marginBottom: 10 }}
        />
        <div className="toolbar" style={{ padding: 0 }}>
          <button type="submit" className="btn-primary">Change Password</button>
          {done && <span className="success-text">Changed</span>}
        </div>
      </form>
    </div>
  )
}

export default function TenantSettingsPanel({ token }) {
  const [settings, setSettings] = useState(null)
  const [error, setError] = useState(null)
  const [saved, setSaved] = useState(false)

  const load = () => {
    apiFetch('/tenant/settings/', token)
      .then((data) => setSettings(data))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const save = (e) => {
    e.preventDefault()
    const { name, logo_url, primary_color, support_email, website } = settings
    apiFetch('/tenant/settings/', token, {
      method: 'PATCH',
      body: JSON.stringify({ name, logo_url, primary_color, support_email, website }),
    })
      .then((data) => {
        setSettings(data)
        setError(null)
        setSaved(true)
        setTimeout(() => setSaved(false), 2000)
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view org settings.</p>
  if (error && !settings) return <p className="error-text">{error}</p>
  if (!settings) return <p className="empty-state">Loading…</p>

  const field = (label, key, type = 'text') => (
    <div style={{ marginBottom: 12 }}>
      <label style={{ display: 'block', marginBottom: 4, fontSize: 13, color: 'var(--color-text-muted)' }}>
        {label}
      </label>
      <input
        type={type}
        value={settings[key] || ''}
        onChange={(e) => setSettings({ ...settings, [key]: e.target.value })}
        style={{ width: 320 }}
      />
    </div>
  )

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <form onSubmit={save} style={{ maxWidth: 360 }}>
        <p className="panel-hint">Schema: {settings.schema_name}</p>
        {field('Org name', 'name')}
        {field('Logo URL', 'logo_url')}
        {field('Primary color', 'primary_color')}
        {field('Support email', 'support_email', 'email')}
        {field('Website', 'website')}
        <div className="toolbar">
          <button type="submit" className="btn-primary">Save</button>
          {saved && <span className="success-text">Saved</span>}
        </div>
      </form>
      <p className="panel-hint">
        Public Trust Center (share with customers/prospects — no login required):{' '}
        <a href="/trust" target="_blank" rel="noreferrer">{window.location.origin}/trust</a>
      </p>
      <ChangePasswordSection token={token} />
    </div>
  )
}
