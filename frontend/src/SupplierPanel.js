import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import StatusBadge from './StatusBadge'
import ExportCsvButton from './ExportCsvButton'

const STATUS_OPTIONS = ['active', 'under_review', 'inactive']

function QuestionnaireForm({ supplierId, token, onCreated }) {
  const [title, setTitle] = useState('')
  const [questionsText, setQuestionsText] = useState('')
  const [error, setError] = useState(null)

  const submit = (e) => {
    e.preventDefault()
    const questions = questionsText.split('\n').map((q) => q.trim()).filter(Boolean)
    if (!questions.length) {
      setError('Add at least one question (one per line).')
      return
    }
    apiFetch('/supplier-questionnaires/', token, {
      method: 'POST',
      body: JSON.stringify({ supplier: supplierId, title, questions }),
    })
      .then(() => {
        setTitle('')
        setQuestionsText('')
        setError(null)
        onCreated()
      })
      .catch((err) => setError(err.message))
  }

  return (
    <form onSubmit={submit} className="toolbar" style={{ flexWrap: 'wrap', marginBottom: 12 }}>
      {error && <p className="error-text" style={{ width: '100%' }}>{error}</p>}
      <input
        placeholder="Questionnaire title (e.g. Annual Security Review)"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        style={{ width: 260 }}
        required
      />
      <textarea
        placeholder={'One question per line, e.g.\nDo you encrypt data at rest?\nWhen was your last penetration test?'}
        value={questionsText}
        onChange={(e) => setQuestionsText(e.target.value)}
        style={{ width: '100%', minHeight: 70, fontFamily: 'inherit' }}
      />
      <button type="submit" className="btn-primary">Create questionnaire</button>
    </form>
  )
}

