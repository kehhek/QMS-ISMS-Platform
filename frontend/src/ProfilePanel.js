import React, { useEffect, useState } from 'react'
import { apiFetch } from './api'

export default function ProfilePanel({ token }) {
  const [profile, setProfile] = useState(null)
  const [form, setForm] = useState(null)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(null)
  const [saving, setSaving] = useState(false)

  const [pwForm, setPwForm] = useState({ old_password: '', new_password: '' })
  const [pwError, setPwError] = useState(null)
  const [pwSuccess, setPwSuccess] = useState(null)
  const [pwSaving, setPwSaving] = useState(false)

  const load = () => {
    apiFetch('/accounts/me/', token)
      .then((data) => {
        setProfile(data)
        setForm({ first_name: data.first_name, last_name: data.last_name, email: data.email })
      })
      .catch((err) => setError(err.message))
  }

  useEffect(() => { if (token) load() }, [token]) // eslint-disable-line

  const saveProfile = (e) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    setSuccess(null)
    apiFetch('/accounts/me/', token, { method: 'PATCH', body: JSON.stringify(form) })
      .then((data) => {
        setProfile(data)
        setSuccess('Profile updated.')
      })
      .catch((err) => setError(err.message))
      .finally(() => setSaving(false))
  }

  const changePassword = (e) => {
    e.preventDefault()
    setPwSaving(true)
    setPwError(null)
    setPwSuccess(null)
    apiFetch('/accounts/password/change/', token, { method: 'POST', body: JSON.stringify(pwForm) })
      .then(() => {
        setPwForm({ old_password: '', new_password: '' })
        setPwSuccess('Password changed.')
      })
      .catch((err) => setPwError(err.message))
      .finally(() => setPwSaving(false))
  }

  if (!token) return <p className="empty-state">Set a token above to view your profile.</p>
  if (!profile || !form) return error ? <p className="error-text">{error}</p> : <p className="empty-state">Loading…</p>

  return (
    <div>
      <div className="dashboard-grid">
        <div className="dashboard-card">
          <h4>Your profile</h4>
          <p className="panel-hint">
            Username, role, and account dates are fixed — an admin manages those from the Members
            tab. Name and email are yours to update.
          </p>
          {error && <p className="error-text">{error}</p>}
          {success && <p className="success-text">{success}</p>}
          <form onSubmit={saveProfile}>
            <div className="modal-field">
              <label className="modal-field-label">Username</label>
              <input value={profile.username} disabled />
            </div>
            <div className="modal-field">
              <label className="modal-field-label">Role in this org</label>
              <input value={profile.role || '—'} disabled />
            </div>
            <div className="modal-field">
              <label className="modal-field-label">First name</label>
              <input
                value={form.first_name}
                onChange={(e) => setForm({ ...form, first_name: e.target.value })}
              />
            </div>
            <div className="modal-field">
              <label className="modal-field-label">Last name</label>
              <input
                value={form.last_name}
                onChange={(e) => setForm({ ...form, last_name: e.target.value })}
              />
            </div>
            <div className="modal-field">
              <label className="modal-field-label">Email</label>
              <input
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
              />
            </div>
            <p className="panel-hint" style={{ margin: '0 0 12px' }}>
              Member since {new Date(profile.date_joined).toLocaleDateString()}
              {profile.last_login && ` — last logged in ${new Date(profile.last_login).toLocaleString()}`}.
            </p>
            <button type="submit" className="btn-primary" disabled={saving}>
              {saving ? 'Saving…' : 'Save changes'}
            </button>
          </form>
        </div>

        <div className="dashboard-card">
          <h4>Change password</h4>
          <p className="panel-hint">Re-enter your current password to set a new one.</p>
          {pwError && <p className="error-text">{pwError}</p>}
          {pwSuccess && <p className="success-text">{pwSuccess}</p>}
          <form onSubmit={changePassword}>
            <div className="modal-field">
              <label className="modal-field-label">Current password</label>
              <input
                type="password"
                autoComplete="current-password"
                value={pwForm.old_password}
                onChange={(e) => setPwForm({ ...pwForm, old_password: e.target.value })}
                required
              />
            </div>
            <div className="modal-field">
              <label className="modal-field-label">New password</label>
              <input
                type="password"
                autoComplete="new-password"
                minLength={10}
                value={pwForm.new_password}
                onChange={(e) => setPwForm({ ...pwForm, new_password: e.target.value })}
                required
              />
            </div>
            <button type="submit" className="btn-primary" disabled={pwSaving}>
              {pwSaving ? 'Changing…' : 'Change password'}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
