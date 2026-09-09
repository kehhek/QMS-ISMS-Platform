import React from 'react'
import { Link } from 'react-router-dom'

// Shared chrome for simple static content pages (Privacy Policy, Contact
// Us, ...) — same header/footer as the homepage so these don't read as a
// different, disconnected site, without dragging in the homepage's hero/
// zigzag sections these pages don't need.
export default function StaticPageLayout({ title, children }) {
  return (
    <div className="marketing marketing-warm">
      <header className="marketing-header">
        <Link to="/" className="marketing-logo" style={{ textDecoration: 'none', color: 'inherit' }}>QISMS</Link>
        <nav className="marketing-nav">
          <Link to="/trust" className="marketing-nav-link">Trust Center</Link>
          <Link to="/app" className="marketing-nav-link">Sign in</Link>
          <Link to="/register" className="pill-btn-dark">Get started</Link>
        </nav>
      </header>

      <section className="static-page">
        <h1>{title}</h1>
        <div className="static-page-body">{children}</div>
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
