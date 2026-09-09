import React, { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { formatApiError } from './api'
import CyclingPhoto, { HERO_PHOTOS } from './CyclingPhoto'

const PROOF_POINTS = [
  { value: '93', label: 'ISO 27001 Annex A controls, pre-loaded' },
  { value: '100%', label: 'Of records logged to an append-only audit trail' },
  { value: '21 CFR Part 11', label: 'Electronic signatures on every approval' },
]

// The two zigzag feature sections — each pairs real product substance
// with a small illustrative mockup (built from real column/status names,
// not lorem ipsum) rather than a stock screenshot we don't have.
const DOCUMENT_MOCK_ROWS = [
  { id: 'QMS-014', title: 'Access Control Policy', status: 'Approved', tone: 'success' },
  { id: 'QMS-021', title: 'Incident Response Plan', status: 'In review', tone: 'warning' },
  { id: 'QMS-009', title: 'Data Retention SOP', status: 'Draft', tone: 'neutral' },
]

const COVERAGE_MOCK_ROWS = [
  { name: 'ISO 27001', percent: 100 },
  { name: 'SOC 2', percent: 88 },
  { name: 'HIPAA', percent: 64 },
]

function HeroEmailCapture() {
  const navigate = useNavigate()
  const [email, setEmail] = useState('')

  const submit = (e) => {
    e.preventDefault()
    navigate(`/register${email ? `?email=${encodeURIComponent(email)}` : ''}`)
  }

  return (
    <form className="hero-capture" onSubmit={submit}>
      <input
        type="email"
        placeholder="Enter your work email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
      />
      <button type="submit" className="pill-btn-dark">Get started</button>
    </form>
  )
}

function DocumentMockCard() {
  return (
    <div className="mock-card">
      <div className="mock-card-header">
        <span>Doc ID</span><span>Title</span><span>Status</span>
      </div>
      {DOCUMENT_MOCK_ROWS.map((row) => (
        <div className="mock-card-row" key={row.id}>
          <span className="mock-card-id">{row.id}</span>
          <span>{row.title}</span>
          <span className={`mock-badge mock-badge-${row.tone}`}>{row.status}</span>
        </div>
      ))}
    </div>
  )
}

function CoverageMockCard() {
  return (
    <div className="mock-card">
      <div className="mock-card-title">Framework coverage</div>
      {COVERAGE_MOCK_ROWS.map((row) => (
        <div className="mock-coverage-row" key={row.name}>
          <span className="mock-coverage-name">{row.name}</span>
          <div className="mock-coverage-bar">
            <div className="mock-coverage-fill" style={{ width: `${row.percent}%` }} />
          </div>
          <span className="mock-coverage-percent">{row.percent}%</span>
        </div>
      ))}
    </div>
  )
}

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
    <div className="marketing marketing-warm">
      <header className="marketing-header">
        <div className="marketing-logo">QISMS</div>
        <nav className="marketing-nav">
          <Link to="/trust" className="marketing-nav-link">Trust Center</Link>
          <Link to="/app" className="marketing-nav-link">Sign in</Link>
          <Link to="/register" className="pill-btn-dark">Get started</Link>
        </nav>
      </header>

      <section className="warm-hero">
        <div className="warm-hero-copy">
          <h1>Elevate your compliance program with one unified platform</h1>
          <p className="warm-hero-subtitle">
            Documents, risks, suppliers, audits, incidents, and corrective actions — with ISO 27001
            and SOC 2 controls built in from day one.
          </p>
          <HeroEmailCapture />
          <p className="warm-hero-frameworks">ISO/IEC 27001:2022 &nbsp;·&nbsp; SOC 2 &nbsp;·&nbsp; 21 CFR Part 11</p>
        </div>

        <div className="warm-hero-art">
          <div className="warm-blob warm-blob-a" />
          <div className="warm-blob warm-blob-b" />
          <CyclingPhoto
            className="warm-hero-photo"
            images={HERO_PHOTOS}
            alt="A compliance team member reviewing controls"
          />
          <div className="warm-float-chip warm-float-chip-frameworks">
            <span className="warm-float-dot" /> ISO 27001 ready
          </div>
          <div className="warm-float-card">
            <div className="warm-float-card-label">Audit trail coverage</div>
            <div className="warm-float-card-value">100%</div>
          </div>
        </div>
      </section>

      <section className="proof-strip">
        {PROOF_POINTS.map((p) => (
          <div key={p.label} className="proof-point">
            <div className="proof-value">{p.value}</div>
            <div className="proof-label">{p.label}</div>
          </div>
        ))}
      </section>

      <section className="zigzag-section">
        <div className="zigzag-copy">
          <h2>Approvals your auditors will actually trust</h2>
          <p>
            Every document routes through role-based, multi-step approval — signed with a real
            electronic signature under 21 CFR Part 11, not just a status flip. Editing an approved
            document automatically sends it back for re-approval.
          </p>
          <Link to="/register" className="pill-btn-outline">Learn more →</Link>
        </div>
        <div className="zigzag-visual">
          <DocumentMockCard />
        </div>
      </section>

      <section className="zigzag-section zigzag-reverse">
        <div className="zigzag-copy">
          <h2>See coverage across every framework, instantly</h2>
          <p>
            ISO 27001, SOC 2, HIPAA, GDPR, PCI DSS, NIST CSF — mapped control-to-control, so
            implementing one framework shows you exactly how far it carries you toward the next.
          </p>
          <Link to="/register" className="pill-btn-outline">Learn more →</Link>
        </div>
        <div className="zigzag-visual">
          <CoverageMockCard />
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
        <div className="marketing-footer-columns">
          <div className="marketing-footer-brand">
            <div className="marketing-logo">QISMS</div>
            <p>Document control, risk, and compliance management for ISO 27001 and SOC 2 teams.</p>
          </div>

          <div className="marketing-footer-col">
            <h4>Product</h4>
            <Link to="/register">Create account</Link>
            <Link to="/app">Log in</Link>
          </div>

          <div className="marketing-footer-col">
            <h4>Resources</h4>
            <Link to="/trust">Trust Center</Link>
            <Link to="/privacy">Privacy Policy</Link>
            <Link to="/contact">Contact Us</Link>
          </div>
        </div>

        <div className="marketing-footer-bottom">
          <p>&copy; {new Date().getFullYear()} QISMS. This is a demo/starter platform.</p>
        </div>
      </footer>
    </div>
  )
}
