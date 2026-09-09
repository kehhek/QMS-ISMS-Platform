import React, { useState } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { formatApiError } from './api'
import { writeStoredToken } from './tokenStorage'
import AuthLayout from './AuthLayout'

export default function RegisterPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState({
    org_name: '', subdomain: '', username: '', email: '', password: '',
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
    <AuthLayout cardMaxWidth={420}>
      <form onSubmit={submit} className="auth-form">
        <h2>Create your organization</h2>
        <p className="panel-hint">Set up your own tenant — you'll be its first admin.</p>
        {error && <p className="error-text">{error}</p>}

        <div className="modal-field">
          <label className="modal-field-label" htmlFor="register-org-name">Organization name</label>
          <input
            id="register-org-name"
            value={form.org_name}
            onChange={(e) => setForm({ ...form, org_name: e.target.value })}
            required
          />
        </div>
        <div className="modal-field">
          <label className="modal-field-label" htmlFor="register-subdomain">Subdomain</label>
          <input
            id="register-subdomain"
            placeholder="e.g. acme"
            value={form.subdomain}
            onChange={(e) => setForm({ ...form, subdomain: e.target.value })}
            required
          />
        </div>
        <div className="modal-field">
          <label className="modal-field-label" htmlFor="register-username">Your username</label>
          <input
            id="register-username"
            value={form.username}
            onChange={(e) => setForm({ ...form, username: e.target.value })}
            required
          />
        </div>
        <div className="modal-field">
          <label className="modal-field-label" htmlFor="register-email">Email</label>
          <input
            id="register-email"
            type="email"
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            required
          />
        </div>
        <div className="modal-field">
          <label className="modal-field-label" htmlFor="register-password">Password</label>
          <input
            id="register-password"
            type="password"
            autoComplete="new-password"
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            required
            minLength={10}
          />
        </div>

        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? 'Creating…' : 'Create account'}
        </button>

        <p className="auth-form-footer-link">
          Already have an account? <Link to="/app">Log in</Link>
        </p>
      </form>
    </AuthLayout>
  )
}
