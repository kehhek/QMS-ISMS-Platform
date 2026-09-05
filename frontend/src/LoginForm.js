import React, { useState } from 'react'

export default function LoginForm({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  // Set once a login attempt comes back with password_expired: true —
  // switches the form into "set a new password" mode using the same
  // username+old password already entered.
  const [expired, setExpired] = useState(false)
  const [newPassword, setNewPassword] = useState('')
  // "Forgot password?" — a separate sub-view, entered explicitly rather
  // than triggered by any login response.
  const [showForgot, setShowForgot] = useState(false)
  const [forgotSent, setForgotSent] = useState(false)

  const submit = (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    fetch('/api/accounts/token/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    })
      .then(async (r) => {
        const data = await r.json().catch(() => null)
        if (!r.ok) {
          if (data && data.password_expired) {
            setExpired(true)
            throw new Error(data.detail || 'Your password has expired.')
          }
          const message = (data && (data.non_field_errors?.[0] || data.detail)) || 'Login failed'
          throw new Error(message)
        }
        return data
      })
      .then((data) => data && onLogin(data.token))
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
  }

  const submitNewPassword = (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    fetch('/api/accounts/password/change-expired/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, old_password: password, new_password: newPassword }),
    })
      .then(async (r) => {
        const data = await r.json().catch(() => null)
        if (!r.ok) {
          const message = (data && (data.new_password?.[0] || data.detail)) || 'Could not change password'
          throw new Error(message)
        }
        return data
      })
      .then((data) => onLogin(data.token))
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
  }

  const submitForgot = (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    fetch('/api/accounts/password/reset/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username }),
    })
      .then(() => setForgotSent(true))
      .catch(() => setForgotSent(true)) // generic outcome either way — never confirm/deny a username exists
      .finally(() => setSubmitting(false))
  }

  if (showForgot) {
    return (
      <form onSubmit={submitForgot}>
        <h2>Reset your password</h2>
        {forgotSent ? (
          <p className="success-text">
            If an account with that username exists and has an email on file, a reset link has been sent.
          </p>
        ) : (
          <>
            <p className="panel-hint">Enter your username and we'll email you a reset link.</p>
            <input
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoFocus
              required
            />
            <button type="submit" disabled={submitting}>{submitting ? 'Sending…' : 'Send Reset Link'}</button>
          </>
        )}
        <p style={{ marginTop: 14, fontSize: 12 }}>
          <button
            type="button"
            onClick={() => { setShowForgot(false); setForgotSent(false) }}
            style={{ background: 'none', border: 'none', padding: 0, color: 'var(--color-primary)', cursor: 'pointer' }}
          >
            Back to log in
          </button>
        </p>
      </form>
    )
  }

  if (expired) {
    return (
      <form onSubmit={submitNewPassword}>
        <h2>Password expired</h2>
        {error && <p className="error-text">{error}</p>}
        <p className="panel-hint">Choose a new password to continue.</p>
        <input
          type="password"
          placeholder="New password"
          value={newPassword}
          onChange={(e) => setNewPassword(e.target.value)}
          autoFocus
          required
          minLength={10}
        />
        <button type="submit" disabled={submitting}>
          {submitting ? 'Changing…' : 'Set New Password & Log In'}
        </button>
      </form>
    )
  }

  return (
    <form onSubmit={submit}>
      <h2>QMS/ISMS Console</h2>
      {error && <p className="error-text">{error}</p>}
      <input
        placeholder="Username"
        value={username}
        onChange={(e) => setUsername(e.target.value)}
        autoFocus
        required
      />
      <input
        placeholder="Password"
        type="password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        required
      />
      <button type="submit" disabled={submitting}>{submitting ? 'Logging in…' : 'Log in'}</button>
      <p style={{ marginTop: 14, fontSize: 12 }}>
        <button
          type="button"
          onClick={() => setShowForgot(true)}
          style={{ background: 'none', border: 'none', padding: 0, color: 'var(--color-primary)', cursor: 'pointer' }}
        >
          Forgot password?
        </button>
      </p>
    </form>
  )
}
