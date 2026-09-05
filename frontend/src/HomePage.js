import React from 'react'
import { Link } from 'react-router-dom'

const FEATURES = [
  { title: 'Document control', body: 'Versioned documents with multi-step, role-based approval workflows.' },
  { title: 'Risk & incident management', body: 'Track risks, incidents, suppliers, and the corrective actions that close them out.' },
  { title: 'ISO 27001 & SOC 2 ready', body: 'All 93 ISO 27001 controls and the SOC 2 Common Criteria, pre-loaded for every org.' },
  { title: 'Immutable audit trail', body: 'Every action is logged, append-only, enforced at the database level — not just in the UI.' },
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

export default function HomePage() {
  return (
    <div className="marketing">
      <header className="marketing-header">
        <div className="marketing-logo">QMS/ISMS Console</div>
        <nav className="marketing-nav">
          <Link to="/app" className="marketing-nav-link">Log in</Link>
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

      <footer className="marketing-footer">
        <p>This is a demo/starter platform — pricing shown here is illustrative, not billed.</p>
      </footer>
    </div>
  )
}
