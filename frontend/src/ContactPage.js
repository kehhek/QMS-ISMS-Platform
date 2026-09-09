import React from 'react'
import StaticPageLayout from './StaticPageLayout'

export default function ContactPage() {
  return (
    <StaticPageLayout title="Contact Us">
      <p>
        Have a question about QISMS, or want to talk through your ISO 27001 or SOC 2 program? Reach
        out — we'd like to hear from you.
      </p>

      <div className="contact-card-grid">
        <div className="contact-card">
          <div className="contact-card-label">Email</div>
          <a href="mailto:keh@qisms.com" className="contact-card-value">keh@qisms.com</a>
        </div>
        <div className="contact-card">
          <div className="contact-card-label">Phone</div>
          <a href="tel:+16788919195" className="contact-card-value">(678) 891-9195</a>
        </div>
      </div>
    </StaticPageLayout>
  )
}
