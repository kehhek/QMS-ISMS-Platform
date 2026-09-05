import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import { formatApiError } from './api'

const FEATURES = [
  {
    title: 'Document control', icon: '📄', tone: 'blue',
    body: 'Versioned documents with multi-step, role-based approval workflows.',
  },
  {
    title: 'Risk & incident management', icon: '⚠️', tone: 'amber',
    body: 'Track risks, incidents, suppliers, and the corrective actions that close them out.',
  },
  {
    title: 'ISO 27001 & SOC 2 ready', icon: '✅', tone: 'teal',
    body: 'All 93 ISO 27001 controls and the SOC 2 Common Criteria, pre-loaded for every org.',
  },
  {
    title: 'Immutable audit trail', icon: '🔒', tone: 'violet',
    body: 'Every action is logged, append-only, enforced at the database level — not just in the UI.',
  },
]

const PLANS = [
  {
    key: 'free',
    name: 'Free',
    price: '$0',
    tagline: 'For evaluating the platform',
    features: ['Up to 3 users', 'Core QMS/ISMS modules', 'Community support'],
  },
  {
    key: 'team',
    name: 'Team',
    price: '$49/mo',
    tagline: 'For a growing compliance team',
    features: [
      'Up to 25 users', 'Unlimited approval workflows',
      'Full ISO 27001 + SOC 2 control catalogs', 'Email support',
    ],
    highlighted: true,
  },
  {
    key: 'enterprise',
    name: 'Enterprise',
    price: 'Talk to us',
    tagline: 'For larger organizations',
    features: ['Unlimited users', 'SSO (coming soon)', 'Dedicated support', 'Custom backup & retention policies'],
  },
]

function DemoRequestForm() {
  const [form, setForm] = useState({ name: '', email: '', company: '', message: '' })
  const [status, setStatus] = useState('idle') // idle | submitting | done
  const [error, setError] = useState(null)

  const submit = (e) => {
    e.preventDefault()
    setStatus('submitting')
    setError(null)
    fetch('/api/accounts/demo-request/', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    })
      .then(async (r) => {
        const data = await r.json().catch(() => null)
        if (!r.ok) throw new Error(formatApiError(data, 'Could not submit your request'))
        return data
      })
      .then(() => setStatus('done'))
      .catch((err) => {
        setError(err.message)
        setStatus('idle')
      })
  }

  if (status === 'done') {
    return <p className="success-text">Thanks — we'll be in touch shortly to schedule your demo.</p>
  }

  return (
    <form className="demo-request-form" onSubmit={submit}>
      {error && <p className="error-text">{error}</p>}
      <input
        placeholder="Your name"
        value={form.name}
        onChange={(e) => setForm({ ...form, name: e.target.value })}
        required
      />
      <input
        type="email"
        placeholder="Work email"
        value={form.email}
        onChange={(e) => setForm({ ...form, email: e.target.value })}
        required
      />
      <input
        placeholder="Company (optional)"
        value={form.company}
        onChange={(e) => setForm({ ...form, company: e.target.value })}
      />
      <textarea
        placeholder="What are you hoping to solve? (optional)"
        value={form.message}
        onChange={(e) => setForm({ ...form, message: e.target.value })}
      />
      <button type="submit" className="btn-primary" disabled={status === 'submitting'}>
        {status === 'submitting' ? 'Sending…' : 'Request a demo'}
      </button>
    </form>
  )
}

export default function HomePage() {
  return (
    <div className="marketing">
      <header className="marketing-header">
        <div className="marketing-logo">QMS/ISMS Console</div>
        <nav className="marketing-nav">
          <Link to="/app" className="marketing-nav-link">Log in</Link>
          <Link to="/register" className="marketing-nav-link">Create account</Link>
          <Link to="/register" className="btn-primary">Get started</Link>
        </nav>
      </header>

      <section className="hero">
        <h1>Run your QMS and ISMS in one place</h1>
        <p className="hero-subtitle">
          Documents, risks, suppliers, audits, incidents, and corrective actions — with ISO 27001
          and SOC 2 controls built in from day one.
        </p>
        <Link to="/register" className="btn-primary hero-cta">Get started free</Link>
      </section>

      <section className="feature-grid">
        {FEATURES.map((f) => (
          <div key={f.title} className="feature-card">
            <div className={`feature-icon feature-icon-${f.tone}`}>{f.icon}</div>
            <h3>{f.title}</h3>
            <p>{f.body}</p>
          </div>
        ))}
      </section>

      <section className="pricing">
        <h2>Simple, transparent pricing</h2>
        <div className="pricing-grid">
          {PLANS.map((p) => (
            <div key={p.key} className={`pricing-card${p.highlighted ? ' highlighted' : ''}`}>
              {p.highlighted && <div className="pricing-ribbon">Most popular</div>}
              <h3>{p.name}</h3>
              <div className="pricing-price">{p.price}</div>
              <p className="pricing-tagline">{p.tagline}</p>
              <ul>
                {p.features.map((f) => <li key={f}>{f}</li>)}
              </ul>
              <Link to={`/register?plan=${p.key}`} className="btn-primary pricing-cta">Get started</Link>
            </div>
          ))}
        </div>
      </section>

      <section className="demo-request">
        <div className="demo-request-inner">
          <div className="demo-request-pitch">
            <h2>Want a guided walkthrough instead?</h2>
            <p>
              Tell us a bit about your team and we'll set up a live demo tailored to your ISMS/QMS
              needs — no need to configure anything yourself first.
            </p>
          </div>
          <DemoRequestForm />
        </div>
      </section>

      <footer className="marketing-footer">
        <p>This is a demo/starter platform — pricing shown here is illustrative, not billed.</p>
      </footer>
    </div>
  )
}