function QuestionnairesSection({ supplierId, token }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [expandedResponses, setExpandedResponses] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [editText, setEditText] = useState('')

  const load = () => {
    apiFetch(`/supplier-questionnaires/?supplier=${supplierId}`, token)
      .then((data) => setItems(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line
  }, [])

  const send = (q) => {
    apiFetch(`/supplier-questionnaires/${q.id}/send/`, token, { method: 'POST' })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  const startEditQuestions = (q) => {
    setEditingId(q.id)
    setEditText(q.questions.join('\n'))
  }

  const saveQuestions = (q) => {
    const questions = editText.split('\n').map((line) => line.trim()).filter(Boolean)
    if (!questions.length) {
      setError('Add at least one question (one per line).')
      return
    }
    apiFetch(`/supplier-questionnaires/${q.id}/`, token, { method: 'PATCH', body: JSON.stringify({ questions }) })
      .then(() => { setError(null); setEditingId(null); load() })
      .catch((err) => setError(err.message))
  }

  const review = (q) => {
    apiFetch(`/supplier-questionnaires/${q.id}/review/`, token, { method: 'POST' })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  const decide = (q, decision) => {
    if (decision === 'reject') {
      // eslint-disable-next-line no-alert
      if (!window.confirm(`Reject "${q.supplier_name || 'this supplier'}" based on this questionnaire? They'll be emailed.`)) return
    }
    apiFetch(`/supplier-questionnaires/${q.id}/${decision}/`, token, { method: 'POST' })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  return (
    <div style={{ padding: '10px 4px' }}>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        The supplier fills this out at a one-time link — no account needed on their end. "Send"
        emails that link to the supplier's contact address on file.
      </p>
      <QuestionnaireForm supplierId={supplierId} token={token} onCreated={load} />
      {items === null ? (
        <p className="empty-state">Loading…</p>
      ) : items.length === 0 ? (
        <p className="empty-state">No questionnaires yet for this supplier.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Questions</th>
              <th>Status</th>
              <th>Sent</th>
              <th>Responded</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((q) => (
              <React.Fragment key={q.id}>
                <tr>
                  <td>{q.title}</td>
                  <td>{q.question_count}</td>
                  <td><StatusBadge value={q.status} /></td>
                  <td>{q.sent_at ? new Date(q.sent_at).toLocaleString() : '—'}</td>
                  <td>{q.responded_at ? new Date(q.responded_at).toLocaleString() : '—'}</td>
                  <td>
                    <div className="cell-actions">
                      {q.status === 'draft' && (
                        <button onClick={() => startEditQuestions(q)}>Edit questions</button>
                      )}
                      <button onClick={() => send(q)}>
                        {q.status === 'draft' ? 'Send' : 'Resend'}
                      </button>
                      {(q.status === 'responded' || q.status === 'reviewed') && (
                        <button onClick={() => setExpandedResponses(expandedResponses === q.id ? null : q.id)}>
                          {expandedResponses === q.id ? 'Hide responses' : 'View responses'}
                        </button>
                      )}
                      {q.status === 'responded' && (
                        <button onClick={() => review(q)}>Mark reviewed</button>
                      )}
                      {(q.status === 'responded' || q.status === 'reviewed') && (
                        <>
                          <button onClick={() => decide(q, 'approve')}>Approve</button>
                          <button onClick={() => decide(q, 'reject')}>Reject</button>
                        </>
                      )}
                    </div>
                  </td>
                </tr>
                {q.decided_at && (
                  <tr>
                    <td colSpan={6} style={{ fontSize: 12, color: 'var(--color-text-muted)', paddingTop: 0 }}>
                      {q.status === 'approved' ? 'Approved' : 'Rejected'} by {q.decided_by_username || 'system'} on{' '}
                      {new Date(q.decided_at).toLocaleString()}
                    </td>
                  </tr>
                )}
                {editingId === q.id && (
                  <tr>
                    <td colSpan={6} style={{ background: 'var(--color-bg)' }}>
                      <textarea
                        value={editText}
                        onChange={(e) => setEditText(e.target.value)}
                        style={{ width: '100%', minHeight: 90, fontFamily: 'inherit', marginTop: 8 }}
                      />
                      <div className="cell-actions" style={{ marginTop: 6 }}>
                        <button onClick={() => saveQuestions(q)}>Save</button>
                        <button onClick={() => setEditingId(null)}>Cancel</button>
                      </div>
                    </td>
                  </tr>
                )}
                {expandedResponses === q.id && (
                  <tr>
                    <td colSpan={6} style={{ background: 'var(--color-bg)' }}>
                      <ul style={{ margin: '8px 0', paddingLeft: 20 }}>
                        {q.responses.map((r, i) => (
                          <li key={i} style={{ marginBottom: 6 }}>
                            <strong>{r.question}</strong>
                            <br />
                            {r.answer || <em>(no answer given)</em>}
                          </li>
                        ))}
                      </ul>
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

function AgreementForm({ supplierId, token, onCreated }) {
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [file, setFile] = useState(null)
  const [error, setError] = useState(null)

  const submit = (e) => {
    e.preventDefault()
    if (!content.trim() && !file) {
      setError('Add agreement text or attach a file.')
      return
    }
    const body = new FormData()
    body.append('supplier', supplierId)
    body.append('title', title)
    if (content.trim()) body.append('content', content)
    if (file) body.append('file', file)
    apiFetch('/supplier-agreements/', token, { method: 'POST', body })
      .then(() => {
        setTitle('')
        setContent('')
        setFile(null)
        setError(null)
        onCreated()
      })
      .catch((err) => setError(err.message))
  }

  return (
    <form onSubmit={submit} className="toolbar" style={{ flexWrap: 'wrap', marginBottom: 12 }}>
      {error && <p className="error-text" style={{ width: '100%' }}>{error}</p>}
      <input
        placeholder="Agreement title (e.g. Vendor Agreement 2026)"
        value={title}
        onChange={(e) => setTitle(e.target.value)}
        style={{ width: 260 }}
        required
      />
      <textarea
        placeholder="Agreement text (optional if attaching a file)"
        value={content}
        onChange={(e) => setContent(e.target.value)}
        style={{ width: '100%', minHeight: 70, fontFamily: 'inherit' }}
      />
      <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files[0])} />
      <button type="submit" className="btn-primary">Create agreement</button>
    </form>
  )
}

function AgreementsSection({ supplierId, token }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)

  const load = () => {
    apiFetch(`/supplier-agreements/?supplier=${supplierId}`, token)
      .then((data) => setItems(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line
  }, [])

  const send = (a) => {
    apiFetch(`/supplier-agreements/${a.id}/send/`, token, { method: 'POST' })
      .then(() => { setError(null); load() })
      .catch((err) => setError(err.message))
  }

  return (
    <div style={{ padding: '10px 4px' }}>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Once you've approved a supplier above, send them an agreement to sign — same one-time,
        no-account link as the questionnaire. Signing captures their typed name/title and a timestamp.
      </p>
      <AgreementForm supplierId={supplierId} token={token} onCreated={load} />
      {items === null ? (
        <p className="empty-state">Loading…</p>
      ) : items.length === 0 ? (
        <p className="empty-state">No agreements yet for this supplier.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Title</th>
              <th>Status</th>
              <th>Sent</th>
              <th>Signed by</th>
              <th>Signed at</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {items.map((a) => (
              <tr key={a.id}>
                <td>{a.title}</td>
                <td><StatusBadge value={a.status} /></td>
                <td>{a.sent_at ? new Date(a.sent_at).toLocaleString() : '—'}</td>
                <td>{a.signer_name ? `${a.signer_name}${a.signer_title ? ` (${a.signer_title})` : ''}` : '—'}</td>
                <td>{a.signed_at ? new Date(a.signed_at).toLocaleString() : '—'}</td>
                <td>
                  <button onClick={() => send(a)}>{a.status === 'draft' ? 'Send' : 'Resend'}</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}

const EMPTY_FORM = {
  name: '', description: '', contact_name: '', contact_email: '',
  contact_phone: '', website: '', status: 'under_review', notes: '',
}

export default function SupplierPanel({ token }) {
  const [suppliers, setSuppliers] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState(null)
  const [expandedId, setExpandedId] = useState(null)

  const load = () => {
    apiFetch('/suppliers/', token)
      .then((data) => setSuppliers(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    if (token) load()
    // eslint-disable-next-line
  }, [token])

  const createSupplier = (e) => {
    e.preventDefault()
    apiFetch('/suppliers/', token, { method: 'POST', body: JSON.stringify(form) })
      .then(() => {
        setForm(EMPTY_FORM)
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const startEdit = (s) => {
    setEditingId(s.id)
    setEditForm({ ...s })
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditForm(null)
  }

  const saveEdit = () => {
    apiFetch(`/suppliers/${editingId}/`, token, { method: 'PATCH', body: JSON.stringify(editForm) })
      .then(() => {
        setEditingId(null)
        setEditForm(null)
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const deleteSupplier = (s) => {
    if (!window.confirm(`Delete supplier "${s.name}"? This can't be undone.`)) return
    apiFetch(`/suppliers/${s.id}/`, token, { method: 'DELETE' })
      .then(() => {
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view suppliers.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <form onSubmit={createSupplier} className="toolbar">
        <input
          placeholder="Name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
        <input
          placeholder="Contact name"
          value={form.contact_name}
          onChange={(e) => setForm({ ...form, contact_name: e.target.value })}
        />
        <input
          placeholder="Contact email"
          type="email"
          value={form.contact_email}
          onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
        />
        <select value={form.status} onChange={(e) => setForm({ ...form, status: e.target.value })}>
          {STATUS_OPTIONS.map((s) => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
        <button type="submit" className="btn-primary">Add Supplier</button>
        <ExportCsvButton token={token} path="/suppliers/" filename="suppliers.csv" />
      </form>

      {suppliers.length === 0 ? (
        <p className="empty-state">No suppliers yet.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Name</th>
              <th>Contact</th>
              <th>Email</th>
              <th>Status</th>
              <th>Website</th>
              <th>Questionnaires</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {suppliers.map((s) => (
              <React.Fragment key={s.id}>
                {editingId === s.id ? (
                  <tr>
                    <td>
                      <input value={editForm.name} onChange={(e) => setEditForm({ ...editForm, name: e.target.value })} />
                    </td>
                    <td>
                      <input
                        value={editForm.contact_name}
                        onChange={(e) => setEditForm({ ...editForm, contact_name: e.target.value })}
                      />
                    </td>
                    <td>
                      <input
                        value={editForm.contact_email}
                        onChange={(e) => setEditForm({ ...editForm, contact_email: e.target.value })}
                      />
                    </td>
                    <td>
                      <select value={editForm.status} onChange={(e) => setEditForm({ ...editForm, status: e.target.value })}>
                        {STATUS_OPTIONS.map((st) => <option key={st} value={st}>{st.replace('_', ' ')}</option>)}
                      </select>
                    </td>
                    <td>
                      <input value={editForm.website} onChange={(e) => setEditForm({ ...editForm, website: e.target.value })} />
                    </td>
                    <td>—</td>
                    <td>
                      <div className="cell-actions">
                        <button onClick={saveEdit}>Save</button>
                        <button onClick={cancelEdit}>Cancel</button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  <tr>
                    <td>{s.name}</td>
                    <td>{s.contact_name || '—'}</td>
                    <td>{s.contact_email || '—'}</td>
                    <td><StatusBadge value={s.status} /></td>
                    <td>{s.website ? <a href={s.website} target="_blank" rel="noreferrer">{s.website}</a> : '—'}</td>
                    <td>
                      <button type="button" onClick={() => setExpandedId(expandedId === s.id ? null : s.id)}>
                        {expandedId === s.id ? 'Hide' : 'View / Send'}
                      </button>
                    </td>
                    <td>
                      <div className="cell-actions">
                        <button onClick={() => startEdit(s)}>Edit</button>
                        <button onClick={() => deleteSupplier(s)}>Delete</button>
                      </div>
                    </td>
                  </tr>
                )}
                {expandedId === s.id && (
                  <tr>
                    <td colSpan={7} style={{ background: 'var(--color-bg)' }}>
                      <QuestionnairesSection supplierId={s.id} token={token} />
                      <hr style={{ border: 'none', borderTop: '1px solid var(--color-border)', margin: '16px 0' }} />
                      <AgreementsSection supplierId={s.id} token={token} />
                    </td>
                  </tr>
                )}
              </React.Fragment>
            ))}
          </tbody>
        </table>
      )}
    </div>
  )
}
