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
    <form onSubmit={submit} style={{ maxWidth: 320 }}>
      <h2>Log in</h2>
      {error && <p style={{ color: 'crimson' }}>{error}</p>}
      <div style={{ marginBottom: 8 }}>
        <input
          placeholder="Username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          style={{ width: '100%', boxSizing: 'border-box' }}
          autoFocus
        />
      </div>
      <div style={{ marginBottom: 8 }}>
        <input
          placeholder="Password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          style={{ width: '100%', boxSizing: 'border-box' }}
        />
      </div>
      <button type="submit" disabled={submitting}>{submitting ? 'Logging in…' : 'Log in'}</button>
    </form>
  )
}
