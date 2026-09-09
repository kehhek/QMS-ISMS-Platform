import React from 'react'
import { Link } from 'react-router-dom'
import CyclingPhoto, { AUTH_PHOTOS } from './CyclingPhoto'

// Shared shell for the login screen (ConsoleApp.js, when there's no
// token yet) and the account-creation page (RegisterPage.js) — the same
// split layout and branding panel either way, so the two don't drift
// into two different "looks" for what's really one first impression.
export default function AuthLayout({ children, cardMaxWidth }) {
  return (
    <div className="auth-screen">
      <div className="auth-topbar">
        <Link to="/" className="auth-brand-link">QISMS</Link>
        <Link to="/" className="auth-back-link">← Back to home</Link>
      </div>
      <div className="auth-branding">
        <div className="auth-branding-inner">
          <CyclingPhoto
            className="auth-branding-photo"
            images={AUTH_PHOTOS}
            alt="A compliance team member reviewing controls"
          />
          <p className="auth-branding-tagline">
            Document control, risk, and compliance management for ISO 27001 and SOC 2 teams — audits,
            evidence, and electronic signatures built in from day one.
          </p>
          <div className="auth-branding-points">
            <div className="auth-branding-point">
              <div className="auth-branding-point-value">93</div>
              <div className="auth-branding-point-label">ISO 27001 controls, pre-loaded</div>
            </div>
            <div className="auth-branding-point">
              <div className="auth-branding-point-value">100%</div>
              <div className="auth-branding-point-label">Of records logged to an append-only audit trail</div>
            </div>
          </div>
          <p className="auth-branding-frameworks">ISO/IEC 27001:2022 &nbsp;·&nbsp; SOC 2 &nbsp;·&nbsp; 21 CFR Part 11</p>
        </div>
      </div>
      <div className="auth-form-side">
        <div className="auth-card" style={cardMaxWidth ? { maxWidth: cardMaxWidth } : undefined}>
          {children}
        </div>
      </div>
    </div>
  )
}
