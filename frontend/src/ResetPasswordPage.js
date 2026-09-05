import React, { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { formatApiError } from './api'
import { writeStoredToken } from './tokenStorage'

export default function ResetPasswordPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const uid = searchParams.get('uid') || ''
  const token = searchParams.get('token') || ''

  const [newPassword, setNewPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  if (!uid || !token) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <h2>Invalid reset link</h2>
          <p className="panel-hint">This link is missing its reset code. Request a new one from the login page.</p>
          <Link to="/app">Back to log in</Link>
        </div>
      </div>
    )
  }

  const submit = (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    fetch('/api/accounts/password/reset-confirm/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ uid, token, new_password: newPassword }),
    })
      .then(async (r) => {
        const data = await r.json().catch(() => null)
        if (!r.ok) {
          throw new Error(formatApiError(data, 'Could not reset password — the link may have expired.'))
        }
        return data
      })
      .then((data) => {
        writeStoredToken(data.token)
        navigate('/app')
      })
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
  }

  return (
    <div className="auth-screen">
      <div className="auth-card">
        <form onSubmit={submit}>
          <h2>Set a new password</h2>
          {error && <p className="error-text">{error}</p>}
          <input
            type="password"
            placeholder="New password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoFocus
            required
            minLength={10}
          />
          <button type="submit" disabled={submitting}>{submitting ? 'Saving…' : 'Set Password & Log In'}</button>
        </form>
      </div>
    </div>
  )
}
