import React, { useEffect, useState } from 'react'

// Public, no-login page proving this org's compliance posture — reuses
// the marketing page's visual language (dark hero, quantified proof
// strip) since it's making the same kind of trust-buying pitch, just to
// this org's own customers/prospects instead of ours. Resolved to
// whichever tenant the domain/Host header maps to, same as every other
// endpoint — see PublicTrustCenterView's docstring for why only
// aggregate, non-sensitive figures are exposed here.
export default function TrustCenterPage() {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    fetch('/api/public/trust-center/')
      .then(async (r) => {
        const body = await r.json().catch(() => null)
        if (!r.ok) throw new Error((body && body.detail) || 'Could not load this trust center.')
        return body
      })
      .then(setData)
      .catch((err) => setError(err.message))
  }, [])

  if (error) {
    return (
      <div className="marketing">
        <p className="error-text" style={{ marginTop: 60, textAlign: 'center' }}>{error}</p>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="marketing">
        <p className="empty-state" style={{ marginTop: 60, textAlign: 'center' }}>Loading…</p>
      </div>
    )
  }

  const { org_name: orgName, frameworks, published_policies: publishedPolicies } = data

  return (
    <div className="marketing">
      <header className="marketing-header">
        <div className="marketing-logo">{orgName} Trust Center</div>
      </header>

      <section className="hero">
        <p className="hero-eyebrow">Security &amp; Compliance</p>
        <h1>{orgName} takes security seriously</h1>
        <p className="hero-subtitle">
          A live look at our information security program — the frameworks we align to and how our
          controls are tracking against them.
        </p>
        <p className="hero-frameworks">ISO/IEC 27001:2022 &nbsp;·&nbsp; SOC 2</p>
      </section>

      <section className="proof-strip">
        <div className="proof-point">
          <div className="proof-value">{frameworks.iso27001.percent}%</div>
          <div className="proof-label">
            ISO 27001 controls implemented ({frameworks.iso27001.implemented}/{frameworks.iso27001.total})
          </div>
        </div>
        <div className="proof-point">
          <div className="proof-value">{frameworks.soc2.percent}%</div>
          <div className="proof-label">
            SOC 2 controls implemented ({frameworks.soc2.implemented}/{frameworks.soc2.total})
          </div>
        </div>
        <div className="proof-point">
          <div className="proof-value">{publishedPolicies}</div>
          <div className="proof-label">Published security policies</div>
        </div>
      </section>

      <section className="feature-grid">
        <div className="feature-card">
          <h3>Information security program</h3>
          <p>
            Our information security management system covers document control, risk management,
            supplier due diligence, incident response, and continuous internal audit.
          </p>
        </div>
        <div className="feature-card">
          <h3>Continuous monitoring</h3>
          <p>
            Control implementation is tracked continuously, not just at audit time — the figures
            above reflect our current status, not a point-in-time snapshot.
          </p>
        </div>
        <div className="feature-card">
          <h3>Want more detail?</h3>
          <p>
            Reach out to your account contact to request our full audit report, policy set, or to
            complete a security questionnaire.
          </p>
        </div>
      </section>

      <footer className="marketing-footer">
        <p>This page reflects aggregate compliance status only and does not disclose control-level detail.</p>
      </footer>
    </div>
  )
}
