import React, { useState } from 'react'

export default function LoginForm({ onLogin }) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

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
          const message = (data && (data.non_field_errors?.[0] || data.detail)) || 'Login failed'
          throw new Error(message)
        }
        return data
      })
      .then((data) => onLogin(data.token))
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
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
    </form>
  )
}
