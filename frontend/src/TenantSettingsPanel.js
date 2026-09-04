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

  if (!token) return <p>Set a token above to view org settings.</p>
  if (error) return <p style={{ color: 'crimson' }}>{error}</p>
  if (!settings) return <p>Loading…</p>

  const field = (label, key, type = 'text') => (
    <div style={{ marginBottom: 10 }}>
      <label style={{ display: 'inline-block', width: 140 }}>{label}</label>
      <input
        type={type}
        value={settings[key] || ''}
        onChange={(e) => setSettings({ ...settings, [key]: e.target.value })}
        style={{ width: 300 }}
      />
    </div>
  )

  return (
    <form onSubmit={save}>
      <p style={{ fontSize: 12, color: '#666' }}>Schema: {settings.schema_name}</p>
      {field('Org name', 'name')}
      {field('Logo URL', 'logo_url')}
      {field('Primary color', 'primary_color')}
      {field('Support email', 'support_email', 'email')}
      {field('Website', 'website')}
      <button type="submit">Save</button>
      {saved && <span style={{ marginLeft: 8, color: 'green' }}>Saved</span>}
    </form>
  )
}
