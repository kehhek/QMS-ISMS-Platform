import React, { useEffect, useState } from 'react'
import { apiFetch } from './api'

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
  if (error) return <p className="error-text">{error}</p>
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
  )
}
