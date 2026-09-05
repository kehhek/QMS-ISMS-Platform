import React, { useState } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { formatApiError } from './api'
import { writeStoredToken } from './tokenStorage'

const PLAN_OPTIONS = [
  { value: 'free', label: 'Free' },
  { value: 'team', label: 'Team' },
  { value: 'enterprise', label: 'Enterprise' },
]

export default function RegisterPage() {
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const [form, setForm] = useState({
    org_name: '',
    subdomain: '',
    username: '',
    email: '',
    password: '',
    plan: searchParams.get('plan') || 'free',
  })
  const [error, setError] = useState(null)
  const [submitting, setSubmitting] = useState(false)

  const submit = (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    fetch('/api/accounts/register/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    })
      .then(async (r) => {
        const data = await r.json().catch(() => null)
        if (!r.ok) {
          throw new Error(formatApiError(data, 'Registration failed'))
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
      <div className="auth-card" style={{ maxWidth: 380 }}>
        <form onSubmit={submit}>
          <h2>Create your organization</h2>
          {error && <p className="error-text">{error}</p>}

          <input
            placeholder="Organization name"
            value={form.org_name}
            onChange={(e) => setForm({ ...form, org_name: e.target.value })}
            required
          />
          <input
            placeholder="Subdomain (e.g. acme)"
            value={form.subdomain}
            onChange={(e) => setForm({ ...form, subdomain: e.target.value })}
            required
          />
          <input
            placeholder="Your username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            required
          />
          <input
            placeholder="Email"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
          <input
            placeholder="Password"
            type="password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
            minLength={8}
          />
          <select
            value={form.plan}
            onChange={(e) => setForm({ ...form, plan: e.target.value })}
            style={{ width: '100%', marginBottom: 10 }}
          >
            {PLAN_OPTIONS.map((p) => <option key={p.value} value={p.value}>{p.label} plan</option>)}
          </select>

          <button type="submit" disabled={submitting}>{submitting ? 'Creating…' : 'Create account'}</button>

          <p style={{ marginTop: 14, fontSize: 12 }}>
            Already have an account? <Link to="/app">Log in</Link>
          </p>
        </form>
      </div>
    </div>
  )
}
