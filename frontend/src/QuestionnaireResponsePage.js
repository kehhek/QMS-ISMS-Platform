import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { formatApiError } from './api'

// Public, no-account page a supplier opens from the link emailed by
// SupplierQuestionnaireViewSet.send() — the access_token in the URL is
// the only credential, so every call here is a plain fetch against
// /api/public/questionnaires/, never one of the authenticated apiFetch
// helpers (there's no token/session to attach).
export default function QuestionnaireResponsePage() {
  const { token } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [answers, setAnswers] = useState([])
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)

  useEffect(() => {
    fetch(`/api/public/questionnaires/${token}/`)
      .then(async (r) => {
        const body = await r.json().catch(() => null)
        if (!r.ok) throw new Error(formatApiError(body, 'This questionnaire link is not valid.'))
        return body
      })
      .then((body) => {
        setData(body)
        setAnswers(new Array(body.questions.length).fill(''))
      })
      .catch((err) => setError(err.message))
  }, [token])

  const submit = (e) => {
    e.preventDefault()
    setSubmitting(true)
    setError(null)
    fetch(`/api/public/questionnaires/${token}/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ answers }),
    })
      .then(async (r) => {
        const body = await r.json().catch(() => null)
        if (!r.ok) throw new Error(formatApiError(body, 'Could not submit your responses.'))
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

  if (submitted || data.already_responded) {
    return (
      <div className="auth-screen">
        <div className="auth-card" style={{ maxWidth: 520 }}>
          <h2>{data.title}</h2>
          <p className="success-text">
            {submitted
              ? 'Thank you — your responses have been submitted.'
              : 'This questionnaire has already been submitted. Thank you.'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="auth-screen">
      <div className="auth-card" style={{ maxWidth: 560 }}>
        <h2>{data.title}</h2>
        <p className="panel-hint">
          Requested from <strong>{data.supplier_name}</strong>. No account is needed — just answer
          below and submit.
        </p>
        {error && <p className="error-text">{error}</p>}
        <form onSubmit={submit}>
          {data.questions.map((q, i) => (
            <div key={i} style={{ marginBottom: 16, textAlign: 'left' }}>
              <label style={{ display: 'block', fontWeight: 600, fontSize: 13, marginBottom: 6 }}>
                {i + 1}. {q}
              </label>
              <textarea
                value={answers[i]}
                onChange={(e) => {
                  const next = [...answers]
                  next[i] = e.target.value
                  setAnswers(next)
                }}
                style={{ width: '100%', minHeight: 70, fontFamily: 'inherit' }}
                required
              />
            </div>
          ))}
          <button type="submit" disabled={submitting}>
            {submitting ? 'Submitting…' : 'Submit responses'}
          </button>
        </form>
      </div>
    </div>
  )
}
