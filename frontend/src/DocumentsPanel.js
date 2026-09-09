import React, { useEffect, useState } from 'react'
import { apiFetch, unwrapList } from './api'
import StatusBadge from './StatusBadge'
import ExportCsvButton from './ExportCsvButton'
import { requestInput, requestSignature } from './PromptDialog'

const CLASSIFICATION_OPTIONS = ['public', 'internal', 'confidential', 'restricted']
const STATUS_OPTIONS = ['draft', 'in_review', 'approved', 'archived']

const CATEGORY_COPY = {
  general: { noun: 'document', plural: 'documents', addLabel: 'Add Document' },
  policy: { noun: 'policy', plural: 'policies', addLabel: 'Add Policy' },
  sop: { noun: 'SOP', plural: 'SOPs', addLabel: 'Add SOP' },
  work_instruction: { noun: 'work instruction', plural: 'work instructions', addLabel: 'Add Work Instruction' },
}

const emptyForm = () => ({
  doc_id: '', title: '', content: '', classification: 'internal', owner: '', reviewer: '', approver: '',
})

function PolicyTemplatesSection({ token, onGenerated }) {
  const [templates, setTemplates] = useState(null)
  const [error, setError] = useState(null)
  const [generatingSlug, setGeneratingSlug] = useState(null)
  const [expanded, setExpanded] = useState(false)

  const load = () => {
    apiFetch('/policy-templates/', token)
      .then(setTemplates)
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line
  }, [])

  const generate = (slug) => {
    setGeneratingSlug(slug)
    setError(null)
    apiFetch(`/policy-templates/${slug}/generate/`, token, { method: 'POST' })
      .then(() => {
        load()
        onGenerated()
      })
      .catch((err) => setError(err.message))
      .finally(() => setGeneratingSlug(null))
  }

  if (!templates) return null

  return (
    <div className="workflow-card" style={{ marginBottom: 16 }}>
      <button type="button" onClick={() => setExpanded(!expanded)} style={{ marginBottom: expanded ? 12 : 0 }}>
        {expanded ? 'Hide' : 'Generate a policy from a template'} ({templates.length} available)
      </button>
      {expanded && (
        <div>
          {error && <p className="error-text">{error}</p>}
          <p className="panel-hint">
            Each template is a real first draft (Purpose, Scope, Policy Statements, Roles, Review) mapped to
            the ISO 27001 controls it supports — generated as a Draft you can edit, then route through the
            normal approval workflow. Generating the same one twice reuses the existing draft.
          </p>
          <table>
            <thead>
              <tr>
                <th>Policy</th>
                <th>Covers</th>
                <th>Controls</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {templates.map((t) => (
                <tr key={t.slug}>
                  <td>{t.title}</td>
                  <td style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{t.summary}</td>
                  <td style={{ fontSize: 12, color: 'var(--color-text-muted)' }}>{t.controls}</td>
                  <td>
                    <button
                      type="button"
                      onClick={() => generate(t.slug)}
                      disabled={generatingSlug === t.slug}
                    >
                      {t.already_generated ? 'View/regenerate' : generatingSlug === t.slug ? 'Generating…' : 'Generate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function PersonSelect({ value, onChange, members, allowNone }) {
  return (
    <select value={value || ''} onChange={(e) => onChange(e.target.value || null)}>
      {allowNone && <option value="">— none —</option>}
      {members.map((m) => <option key={m.user} value={m.user}>{m.username}</option>)}
    </select>
  )
}

export default function DocumentsPanel({ token, category = 'general', initialFilter, onConsumeFilter }) {
  const copy = CATEGORY_COPY[category] || CATEGORY_COPY.general
  const [documents, setDocuments] = useState([])
  const [members, setMembers] = useState([])
  const [error, setError] = useState(null)
  const [form, setForm] = useState(emptyForm)
  const [file, setFile] = useState(null)
  const [editingId, setEditingId] = useState(null)
  const [editForm, setEditForm] = useState(null)
  const [replaceFileId, setReplaceFileId] = useState(null)
  const [replaceFile, setReplaceFile] = useState(null)
  // Seeded from a Dashboard drill-down click (that chart spans every
  // document category — see DashboardSummaryView — so this only lands
  // on whichever category tab is actually open, "General" by default).
  const [statusFilter, setStatusFilter] = useState((initialFilter && initialFilter.status) || '')
  const [statusCounts, setStatusCounts] = useState(null)
  const [workflows, setWorkflows] = useState([])
  const [reviewRoleChoice, setReviewRoleChoice] = useState({}) // {[documentId]: approver_role}

  useEffect(() => {
    if (initialFilter && onConsumeFilter) onConsumeFilter()
    // Once on mount only — see statusFilter's own initializer above.
    // eslint-disable-next-line
  }, [])

  const load = () => {
    const query = statusFilter ? `&status=${statusFilter}` : ''
    apiFetch(`/documents/?category=${category}${query}`, token)
      .then((data) => setDocuments(unwrapList(data)))
      .catch((err) => setError(err.message))
  }

  const loadStatusCounts = () => {
    apiFetch(`/documents/status-summary/?category=${category}`, token)
      .then(setStatusCounts)
      .catch(() => setStatusCounts(null))
  }

  // Same workflows the Approvals tab manages — fetched here too so
  // Submit for review / Approve / Reject can live right on this table
  // instead of requiring a trip to that tab. Not category-filtered
  // (the endpoint doesn't support it), so this is every workflow in the
  // tenant; pendingStepFor below picks out just the one for each row.
  const loadWorkflows = () => {
    apiFetch('/workflows/', token).then((data) => setWorkflows(unwrapList(data))).catch(() => setWorkflows([]))
  }

  useEffect(() => {
    if (!token) return
    load()
    loadStatusCounts()
    loadWorkflows()
    apiFetch('/tenant/members/', token).then((data) => setMembers(unwrapList(data))).catch(() => setMembers([]))
    // eslint-disable-next-line
  }, [token, category, statusFilter])

  // The earliest still-pending step of this document's pending workflow
  // (if any) — WorkflowStepViewSet.decide only ever lets the earliest
  // pending step be decided, so that's the one actually actionable here.
  const pendingStepFor = (documentId) => {
    const wf = workflows.find((w) => w.document === documentId && w.status === 'pending')
    if (!wf) return null
    return [...wf.steps].filter((s) => s.status === 'pending').sort((a, b) => a.order - b.order)[0] || null
  }

  const submitForReview = (doc) => {
    const role = reviewRoleChoice[doc.id] || 'admin'
    apiFetch('/workflows/', token, {
      method: 'POST',
      body: JSON.stringify({ document: doc.id, new_steps: [{ order: 1, approver_role: role }] }),
    })
      .then(() => {
        setError(null)
        load()
        loadStatusCounts()
        loadWorkflows()
      })
      .catch((err) => setError(err.message))
  }

  const decideStep = async (stepId, decision) => {
    // 21 CFR Part 11 §11.200: signing requires re-entering your password
    // at the moment of signing — same electronic-signature flow as the
    // Approvals tab, just triggered from here.
    const result = await requestSignature({
      title: decision === 'approved' ? `Approve this ${copy.noun}` : `Reject this ${copy.noun}`,
      danger: decision === 'rejected',
      confirmLabel: decision === 'approved' ? 'Approve' : 'Reject',
    })
    if (!result) return
    apiFetch(`/workflow-steps/${stepId}/decide/`, token, {
      method: 'POST',
      body: JSON.stringify({ decision, password: result.password }),
    })
      .then(() => {
        setError(null)
        load()
        loadStatusCounts()
        loadWorkflows()
      })
      .catch((err) => setError(err.message))
  }

  const create = (e) => {
    e.preventDefault()
    const body = new FormData()
    body.append('category', category)
    Object.entries(form).forEach(([key, value]) => {
      if (value !== null && value !== undefined && value !== '') body.append(key, value)
    })
    if (file) body.append('file', file)

    apiFetch('/documents/', token, { method: 'POST', body })
      .then(() => {
        setForm(emptyForm())
        setFile(null)
        setError(null)
        load()
        loadStatusCounts()
      })
      .catch((err) => setError(err.message))
  }

  const startEdit = (doc) => {
    setEditingId(doc.id)
    // Deliberately excludes `file` — it's the download URL string here,
    // not something an inline JSON edit should ever send back (that
    // would corrupt the FileField). See "Replace file" below instead.
    const { file: _unused, ...rest } = doc
    setEditForm(rest)
  }

  const cancelEdit = () => {
    setEditingId(null)
    setEditForm(null)
  }

  const saveEdit = () => {
    apiFetch(`/documents/${editingId}/`, token, { method: 'PATCH', body: JSON.stringify(editForm) })
      .then(() => {
        setEditingId(null)
        setEditForm(null)
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const remove = (doc) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm(`Delete "${doc.title}"? This can't be undone.`)) return
    apiFetch(`/documents/${doc.id}/`, token, { method: 'DELETE' })
      .then(() => { setError(null); load(); loadStatusCounts() })
      .catch((err) => setError(err.message))
  }

  const archiveDocument = async (doc) => {
    const result = await requestInput({
      title: `Archive "${doc.title}"?`,
      message: "This retires it — it can't be un-archived.",
      fields: [{ name: 'reason', label: 'Reason for archiving', type: 'textarea', required: true }],
      confirmLabel: 'Archive',
      danger: true,
    })
    if (!result) return
    apiFetch(`/documents/${doc.id}/archive/`, token, {
      method: 'POST',
      body: JSON.stringify({ reason: result.reason }),
    })
      .then(() => {
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const uploadReplacementFile = (doc) => {
    if (!replaceFile) return
    const body = new FormData()
    body.append('file', replaceFile)
    apiFetch(`/documents/${doc.id}/`, token, { method: 'PATCH', body })
      .then(() => {
        setReplaceFileId(null)
        setReplaceFile(null)
        setError(null)
        load()
      })
      .catch((err) => setError(err.message))
  }

  const download = (doc) => {
    // A bespoke fetch, not the shared downloadFile helper: doc.file is
    // already a full "/api/..." path (see DocumentSerializer), and
    // downloadFile always prepends the API base itself — same pattern
    // EvidencePanel's download() uses for the identical reason.
    fetch(doc.file, { headers: { Authorization: `Token ${token}` } })
      .then((r) => {
        if (!r.ok) throw new Error(`Download failed (${r.status})`)
        return r.blob()
      })
      .then((blob) => {
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = doc.title || 'document'
        document.body.appendChild(a)
        a.click()
        a.remove()
        URL.revokeObjectURL(url)
      })
      .catch((err) => setError(err.message))
  }

  if (!token) return <p className="empty-state">Set a token above to view {copy.plural}.</p>

  return (
    <div>
      {error && <p className="error-text">{error}</p>}
      <p className="panel-hint">
        Version bumps automatically on every content/status/file change (see the version column) —
        it isn't something you set directly. Status only ever changes through a signed approval, in
        the Review column below: Submit for review moves a Draft to In review, and approving (which
        requires re-entering your password as an electronic signature) moves it to Approved. Editing
        an Approved {copy.noun}'s content or file sends it back to Draft for re-approval. Once
        Approved, an admin can Archive it with a reason. For a multi-step approval chain with named
        approvers, use the Approvals tab instead — this is a one-step shortcut for the common case.
      </p>

      {category === 'policy' && (
        <PolicyTemplatesSection token={token} onGenerated={() => { load(); loadStatusCounts() }} />
      )}

      {statusCounts && (
        <div className="stat-row">
          {STATUS_OPTIONS.map((s) => (
            <button
              key={s}
              type="button"
              className={`stat-tile stat-tile-clickable${statusFilter === s ? ' selected' : ''}`}
              onClick={() => setStatusFilter(statusFilter === s ? '' : s)}
              title={`Show only ${s.replace('_', ' ')} ${copy.plural}`}
            >
              <div className="stat-tile-value">{statusCounts[s] ?? 0}</div>
              <div className="stat-tile-label"><StatusBadge value={s} /></div>
            </button>
          ))}
        </div>
      )}
      {statusFilter && (
        <p className="panel-hint">
          Showing only <strong>{statusFilter.replace('_', ' ')}</strong> {copy.plural} —{' '}
          <button type="button" onClick={() => setStatusFilter('')} style={{ padding: '2px 8px' }}>
            clear filter
          </button>
        </p>
      )}

      <form onSubmit={create} className="toolbar" style={{ flexWrap: 'wrap' }}>
        <input
          placeholder="Document ID (e.g. QMS-001)"
          value={form.doc_id}
          onChange={(e) => setForm({ ...form, doc_id: e.target.value })}
          style={{ width: 140 }}
        />
        <input
          placeholder="Title"
          value={form.title}
          onChange={(e) => setForm({ ...form, title: e.target.value })}
          required
        />
        <input
          placeholder="Content (optional if attaching a file)"
          value={form.content}
          onChange={(e) => setForm({ ...form, content: e.target.value })}
          style={{ width: 220 }}
        />
        <select value={form.classification} onChange={(e) => setForm({ ...form, classification: e.target.value })}>
          {CLASSIFICATION_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <span className="field-label">Author:</span>
        <PersonSelect value={form.owner} onChange={(v) => setForm({ ...form, owner: v })} members={members} allowNone />
        <span className="field-label">Reviewer:</span>
        <PersonSelect value={form.reviewer} onChange={(v) => setForm({ ...form, reviewer: v })} members={members} allowNone />
        <span className="field-label">Approver:</span>
        <PersonSelect value={form.approver} onChange={(v) => setForm({ ...form, approver: v })} members={members} allowNone />
        <input type="file" accept="application/pdf" onChange={(e) => setFile(e.target.files[0])} />
        <button type="submit" className="btn-primary">{copy.addLabel}</button>
        <ExportCsvButton token={token} path="/documents/" query={`category=${category}`} filename={`${category}.csv`} />
      </form>
      {documents.length === 0 ? (
        <p className="empty-state">No {copy.plural} yet.</p>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table>
            <thead>
              <tr>
                <th>Doc ID</th>
                <th>Title</th>
                <th>Classification</th>
                <th>Status</th>
                <th>Review</th>
                <th>Version</th>
                <th>Author</th>
                <th>Reviewer</th>
                <th>Approver</th>
                <th>File</th>
                <th>Updated</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((d) => (
                editingId === d.id ? (
                  <tr key={d.id}>
                    <td>
                      <input value={editForm.doc_id} onChange={(e) => setEditForm({ ...editForm, doc_id: e.target.value })} style={{ width: 90 }} />
                    </td>
                    <td>
                      <input value={editForm.title} onChange={(e) => setEditForm({ ...editForm, title: e.target.value })} />
                    </td>
                    <td>
                      <select
                        value={editForm.classification}
                        onChange={(e) => setEditForm({ ...editForm, classification: e.target.value })}
                      >
                        {CLASSIFICATION_OPTIONS.map((c) => <option key={c} value={c}>{c}</option>)}
                      </select>
                    </td>
                    <td><StatusBadge value={d.status} /></td>
                    <td>—</td>
                    <td>{d.version}</td>
                    <td>
                      <PersonSelect
                        value={editForm.owner}
                        onChange={(v) => setEditForm({ ...editForm, owner: v })}
                        members={members}
                        allowNone
                      />
                    </td>
                    <td>
                      <PersonSelect
                        value={editForm.reviewer}
                        onChange={(v) => setEditForm({ ...editForm, reviewer: v })}
                        members={members}
                        allowNone
                      />
                    </td>
                    <td>
                      <PersonSelect
                        value={editForm.approver}
                        onChange={(v) => setEditForm({ ...editForm, approver: v })}
                        members={members}
                        allowNone
                      />
                    </td>
                    <td>{d.file ? <button onClick={() => download(d)}>Download</button> : '—'}</td>
                    <td>{new Date(d.updated_at).toLocaleString()}</td>
                    <td>
                      <div className="cell-actions">
                        <button onClick={saveEdit}>Save</button>
                        <button onClick={cancelEdit}>Cancel</button>
                      </div>
                    </td>
                  </tr>
                ) : (
                  <tr key={d.id}>
                    <td>{d.doc_id || '—'}</td>
                    <td>{d.title}</td>
                    <td><span className="badge badge-neutral">{d.classification}</span></td>
                    <td>
                      <StatusBadge value={d.status} />
                      {d.status === 'archived' && d.archived_reason && (
                        <div className="cell-wrap" style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                          {d.archived_reason} — {new Date(d.archived_at).toLocaleDateString()} by{' '}
                          {d.archived_by_username || 'system'}
                        </div>
                      )}
                    </td>
                    <td>
                      {d.status === 'draft' && (
                        <div className="cell-actions">
                          <select
                            value={reviewRoleChoice[d.id] || 'admin'}
                            onChange={(e) => setReviewRoleChoice({ ...reviewRoleChoice, [d.id]: e.target.value })}
                          >
                            <option value="admin">Admin</option>
                            <option value="auditor">Auditor</option>
                            <option value="user">User</option>
                          </select>
                          <button onClick={() => submitForReview(d)}>Submit for review</button>
                        </div>
                      )}
                      {d.status === 'in_review' && (() => {
                        const step = pendingStepFor(d.id)
                        if (!step) {
                          return <span className="badge badge-warning">Awaiting review</span>
                        }
                        return (
                          <div className="cell-actions">
                            <span style={{ fontSize: 11, color: 'var(--color-text-muted)' }}>
                              Needs {step.approver_username || step.approver_role}
                            </span>
                            <button onClick={() => decideStep(step.id, 'approved')}>Approve</button>
                            <button onClick={() => decideStep(step.id, 'rejected')}>Reject</button>
                          </div>
                        )
                      })()}
                      {(d.status === 'approved' || d.status === 'archived') && '—'}
                    </td>
                    <td>{d.version}</td>
                    <td>{d.owner_username || '—'}</td>
                    <td>{d.reviewer_username || '—'}</td>
                    <td>{d.approver_username || '—'}</td>
                    <td>
                      <div className="cell-actions">
                        {d.file && <button onClick={() => download(d)}>Download</button>}
                        {replaceFileId === d.id ? (
                          <>
                            <input
                              type="file" accept="application/pdf"
                              onChange={(e) => setReplaceFile(e.target.files[0])}
                              style={{ width: 110 }}
                            />
                            <button onClick={() => uploadReplacementFile(d)}>Upload</button>
                          </>
                        ) : (
                          <button onClick={() => { setReplaceFileId(d.id); setReplaceFile(null) }}>
                            {d.file ? 'Replace file' : 'Attach file'}
                          </button>
                        )}
                      </div>
                    </td>
                    <td>{new Date(d.updated_at).toLocaleString()}</td>
                    <td>
                      <div className="cell-actions">
                        <button onClick={() => startEdit(d)}>Edit</button>
                        {d.status === 'approved' && (
                          <button onClick={() => archiveDocument(d)}>Archive</button>
                        )}
                        <button onClick={() => remove(d)}>Delete</button>
                      </div>
                    </td>
                  </tr>
                )
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
