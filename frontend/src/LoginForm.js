import React, { useState } from 'react'

export default function LoginForm({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)
  // Set once a login attempt comes back with password_expired: true or
  // must_change_password: true — switches the form into "set a new
  // password" mode using the same username+old password already
  // entered. Both reasons land on the same screen and the same
  // change-expired endpoint (it doesn't care which sent someone there),
  // just with different wording for why they're here.
  const [changeRequired, setChangeRequired] = useState(null) // null | 'expired' | 'must_change'
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
          if (data && (data.password_expired || data.must_change_password)) {
            setChangeRequired(data.must_change_password ? 'must_change' : 'expired')
            throw new Error(data.detail || 'Your password must be changed.')
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
      <form onSubmit={submitForgot} className="auth-form">
        <h2>Reset your password</h2>
        {forgotSent ? (
          <p className="success-text">
            If an account with that username exists and has an email on file, a reset link has been sent.
          </p>
        ) : (
          <>
            <p className="panel-hint">Enter your username and we'll email you a reset link.</p>
            <div className="modal-field">
              <label className="modal-field-label" htmlFor="login-forgot-username">Username</label>
              <input
                id="login-forgot-username"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                autoFocus
                required
              />
            </div>
            <button type="submit" className="btn-primary" disabled={submitting}>
              {submitting ? 'Sending…' : 'Send reset link'}
            </button>
          </>
        )}
        <p className="auth-form-footer-link">
          <button type="button" className="link-button" onClick={() => { setShowForgot(false); setForgotSent(false) }}>
            Back to log in
          </button>
        </p>
      </form>
    )
  }

  if (changeRequired) {
    return (
      <form onSubmit={submitNewPassword} className="auth-form">
        <h2>{changeRequired === 'must_change' ? 'Choose your own password' : 'Password expired'}</h2>
        {error && <p className="error-text">{error}</p>}
        <p className="panel-hint">
          {changeRequired === 'must_change'
            ? "An administrator set a temporary password for you — choose your own to continue. You won't see this screen again after this."
            : 'Choose a new password to continue.'}
        </p>
        <div className="modal-field">
          <label className="modal-field-label" htmlFor="login-new-password">New password</label>
          <input
            id="login-new-password"
            type="password"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoFocus
            required
            minLength={10}
          />
        </div>
        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? 'Changing…' : 'Set new password & log in'}
        </button>
      </form>
    )
  }

  return (
    <form onSubmit={submit} className="auth-form">
      <h2>Log in</h2>
      <p className="panel-hint">Welcome back — enter your credentials to continue.</p>
      {error && <p className="error-text">{error}</p>}
      <div className="modal-field">
        <label className="modal-field-label" htmlFor="login-username">Username</label>
        <input
          id="login-username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoFocus
          required
        />
      </div>
      <div className="modal-field">
        <label className="modal-field-label" htmlFor="login-password">Password</label>
        <input
          id="login-password"
          type="password"
          autoComplete="current-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          required
        />
      </div>
      <button type="submit" className="btn-primary" disabled={submitting}>
        {submitting ? 'Logging in…' : 'Log in'}
      </button>
      <p className="auth-form-footer-link">
        <button type="button" className="link-button" onClick={() => setShowForgot(true)}>
          Forgot password?
        </button>
      </p>
    </form>
  )
}
