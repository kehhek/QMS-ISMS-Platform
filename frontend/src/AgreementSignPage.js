import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { formatApiError } from './api'

// Public, no-account page a supplier opens from the link emailed by
// SupplierAgreementViewSet.send() — same access_token-is-the-credential
// pattern as QuestionnaireResponsePage, so this uses plain fetch too,
// never the authenticated apiFetch helpers.
export default function AgreementSignPage() {
  const { token } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [signerName, setSignerName] = useState('')
  const [signerTitle, setSignerTitle] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    fetch(`/api/public/agreements/${token}/`)
      .then(async (r) => {
        const body = await r.json().catch(() => null)
        if (!r.ok) throw new Error(formatApiError(body, 'This agreement link is not valid.'))
        return body
      })
      .then(setData)
      .catch((err) => setError(err.message))
  }, [token])

  const submit = (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    fetch(`/api/public/agreements/${token}/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ signer_name: signerName, signer_title: signerTitle }),
    })
      .then(async (r) => {
        const body = await r.json().catch(() => null)
        if (!r.ok) throw new Error(formatApiError(body, 'Could not submit your signature.'))
        return body
      })
      .then(() => setSubmitted(true))
      .catch((err) => setError(err.message))
      .finally(() => setSubmitting(false))
  }

  if (error && !data) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <h2>Link not valid</h2>
          <p className="panel-hint">{error}</p>
        </div>
      </div>
    )
  }

  if (!data) {
    return (
      <div className="auth-screen">
        <div className="auth-card">
          <p className="empty-state">Loading…</p>
        </div>
      </div>
    )
  }

  if (submitted || data.already_signed) {
    return (
      <div className="auth-screen">
        <div className="auth-card" style={{ maxWidth: 520 }}>
          <h2>{data.title}</h2>
          <p className="success-text">
            {submitted
              ? 'Thank you — your signature has been recorded.'
              : `This agreement was already signed by ${data.signer_name} on ${new Date(data.signed_at).toLocaleString()}.`}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-screen">
      <div className="auth-card" style={{ maxWidth: 600 }}>
        <h2>{data.title}</h2>
        <p className="panel-hint">
          From <strong>{data.supplier_name}</strong>. No account is needed — type your name below to sign.
        </p>
        {error && <p className="error-text">{error}</p>}

        {data.content && (
          <div
            style={{
              textAlign: 'left', whiteSpace: 'pre-wrap', border: '1px solid var(--color-border)',
              borderRadius: 8, padding: 14, marginBottom: 16, maxHeight: 320, overflowY: 'auto', fontSize: 13,
            }}
          >
            {data.content}
          </div>
        )}
        {data.file && (
          <p style={{ marginBottom: 16 }}>
            <a href={data.file} target="_blank" rel="noreferrer">Download the full agreement (PDF)</a>
          </p>
        )}

        <form onSubmit={submit}>
          <input
            placeholder="Your full name"
            value={signerName}
            onChange={(e) => setSignerName(e.target.value)}
            required
          />
          <input
            placeholder="Your title (optional)"
            value={signerTitle}
            onChange={(e) => setSignerTitle(e.target.value)}
          />
          <p className="panel-hint" style={{ textAlign: 'left' }}>
            By typing your name and submitting, you agree this constitutes your electronic signature
            on the agreement above.
          </p>
          <button type="submit" disabled={submitting}>
            {submitting ? 'Submitting…' : 'Sign agreement'}
          </button>
        </form>
      </div>
    </div>
  )
}
